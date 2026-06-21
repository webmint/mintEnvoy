"""Build-tool + framework hint derivation from package manifests."""

from __future__ import annotations

from typing import Optional


# Build tool hint derivation: if any of these names appear in dependency
# keys (deps or devDeps), the corresponding hint is emitted. First match wins.
_BUILD_TOOL_HINTS = (
    ("vite",    "vite"),
    ("webpack", "webpack"),
    ("rollup",  "rollup"),
    ("next",    "next"),
    ("tsc",     "tsc"),
)


# Framework hint derivation: per-package framework signal extracted
# mechanically from manifest deps. First match wins. Order is by
# specificity (Next.js implies React but emits "Next.js"; Nuxt implies
# Vue but emits "Nuxt"; bare "vue" only fires when no meta-framework
# matches first). Returns None when no recognized framework is present
# — used by Phase 2 PACKAGE_STACKS compose to avoid mis-attributing
# the project-level top framework to every workspace package.
_FRAMEWORK_HINTS = (
    # Meta-frameworks first (more specific than the bare framework).
    ("next",                  "Next.js"),
    ("nuxt",                  "Nuxt"),
    ("@remix-run/react",      "Remix"),
    ("@sveltejs/kit",         "SvelteKit"),
    ("expo",                  "Expo"),
    # Frontend frameworks.
    ("vue",                   "Vue"),
    ("react",                 "React"),
    ("@angular/core",         "Angular"),
    ("svelte",                "Svelte"),
    ("solid-js",              "Solid"),
    ("@builder.io/qwik",      "Qwik"),
    ("react-native",          "React Native"),
    ("preact",                "Preact"),
    ("lit",                   "Lit"),
    # Backend frameworks.
    ("@nestjs/core",          "NestJS"),
    ("express",               "Express"),
    ("fastify",               "Fastify"),
    ("koa",                   "Koa"),
    ("hapi",                  "Hapi"),
    ("@adonisjs/core",        "AdonisJS"),
    ("hono",                  "Hono"),
    # Python frameworks (when manifest is pyproject.toml).
    ("fastapi",               "FastAPI"),
    ("django",                "Django"),
    ("flask",                 "Flask"),
)


def _derive_build_tool_hint(
    dependencies: dict, dev_dependencies: dict
) -> Optional[str]:
    """Derive a build tool hint from package dependencies.

    Checks dep key names (case-insensitive exact match on the bare tool
    name component). Returns None if no known build tool is detected.
    """
    all_deps = {}
    all_deps.update(dependencies or {})
    all_deps.update(dev_dependencies or {})
    lower_keys = {k.lower() for k in all_deps}
    for tool, hint in _BUILD_TOOL_HINTS:
        if tool in lower_keys:
            return hint
    return None


def _derive_framework_hint(
    dependencies: dict, dev_dependencies: dict
) -> Optional[str]:
    """Derive a framework hint from package dependencies.

    Walks _FRAMEWORK_HINTS in order; returns the canonical framework name
    on first match. Order is by specificity — meta-frameworks (Next.js,
    Nuxt, Remix, SvelteKit) are checked BEFORE their underlying framework
    (React, Vue, Svelte) so a Next.js package emits "Next.js" not "React".
    Returns None when no recognized framework is present (per-package
    fact, not project-level inheritance).
    """
    all_deps = {}
    all_deps.update(dependencies or {})
    all_deps.update(dev_dependencies or {})
    lower_keys = {k.lower() for k in all_deps}
    for dep_name, hint in _FRAMEWORK_HINTS:
        if dep_name.lower() in lower_keys:
            return hint
    return None
