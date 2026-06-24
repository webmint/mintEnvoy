# Bug 002: Leftover ping debug artifact in main

**Status**: Open
**Severity**: Info
**Source**: manual
**Feature**: N/A
**AC**: N/A
**Reported**: 2026-06-24
**Fixed**:

## Description

src/main/index.ts:54 has a leftover electron-vite scaffold debug handler ipcMain.on('ping', () => console.log('pong')). Constitution forbids leaving debug artifacts (console.log) behind. Pre-existing scaffold; not part of feature 003. Remove the handler (and its renderer 'ping' caller if any).

## Expected Behavior

_Expected behavior not specified — see spec AC._

## Actual Behavior

_Actual behavior not specified — see verification evidence._

## File(s)

| File              | Detail |
| ----------------- | ------ |
| src/main/index.ts |        |

## Evidence

Reported by user.

## Related Issues

_None — standalone bug._

## Fix Notes

_Filled in after resolution._
