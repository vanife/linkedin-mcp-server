#!/usr/bin/env bash
# Transfer a LinkedIn MCP profile archive to a remote machine via scp.
# Usage:
#   _profile-transfer.sh <user@host> [local-archive-path] [remote-dir]
#
# Example:
#   _profile-transfer.sh myuser@myhost
#   _profile-transfer.sh myuser@myhost ~/custom-backup.tar.gz ~/.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <user@host> [local-archive-path] [remote-dir]" >&2
    exit 1
fi

REMOTE_HOST="$1"
LOCAL_ARCHIVE="${2:-$HOME/.linkedin-mcp-backup.tar.gz}"
REMOTE_DIR="${3:-~}"

if [ ! -f "$LOCAL_ARCHIVE" ]; then
    echo "Error: Archive not found at $LOCAL_ARCHIVE" >&2
    echo "Run _profile-source-archive.sh first." >&2
    exit 1
fi

echo "Transferring $LOCAL_ARCHIVE to $REMOTE_HOST:$REMOTE_DIR ..."

scp "$LOCAL_ARCHIVE" "$REMOTE_HOST:$REMOTE_DIR/"

echo "Transfer complete. On the remote machine, run:"
echo "  _profile-extract.sh $REMOTE_DIR/$(basename "$LOCAL_ARCHIVE")"
