#!/bin/sh
# pre-commit-forcing-functions.sh
#
# Pre-commit hook: runs each enabled forcing-function detector against the
# project root and aborts the commit on any violations.
#
# Install:
#   cp .devforge/templates/git-hooks/pre-commit-forcing-functions.sh \
#      .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Exit codes:
#   0 — all detectors clean (or no config, or no enabled rules)
#   1 — one or more detectors reported violations

set -e

# --- Resolve the project root ---
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$ROOT" ]; then
    # Not inside a git repo; nothing to do.
    exit 0
fi

HELPER="$ROOT/.devforge/lib/constitute_helper"
CONFIG="$ROOT/.devforge/constitute.json"

# --- Skip silently if the helper or config is absent / not executable ---
if [ ! -f "$CONFIG" ]; then
    exit 0
fi
if [ ! -x "$HELPER" ]; then
    exit 0
fi

# --- List enabled rules as CLI verbs ---
ENABLED_VERBS="$("$HELPER" list-forcing-functions --enabled --format verb --config "$CONFIG" 2>/dev/null || true)"

if [ -z "$ENABLED_VERBS" ]; then
    exit 0
fi

# --- Run each enabled detector ---
FAILED=0
for VERB in $ENABLED_VERBS; do
    # verify-design-tokens is a UI-feature check; only run it when at least
    # one disposition manifest exists (specs/*/design-manifest.json).  Non-UI
    # projects that have the rule enabled in constitute.json are skipped here
    # so the hook remains silent on non-UI features (consistent with how the
    # verify-magic-enum / verify-any-leak checks skip silently when their
    # preconditions are absent — e.g. no generated_types_dirs present).
    if [ "$VERB" = "verify-design-tokens" ]; then
        MANIFEST_FOUND="$(find "$ROOT/specs" -maxdepth 2 -name "design-manifest.json" 2>/dev/null | head -1)"
        if [ -z "$MANIFEST_FOUND" ]; then
            continue
        fi
    fi
    if "$HELPER" "$VERB" --root "$ROOT" --config "$CONFIG"; then
        : # clean
    else
        STATUS=$?
        if [ "$STATUS" -eq 2 ]; then
            printf >&2 "\npre-commit: forcing-functions %s reported violations; aborting commit.\n" "$VERB"
            printf >&2 "Fix the violations or add an inline escape on the offending line:\n"
            printf >&2 "  // forcing-fn-ok: <reason explaining why this exception is safe>\n\n"
            FAILED=1
        fi
        # exit code 1 = internal error; don't block commit on helper crashes
    fi
done

if [ "$FAILED" -eq 1 ]; then
    exit 1
fi

exit 0
