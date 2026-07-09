/**
 * intent_reader.js -- html intent-reader evaluate_script asset (plan 53 Phase 4).
 *
 * THIN MEASUREMENT COLLECTOR ONLY -- see built_reader.js's header for the
 * full rationale (OQ-A: no decisions here, Python owns every predicate).
 *
 * Precondition: the caller has ALREADY navigated to the design anchor's
 * `file` (a file:// URL) before invoking this script -- mirrors
 * built_reader.js's "already navigated to route" precondition.
 *
 * Bag output contract -- the SAME SHAPE as built_reader.js's bag (see that
 * file's docstring for the full field list), with two structural
 * differences. Both are legitimate empty defaults on this side, not
 * validation exceptions -- _design/_bag.py's parser accepts both:
 *   - "overflow_candidates" / "clip_candidates" are always [] -- the
 *     anchor-free sanity floor (plan 53 D9) runs ONLY on the built side;
 *     the reference is a static file, not a runtime surface to audit for
 *     unintended overflow/clip.
 *   - "fonts" is always {} -- there is no font-LOAD check on the intent
 *     side (plan 53 Phase 4 deliverable #2): the static reference is the
 *     source of truth for WHICH family is intended, not whether a font
 *     loaded at runtime.
 *
 * Elements are keyed by the anchor CSS SELECTOR (not a testid) -- the
 * anchor's selectors may be brittle classes (plan 53 D7 selector
 * asymmetry); that is fine because the reference is a static, unchanging
 * file, unlike living built code.
 *
 * Invocation (Phase 6 wires this, out of scope for Phase 4/5): the caller
 * substitutes the two placeholder tokens below --
 *   __CONTAINER_SELECTOR__      a JSON string literal CSS selector for the
 *                                anchor's container element (the binding's
 *                                first pair's anchor_selector).
 *   __ANCHOR_SELECTORS_JSON__   a JSON array literal of every anchor
 *                                selector this run needs measured (every
 *                                binding pair's anchor_selector, container
 *                                included).
 * -- then passes the resulting script body as the evaluate_script
 * `function`/`expression` payload. The result of this IIFE is the bag; the
 * caller writes it to a scratch file that `design_helper compare
 * --intent-bag <path>` reads.
 */
(function collectIntentBag(containerSelector, anchorSelectors) {
  function measureStyle(el) {
    var cs = window.getComputedStyle(el);
    return {
      color: cs.color,
      background: cs.backgroundColor,
      border: cs.borderTopWidth + ' ' + cs.borderTopStyle + ' ' + cs.borderTopColor,
      border_radius: cs.borderRadius,
      padding: cs.padding,
      margin: cs.margin,
      gap: cs.gap,
      font_family: cs.fontFamily,
      font_size: cs.fontSize,
      line_height: cs.lineHeight,
      font_weight: cs.fontWeight
    };
  }

  function measureGeometry(el) {
    var rect = el.getBoundingClientRect();
    return {
      x: rect.x,
      y: rect.y,
      width: rect.width,
      height: rect.height,
      scroll_width: el.scrollWidth,
      client_width: el.clientWidth
    };
  }

  function measureSelector(selector) {
    var el = document.querySelector(selector);
    if (!el) {
      return { found: false };
    }
    var cs = window.getComputedStyle(el);
    return {
      found: true,
      style: measureStyle(el),
      geometry: measureGeometry(el),
      overflow_x: cs.overflowX,
      position: cs.position
    };
  }

  var containerEl = document.querySelector(containerSelector);
  var regionFound = !!containerEl;

  var elements = {};
  for (var i = 0; i < anchorSelectors.length; i++) {
    elements[anchorSelectors[i]] = measureSelector(anchorSelectors[i]);
  }

  return {
    region_found: regionFound,
    elements: elements,
    overflow_candidates: [],
    clip_candidates: [],
    fonts: {}
  };
})(__CONTAINER_SELECTOR__, __ANCHOR_SELECTORS_JSON__);
