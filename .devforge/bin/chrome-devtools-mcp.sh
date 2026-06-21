#!/bin/bash
# Auto-detect Chrome/Chromium debugging port and launch MCP server.
# Works with: JetBrains IDEs (WebStorm, IntelliJ, PhpStorm), VS Code,
# manual Chrome launches, and any OS (macOS, Linux, WSL).

PORT=""

# ── Step 1: Explicit override via environment variable ────────────────────
if [ -n "$CHROME_DEBUG_PORT" ]; then
  PORT="$CHROME_DEBUG_PORT"
  echo "Using CHROME_DEBUG_PORT=$PORT from environment" >&2
fi

# ── Step 2: Search for DevToolsActivePort files ───────────────────────────
if [ -z "$PORT" ] || [ "$PORT" = "0" ]; then
  SEARCH_DIRS=""

  case "$(uname -s)" in
    Darwin)
      # macOS: JetBrains IDEs + Chrome
      SEARCH_DIRS="$HOME/Library/Application Support/JetBrains"
      SEARCH_DIRS="$SEARCH_DIRS:$HOME/Library/Application Support/Google/Chrome"
      SEARCH_DIRS="$SEARCH_DIRS:$HOME/Library/Application Support/Chromium"
      ;;
    Linux)
      # Linux / WSL: JetBrains IDEs + Chrome/Chromium
      SEARCH_DIRS="$HOME/.config/JetBrains"
      SEARCH_DIRS="$SEARCH_DIRS:$HOME/.config/google-chrome"
      SEARCH_DIRS="$SEARCH_DIRS:$HOME/.config/chromium"
      # WSL: check Windows JetBrains paths
      for winuser in /mnt/c/Users/*; do
        [ -d "$winuser/AppData/Roaming/JetBrains" ] && SEARCH_DIRS="$SEARCH_DIRS:$winuser/AppData/Roaming/JetBrains"
      done 2>/dev/null
      ;;
  esac

  # Find the most recently modified DevToolsActivePort file across all search dirs
  DEVTOOLS_PORT_FILE=""
  IFS=':'
  for dir in $SEARCH_DIRS; do
    [ -d "$dir" ] || continue
    FOUND=$(find "$dir" -name "DevToolsActivePort" 2>/dev/null -exec ls -t {} + 2>/dev/null | head -1)
    if [ -n "$FOUND" ] && [ -f "$FOUND" ]; then
      DEVTOOLS_PORT_FILE="$FOUND"
      break
    fi
  done
  unset IFS

  if [ -n "$DEVTOOLS_PORT_FILE" ]; then
    PORT=$(head -1 "$DEVTOOLS_PORT_FILE")
    echo "Detected debugging port $PORT from: $DEVTOOLS_PORT_FILE" >&2
  fi
fi

# ── Step 3: Fall back to conventional default port ────────────────────────
if [ -z "$PORT" ] || [ "$PORT" = "0" ]; then
  # Port 9222 is the conventional default for --remote-debugging-port
  if curl -s "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
    PORT=9222
    echo "Detected Chrome on default port 9222" >&2
  fi
fi

# ── Step 4: Give up with helpful message ──────────────────────────────────
if [ -z "$PORT" ] || [ "$PORT" = "0" ]; then
  echo "Error: Could not find a Chrome debugging port." >&2
  echo "" >&2
  echo "Options:" >&2
  echo "  1. Set CHROME_DEBUG_PORT=<port> environment variable" >&2
  echo "  2. Start Chrome with: --remote-debugging-port=9222" >&2
  echo "  3. Start your IDE's JS debugger (WebStorm, IntelliJ, VS Code)" >&2
  exit 1
fi

# ── Launch MCP server ─────────────────────────────────────────────────────
exec npx -y --registry https://registry.npmjs.org chrome-devtools-mcp@latest --browserUrl "http://127.0.0.1:$PORT"
