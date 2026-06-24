"""_design_tokens — static provenance detector for design tokens.

Enforces that component style sources (CSS / styled-components / CSS-in-JS)
use design tokens rather than hardcoded visual literals.  Part of the
forcing-functions family (plan 40 Phase 4).

Public API
----------
From _cmd:  cmd_verify_design_tokens
From _scanner: scan_for_design_token_violations
"""
