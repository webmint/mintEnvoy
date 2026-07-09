/**
 * built_reader.js -- web built-reader evaluate_script asset (plan 53 Phase 4).
 *
 * THIN MEASUREMENT COLLECTOR ONLY. This script makes NO overflow / clip /
 * fidelity / font-loaded DECISIONS -- it only measures the running page and
 * returns a normalized JSON "bag". Every predicate (overflow, clip,
 * font-not-loaded, value fidelity, geometry fidelity) is applied in Python
 * to that bag by src/devforge/lib/_design/_floor.py + _fidelity.py +
 * _comparator.py (see _bag.py's module docstring for the authoritative bag
 * schema this output MUST match field-for-field).
 *
 * Why thin (OQ-A resolution): the framework repo has no JS test infra, and
 * jsdom (the usual node unit-test DOM) has no layout engine -- scrollWidth /
 * clientWidth / getBoundingClientRect all read 0 there -- and no font
 * loading, so a jsdom test of this file's geometry/font logic would be
 * meaningless. Keeping every decision in Python means the decision logic
 * IS fully unit-tested (against synthetic bag fixtures in
 * tests/lib/_design/test_floor.py / test_fidelity.py / test_comparator.py);
 * this file's own measurement logic is verified only at Phase 9 e2e against
 * a real Chrome MCP render, per the ratified plan.
 *
 * Precondition: the caller has ALREADY navigated to the binding's `route`
 * (e.g. via mcp__chrome-devtools__navigate_page) before invoking this
 * script.
 *
 * Invocation (Phase 6 wires this, out of scope for Phase 4/5): the caller
 * substitutes the two placeholder tokens below --
 *   __CONTAINER_TESTID__      a JSON string literal, e.g. "\"my-region\""
 *   __BUILT_TESTIDS_JSON__    a JSON array literal of every built_testid
 *                             this run needs measured (normally every
 *                             binding pair's built_testid, container
 *                             included -- the container is simply pairs[0]).
 * -- then passes the resulting script body as the evaluate_script
 * `function`/`expression` payload. The result of this IIFE is the bag; the
 * caller writes it to a scratch file that `design_helper compare
 * --built-bag <path>` reads.
 *
 * Bag output contract (must match _design/_bag.py's parse_bag exactly):
 * {
 *   "region_found": boolean,           -- containerTestid resolved + mounted
 *   "elements": {
 *     "<built_testid>": {
 *       "found": boolean,
 *       "style": {                      -- present only when found=true
 *         "color": string, "background": string, "border": string,
 *         "border_radius": string, "padding": string, "margin": string,
 *         "gap": string, "font_family": string, "font_size": string,
 *         "line_height": string, "font_weight": string
 *       },
 *       "geometry": {                   -- present only when found=true
 *         "x": number, "y": number, "width": number, "height": number,
 *         "scroll_width": number, "client_width": number
 *       },
 *       "overflow_x": string,           -- present only when found=true
 *       "position": string              -- present only when found=true
 *     }, ...
 *   },
 *   "overflow_candidates": [             -- every descendant of the
 *     { "label": string,                   container (anchor-free floor,
 *       "scroll_width": number,             plan 53 D9); [] when the
 *       "client_width": number,             container was not found
 *       "overflow_x": string }, ...
 *   ],
 *   "clip_candidates": [
 *     { "label": string,
 *       "child_rect": {"x": number, "y": number, "width": number, "height": number},
 *       "parent_rect": {"x": number, "y": number, "width": number, "height": number},
 *       "parent_overflow": string,
 *       "child_position": string }, ...
 *   ],
 *   "fonts": {                            -- the FIRST family token of the
 *     "<family-token>": boolean             computed font-family stack
 *   }                                        (quotes/whitespace stripped),
 *                                            sampled from :root, the
 *                                            container, AND each measured
 *                                            built_testid pair element
 *                                            (FIX F3/F4 -- element-level
 *                                            sampling catches an opt-in
 *                                            pair's own font-family, and
 *                                            first-token-only means a
 *                                            loaded custom primary with an
 *                                            unloaded secondary fallback
 *                                            never enters this dict). Raw
 *                                            document.fonts.check() result
 *                                            (Python decides "not-loaded"
 *                                            and skips generic keywords --
 *                                            this collector does neither).
 * }
 */
