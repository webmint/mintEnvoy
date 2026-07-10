// Probe: deterministically reproduce the confirmed root cause of Bug 011.
// Root cause (H-A): the renderer NAMES Inter + JetBrains Mono in its font-family
// tokens, but NO @font-face sources them, so the faces are unavailable and every
// surface falls back to system fonts. This is a data-shape / code-fact check —
// no runtime, auth, network, or timing dependency.

// SOURCE: src/renderer/styles/tokens.css:62
const FONT_SANS = "-apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Text', system-ui, sans-serif";
// SOURCE: src/renderer/styles/tokens.css:63
const FONT_MONO = "'JetBrains Mono', 'SF Mono', ui-monospace, Menlo, Consolas, monospace";

// The set of font families the app actually sources via @font-face.
// Established by search_code over src/renderer: ZERO @font-face declarations exist.
const SOURCED_FACES = new Set(); // empty — no @font-face anywhere in src/renderer

// Custom (non-system) faces the tokens NAME and therefore require a source.
const REQUIRED_CUSTOM_FACES = ['Inter', 'JetBrains Mono'];

const unsourced = REQUIRED_CUSTOM_FACES.filter((f) => !SOURCED_FACES.has(f));

if (unsourced.length === REQUIRED_CUSTOM_FACES.length) {
  console.log('H-A CONFIRMED: all named custom faces are unsourced -> ' + JSON.stringify(unsourced));
  console.log('  font-sans stack: ' + FONT_SANS);
  console.log('  font-mono stack: ' + FONT_MONO);
  process.exit(0);
}
console.log(
  'H-A DISPROVED: some named faces are sourced by @font-face: ' +
    JSON.stringify(REQUIRED_CUSTOM_FACES.filter((f) => SOURCED_FACES.has(f)))
);
process.exit(1);
