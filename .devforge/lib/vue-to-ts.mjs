#!/usr/bin/env node
// Compile every .vue Single File Component under <root> to a plain .ts/.js file
// using the consumer project's own @vue/compiler-sfc (resolved from <root>'s
// node_modules via createRequire). Output is intended for downstream graph
// indexing — TS parsers can read the compiled scripts and extract symbols
// otherwise invisible inside SFCs.
//
// This tool has ZERO npm dependencies of its own. It is shipped as a single
// .mjs file. The consumer project must have @vue/compiler-sfc installed
// (every Vue 3 project does — it's a transitive dep of `vue` and an explicit
// devDep in most setups).
//
// Recommended usage: write to a system temp dir + delete after codegraph
// ingest, so no .vue.ts artifacts ever land inside the consumer repo:
//
//   TEMP=$(mktemp -d) && \
//     node vue-to-ts.mjs <root> --mode mirror --out "$TEMP" && \
//     codegraph build --root <root> --vue-extract-dir "$TEMP" && \
//     rm -rf "$TEMP"
import { readFile, writeFile, mkdir, readdir, stat } from 'node:fs/promises'
import { basename, dirname, join, relative, resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { createHash } from 'node:crypto'
import { createRequire } from 'node:module'

const HELP = `Usage: vue-to-ts <root> [options]

Walks <root> recursively, compiles every .vue file to .ts (or .js) using the
consumer project's @vue/compiler-sfc (resolved from <root>'s node_modules),
and writes the result for downstream graph indexing.

Options:
  --mode <sidecar|mirror>   sidecar: write next to source as <name>.vue.ts
                            mirror:  write under --out preserving tree
                            (default: sidecar)
  -o, --out <dir>           Required when --mode mirror
  --include <name>          (reserved — currently ignored; only *.vue files
                            are processed)
  --exclude <substr>        Skip files whose relative path contains <substr>
                            (repeatable, comma-separated)
  --include-template        Append compiled render fn (default: script only)
  --raw-template-comment    Append raw template as a trailing comment
  --no-header               Omit the auto-generated provenance header
  --dry-run                 Parse + compile but do not write files
  -q, --quiet               Suppress per-file logs
  -h, --help                Show this message

Defaults
  - Skip directories by name: node_modules, dist, build, coverage, .git,
    .cache, .nuxt, .output, .turbo
  - Output language: .ts if <script lang="ts"> detected, else .js
  - Style blocks are dropped (irrelevant for symbol extraction)
  - Source maps emitted as Source Map V3 sidecar (<name>.vue.ts.map)
    with mappings shifted by header line count

Exit codes
  0  all files compiled
  1  one or more files failed
  2  invalid arguments OR @vue/compiler-sfc missing in <root>'s node_modules
`

const args = (() => {
  try {
    return parseArgs({
      options: {
        mode: { type: 'string', default: 'sidecar' },
        out: { type: 'string', short: 'o' },
        include: { type: 'string', multiple: true },
        exclude: { type: 'string', multiple: true },
        'include-template': { type: 'boolean', default: false },
        'raw-template-comment': { type: 'boolean', default: false },
        'no-header': { type: 'boolean', default: false },
        'dry-run': { type: 'boolean', default: false },
        quiet: { type: 'boolean', short: 'q', default: false },
        help: { type: 'boolean', short: 'h', default: false },
      },
      allowPositionals: true,
    })
  } catch (err) {
    console.error(`Argument error: ${err.message}`)
    console.error(HELP)
    process.exit(2)
  }
})()

if (args.values.help || args.positionals.length === 0) {
  console.log(HELP)
  process.exit(args.values.help ? 0 : 2)
}

const root = resolve(args.positionals[0])
const mode = args.values.mode
if (mode !== 'sidecar' && mode !== 'mirror') {
  console.error(`--mode must be 'sidecar' or 'mirror' (got '${mode}')`)
  process.exit(2)
}
const outDir = args.values.out ? resolve(args.values.out) : null
if (mode === 'mirror' && !outDir) {
  console.error('--mode mirror requires --out <dir>')
  process.exit(2)
}

try {
  const s = await stat(root)
  if (!s.isDirectory()) {
    console.error(`<root> is not a directory: ${root}`)
    process.exit(2)
  }
} catch {
  console.error(`<root> does not exist: ${root}`)
  process.exit(2)
}

// Resolve @vue/compiler-sfc from <root>'s tree. Try in order:
//   1. <root>/node_modules/@vue/compiler-sfc           (target-is-Vue-project)
//   2. ancestors of <root> via createRequire walk-up   (target-is-subdir-of-vue-project)
//   3. descendants — walk DOWN for first `node_modules/@vue/compiler-sfc/package.json`
//      hit, using <root>'s skip rules                  (wrapper-mode + monorepo)
// First hit wins.
let parse, compileScript, compileTemplate
{
  const tried = []

  function tryResolve(anchorDir) {
    tried.push(anchorDir)
    try {
      const req = createRequire(`${anchorDir}/__resolve_anchor__`)
      return req('@vue/compiler-sfc')
    } catch {
      return null
    }
  }

  // Strategies 1 + 2: Node's standard resolution from <root> (walks up).
  let sfc = tryResolve(root)

  // Strategy 3: walk DOWN for first node_modules/@vue/compiler-sfc/package.json hit.
  if (!sfc) {
    const SKIP_FOR_DEP_SEARCH = new Set([
      'dist', 'build', 'coverage', '.git', '.cache',
      '.nuxt', '.output', '.turbo',
    ])
    async function* findSfcAnchors(dir) {
      let entries
      try {
        entries = await readdir(dir, { withFileTypes: true })
      } catch { return }
      for (const e of entries) {
        if (!e.isDirectory()) continue
        const full = join(dir, e.name)
        if (e.name === 'node_modules') {
          // Check this node_modules for @vue/compiler-sfc directly.
          try {
            const pkg = await readFile(
              join(full, '@vue', 'compiler-sfc', 'package.json'),
              'utf8',
            )
            if (pkg) yield dirname(full)  // parent of node_modules = anchor
          } catch {}
          continue  // never descend into node_modules
        }
        if (SKIP_FOR_DEP_SEARCH.has(e.name)) continue
        yield* findSfcAnchors(full)
      }
    }
    for await (const anchor of findSfcAnchors(root)) {
      sfc = tryResolve(anchor)
      if (sfc) break
    }
  }

  if (!sfc) {
    console.error(`Failed to resolve @vue/compiler-sfc anywhere under ${root}.`)
    console.error(`Tried anchors: ${tried.join(', ')}`)
    console.error(`Install it in the consumer Vue project (or its monorepo root):`)
    console.error(`  cd <vue-project-dir> && npm install @vue/compiler-sfc`)
    process.exit(2)
  }
  parse = sfc.parse
  compileScript = sfc.compileScript
  compileTemplate = sfc.compileTemplate
}

// Skip directories by name (replaces fast-glob's `**/<name>/**` patterns
// for the common case). Walking is recursive; entries matching these names
// are not descended into.
const SKIP_DIRS = new Set([
  'node_modules', 'dist', 'build', 'coverage', '.git',
  '.cache', '.nuxt', '.output', '.turbo',
])

const userExcludes = flatten(args.values.exclude)

function flatten(arr) {
  if (!arr) return []
  return arr.flatMap((s) => s.split(',').map((x) => x.trim()).filter(Boolean))
}

function pathExcluded(rel) {
  for (const sub of userExcludes) {
    if (rel.includes(sub)) return true
  }
  return false
}

async function* walkVueFiles(dir) {
  let entries
  try {
    entries = await readdir(dir, { withFileTypes: true })
  } catch {
    return
  }
  for (const entry of entries) {
    const fullPath = join(dir, entry.name)
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue
      yield* walkVueFiles(fullPath)
    } else if (entry.isFile() && entry.name.endsWith('.vue')) {
      const rel = relative(root, fullPath)
      if (pathExcluded(rel)) continue
      yield fullPath
    }
  }
}