(function collectBuiltBag(containerTestid, builtTestids) {
  function byTestid(testid) {
    return document.querySelector('[data-testid="' + testid + '"]');
  }

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

  function measureElement(testid) {
    var el = byTestid(testid);
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

  // Build a short human-readable path from the container down to `el`,
  // preferring a data-testid segment where present -- purely a report
  // label, never consumed as a selector.
  function labelFor(el, root) {
    var parts = [];
    var node = el;
    while (node && node !== root && node.nodeType === 1) {
      var tag = node.tagName.toLowerCase();
      var testid = node.getAttribute('data-testid');
      if (testid) {
        parts.unshift(tag + '[data-testid="' + testid + '"]');
        break;
      }
      var parent = node.parentElement;
      var idx = 1;
      if (parent) {
        var siblings = parent.children;
        for (var i = 0; i < siblings.length; i++) {
          if (siblings[i] === node) {
            break;
          }
          if (siblings[i].tagName === node.tagName) {
            idx++;
          }
        }
      }
      parts.unshift(tag + ':nth-of-type(' + idx + ')');
      node = parent;
    }
    return parts.join(' > ') || el.tagName.toLowerCase();
  }

  function collectOverflowAndClip(root) {
    var overflow = [];
    var clip = [];
    var all = root.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      var cs = window.getComputedStyle(el);
      var label = labelFor(el, root);

      overflow.push({
        label: label,
        scroll_width: el.scrollWidth,
        client_width: el.clientWidth,
        overflow_x: cs.overflowX
      });

      var parent = el.parentElement;
      if (parent) {
        var parentCs = window.getComputedStyle(parent);
        var childRect = el.getBoundingClientRect();
        var parentRect = parent.getBoundingClientRect();
        clip.push({
          label: label,
          child_rect: {
            x: childRect.x,
            y: childRect.y,
            width: childRect.width,
            height: childRect.height
          },
          parent_rect: {
            x: parentRect.x,
            y: parentRect.y,
            width: parentRect.width,
            height: parentRect.height
          },
          parent_overflow: parentCs.overflow,
          child_position: cs.position
        });
      }
    }
    return { overflow: overflow, clip: clip };
  }

  // FIX F3/F4: take only the FIRST family token of a computed font-family
  // stack (quotes/whitespace stripped) -- a legit secondary custom fallback
  // (e.g. "Primary","FallbackCustom",sans-serif where Primary loaded) must
  // never enter the fonts dict and false-flag (F4). Returns '' when the
  // stack is empty/whitespace-only.
  function firstFontFamilyToken(fontFamilyValue) {
    var stack = fontFamilyValue || '';
    var first = stack.split(',')[0] || '';
    return first.trim().replace(/^["']+/, '').replace(/["']+$/, '').trim();
  }

  // FIX F3: sample :root, the container, AND each measured built_testid
  // pair element -- not just :root + container -- so an opt-in pair's own
  // font-family (which may differ from its ancestors) is covered by the
  // font-not-loaded floor (the D10 vacuous-pass case reproduced at element
  // level: a value-compare passes because the declared family name still
  // matches while the actual font silently fell back).
  function collectFonts(root, builtTestids, elements) {
    var fonts = {};
    var stacks = [
      window.getComputedStyle(document.documentElement).fontFamily,
      window.getComputedStyle(root).fontFamily
    ];

    for (var i = 0; i < builtTestids.length; i++) {
      var testid = builtTestids[i];
      var record = elements[testid];
      if (!record || !record.found) {
        continue;
      }
      var el = byTestid(testid);
      if (!el) {
        continue;
      }
      stacks.push(window.getComputedStyle(el).fontFamily);
    }

    for (var j = 0; j < stacks.length; j++) {
      var token = firstFontFamilyToken(stacks[j]);
      if (!token || token in fonts) {
        continue;
      }
      var loaded = false;
      try {
        loaded = document.fonts.check('16px ' + token);
      } catch (e) {
        loaded = false;
      }
      fonts[token] = loaded;
    }
    return fonts;
  }

  var containerEl = byTestid(containerTestid);
  var regionFound = !!containerEl;

  var elements = {};
  for (var i = 0; i < builtTestids.length; i++) {
    elements[builtTestids[i]] = measureElement(builtTestids[i]);
  }

  var overflowCandidates = [];
  var clipCandidates = [];
  var fonts = {};
  if (regionFound) {
    var oc = collectOverflowAndClip(containerEl);
    overflowCandidates = oc.overflow;
    clipCandidates = oc.clip;
    fonts = collectFonts(containerEl, builtTestids, elements);
  }

  return {
    region_found: regionFound,
    elements: elements,
    overflow_candidates: overflowCandidates,
    clip_candidates: clipCandidates,
    fonts: fonts
  };
})(__CONTAINER_TESTID__, __BUILT_TESTIDS_JSON__);
