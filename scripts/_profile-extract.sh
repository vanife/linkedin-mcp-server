#!/usr/bin/env bash
# Extract a LinkedIn MCP profile archive on the target machine.
# Usage:
#   _profile-extract.sh [archive-path] [target-dir]
#
# Example:
#   _profile-extract.sh
#   _profile-extract.sh ~/backup.tar.gz ~/.linkedin-mcp

set -euo pipefail

ARCHIVE="${1:-$HOME/.linkedin-mcp-backup.tar.gz}"
PROFILE_ROOT="${2:-$HOME/.linkedin-mcp}"

if [ ! -f "$ARCHIVE" ]; then
    echo "Error: Archive not found at $ARCHIVE" >&2
    exit 1
fi

echo "Extracting LinkedIn MCP profile to $PROFILE_ROOT ..."

mkdir -p "$PROFILE_ROOT"

tar xzf "$ARCHIVE" -C "$PROFILE_ROOT"

if [ -d "$PROFILE_ROOT/profile" ]; then
    PROFILE_SIZE=$(du -sh "$PROFILE_ROOT/profile" | cut -f1)
    echo "Profile restored successfully ($PROFILE_SIZE)"

    if [ -f "$PROFILE_ROOT/source-state.json" ]; then
        echo "Source state found - session metadata is intact."
    fi

    echo ""
    echo "Note: The server will detect a runtime mismatch and create a new"
    echo "derived runtime profile on first startup. This is expected."
else
    echo "Warning: profile/ directory not found in archive." >&2
    exit 1
fi
