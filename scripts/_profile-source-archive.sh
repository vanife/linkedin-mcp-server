#!/usr/bin/env bash
# Archive the LinkedIn MCP browser profile for transfer to another machine.
# Usage:
#   _profile-source-archive.sh [output-archive-path]
#
# The archive includes:
#   - profile/          (Chromium persistent browser profile)
#   - cookies.json      (portable cookie export)
#   - source-state.json (session metadata)
#   - runtime-profiles/ (per-machine derived sessions)

set -euo pipefail

PROFILE_ROOT="${LINKEDIN_MCP_PROFILE_DIR:-$HOME/.linkedin-mcp}"
OUTPUT="${1:-$HOME/.linkedin-mcp-backup.tar.gz}"

if [ ! -d "$PROFILE_ROOT/profile" ]; then
    echo "Error: No profile found at $PROFILE_ROOT/profile" >&2
    exit 1
fi

echo "Archiving LinkedIn MCP profile from $PROFILE_ROOT ..."

# Build file list - only include what actually exists
ARCHIVE_FILES=(profile)
[ -f "$PROFILE_ROOT/cookies.json" ] && ARCHIVE_FILES+=(cookies.json)
[ -f "$PROFILE_ROOT/source-state.json" ] && ARCHIVE_FILES+=(source-state.json)

if [ -d "$PROFILE_ROOT/runtime-profiles" ]; then
    ARCHIVE_FILES+=(runtime-profiles)
fi

if [ ${#ARCHIVE_FILES[@]} -lt 1 ]; then
    echo "Error: Nothing to archive at $PROFILE_ROOT" >&2
    exit 1
fi

tar czf "$OUTPUT" -C "$PROFILE_ROOT" "${ARCHIVE_FILES[@]}"

echo "Archive written to $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
