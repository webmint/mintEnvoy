"""Forcing-functions detector family for consumer-side constitute verification.

This subpackage contains mechanical detectors that catch the rule classes LLMs
systematically violate when generating code under a constitution. Each detector
is a consumer-side recurring gate (not forge-internal) that compares the
consumer's own source against declared sources of truth such as generated types
or declared layer graphs. The shared substrate lives in _shared.py; each
detector lives in its own sub-subpackage (_magic_enum/, _cross_layer/,
_any_leak/).
"""