const files = []
for await (const f of walkVueFiles(root)) files.push(f)

if (files.length === 0) {
  console.error(`No .vue files found under ${root}`)
  process.exit(0)
}

if (!args.values.quiet) {
  console.error(`Found ${files.length} .vue file(s) under ${relative(process.cwd(), root) || '.'}`)
}

const results = { ok: 0, failed: 0, errors: [] }
const t0 = Date.now()

for (const absPath of files) {
  const rel = relative(root, absPath)
  try {
    const out = await processFile(absPath, rel)
    results.ok++
    if (!args.values.quiet) {
      console.log(`  ok  ${rel} -> ${out.outRel}`)
    }
  } catch (err) {
    results.failed++
    results.errors.push({ file: rel, error: err.message })
    console.error(`  err ${rel}: ${err.message}`)
  }
}

const dt = ((Date.now() - t0) / 1000).toFixed(2)
console.error(`\n${results.ok} ok, ${results.failed} failed, ${dt}s`)
process.exit(results.failed > 0 ? 1 : 0)

async function processFile(absPath, rel) {
  const source = await readFile(absPath, 'utf8')
  const id = hashId(rel)

  if (source.trim().length === 0) {
    return writeStub(absPath, rel, 'js', 'empty source file')
  }

  const { descriptor, errors: parseErrors } = parse(source, { filename: absPath })

  const isEmptySfc =
    !descriptor.script && !descriptor.scriptSetup && !descriptor.template
  if (isEmptySfc) {
    return writeStub(absPath, rel, 'js', 'no <script> or <template> blocks')
  }

  if (parseErrors.length) {
    throw new Error(`parse: ${parseErrors.map((e) => e.message).join('; ')}`)
  }

  const hasScriptSetup = !!descriptor.scriptSetup
  const hasScript = !!descriptor.script
  const lang = descriptor.scriptSetup?.lang || descriptor.script?.lang || 'js'
  const isTs = lang === 'ts' || lang === 'tsx'
  const ext = isTs ? '.ts' : '.js'

  let compiledScript = null
  if (hasScript || hasScriptSetup) {
    try {
      compiledScript = compileScript(descriptor, {
        id,
        sourceMap: true,
        inlineTemplate: false,
        babelParserPlugins: isTs ? ['typescript'] : [],
      })
    } catch (err) {
      throw new Error(`compileScript: ${err.message}`)
    }
  }

  let templateBlock = ''
  if (args.values['include-template'] && descriptor.template) {
    try {
      const tpl = compileTemplate({
        id,
        filename: absPath,
        source: descriptor.template.content,
        scoped: false,
        slotted: false,
        compilerOptions: {
          bindingMetadata: compiledScript?.bindings,
          mode: 'module',
        },
      })
      const tplErrors = (tpl.errors || []).map((e) => (typeof e === 'string' ? e : e.message))
      if (tplErrors.length) {
        templateBlock = `\n// --- template (compile errors) ---\n// ${tplErrors.join('\n// ')}\n`
      } else {
        templateBlock = `\n// --- template (compiled render) ---\n${tpl.code}\n`
      }
    } catch (err) {
      templateBlock = `\n// --- template (compile threw) ---\n// ${err.message}\n`
    }
  }

  let rawTemplateComment = ''
  if (args.values['raw-template-comment'] && descriptor.template) {
    const lines = descriptor.template.content.split('\n').map((l) => `// ${l}`).join('\n')
    rawTemplateComment = `\n// --- template (raw) ---\n${lines}\n`
  }

  const header = args.values['no-header']
    ? ''
    : buildHeader(rel, hasScriptSetup ? '<script setup>' : hasScript ? '<script>' : '(no script)', lang)

  const scriptContent = compiledScript ? compiledScript.content : 'export default {}\n'

  let outAbs
  let outRel
  if (mode === 'sidecar') {
    outAbs = absPath + ext
    outRel = relative(process.cwd(), outAbs)
  } else {
    outAbs = join(outDir, rel) + ext
    outRel = relative(process.cwd(), outAbs)
  }

  // Source map: shift compiledScript.map by header line count + retarget
  // sources to a path relative to the .map file. The map only covers the
  // <script> block; templateBlock + rawTemplateComment after it are
  // unmapped (template would need its own map from compileTemplate).
  const mapAbs = outAbs + '.map'
  let mapWrite = null
  let sourceMappingComment = ''
  if (compiledScript && compiledScript.map) {
    const headerLineOffset = countLines(header)
    const sourceRel = relative(dirname(outAbs), absPath)
    const adjusted = {
      ...compiledScript.map,
      sources: [sourceRel],
      mappings: ';'.repeat(headerLineOffset) + compiledScript.map.mappings,
    }
    mapWrite = JSON.stringify(adjusted) + '\n'
    sourceMappingComment = `\n//# sourceMappingURL=${basename(mapAbs)}\n`
  }

  const output = header + scriptContent + templateBlock + rawTemplateComment + sourceMappingComment

  if (!args.values['dry-run']) {
    await mkdir(dirname(outAbs), { recursive: true })
    await writeFile(outAbs, output, 'utf8')
    if (mapWrite !== null) {
      await writeFile(mapAbs, mapWrite, 'utf8')
    }
  }

  return { outAbs, outRel }
}

function countLines(s) {
  if (!s) return 0
  // Header always terminates with '\n'; newline count == line count.
  return (s.match(/\n/g) || []).length
}

async function writeStub(absPath, rel, lang, reason) {
  const isTs = lang === 'ts' || lang === 'tsx'
  const ext = isTs ? '.ts' : '.js'
  const header = args.values['no-header']
    ? ''
    : [
        '// ============================================================',
        `// auto-generated by vue-to-ts from ${rel}`,
        `// stub: ${reason}`,
        '// ============================================================',
        '',
        '',
      ].join('\n')
  const output = header + 'export default {}\n'

  let outAbs
  let outRel
  if (mode === 'sidecar') {
    outAbs = absPath + ext
    outRel = relative(process.cwd(), outAbs)
  } else {
    outAbs = join(outDir, rel) + ext
    outRel = relative(process.cwd(), outAbs)
  }
  if (!args.values['dry-run']) {
    await mkdir(dirname(outAbs), { recursive: true })
    await writeFile(outAbs, output, 'utf8')
  }
  return { outAbs, outRel }
}

function buildHeader(rel, blockKind, lang) {
  return [
    '// ============================================================',
    `// auto-generated by vue-to-ts from ${rel}`,
    `// source kind: ${blockKind}, lang: ${lang}`,
    '// edits will be overwritten on next run',
    '// ============================================================',
    '',
    '',
  ].join('\n')
}

function hashId(input) {
  return createHash('sha256').update(input).digest('hex').slice(0, 8)
}
