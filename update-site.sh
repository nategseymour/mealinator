#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DB_SOURCE="${1:-${MEALIE_DB_SOURCE:-/var/lib/docker/volumes/mealie_mealie-data/_data/mealie.db}}"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_DIR/.venv/bin/python}"
LOCAL_DB="$PROJECT_DIR/mealie.db"
SNAPSHOT_SOURCE=""

cleanup() {
    if [[ -n "${SNAPSHOT_SOURCE:-}" ]]; then
        if [[ -e "$SNAPSHOT_SOURCE" ]]; then
            if [[ -O "$SNAPSHOT_SOURCE" ]]; then
                rm -f -- "$SNAPSHOT_SOURCE" || true
            else
                sudo rm -f -- "$SNAPSHOT_SOURCE" || true
            fi
        fi
    fi
}
trap cleanup EXIT

# The Docker volume may not be traversable by the current user.
# If so, create a consistent temporary snapshot using sudo and Python.
if [[ ! -r "$DB_SOURCE" ]]; then
    SNAPSHOT_SOURCE="$(mktemp /tmp/mealinator-db-XXXXXX.sqlite)"
    sudo chown root:root "$SNAPSHOT_SOURCE"
    sudo python3 -c 'import sqlite3,sys; s=sqlite3.connect("file:"+sys.argv[1]+"?mode=ro",uri=True); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()' "$DB_SOURCE" "$SNAPSHOT_SOURCE"
    sudo chown "$(id -u):$(id -g)" "$SNAPSHOT_SOURCE"
    chmod 600 "$SNAPSHOT_SOURCE"
    DB_SOURCE="$SNAPSHOT_SOURCE"
fi

if [[ ! -e "$DB_SOURCE" ]]; then
    echo "Error: database path not found: $DB_SOURCE" >&2
    exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Error: Python environment not found: $PYTHON_BIN" >&2
    exit 1
fi

DB_SOURCE="$(realpath -- "$DB_SOURCE")"
cd "$PROJECT_DIR"

echo "========================================"
echo " Updating Mealinator static site"
echo "========================================"

echo
echo "→ Creating a consistent SQLite database snapshot..."

# SQLite's backup API safely reads a live database, including committed
# changes that may still be in its write-ahead log.
"$PYTHON_BIN" - "$DB_SOURCE" "$LOCAL_DB" <<'PY'
import os
import sqlite3
import sys

source_path, destination_path = sys.argv[1:3]
temporary_path = destination_path + ".snapshot.tmp"

try:
    if os.path.exists(temporary_path):
        os.remove(temporary_path)

    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    destination = sqlite3.connect(temporary_path)
    try:
        source.backup(destination)
        result = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result}")
    finally:
        destination.close()
        source.close()

    os.replace(temporary_path, destination_path)
    print("Database snapshot created and integrity check passed.")
except Exception:
    if os.path.exists(temporary_path):
        os.remove(temporary_path)
    raise
PY

echo
echo "→ Extracting images..."
"$PYTHON_BIN" extract_images.py

echo
echo "→ Converting images to JPEG..."
"$PYTHON_BIN" convert_images_to_jpg.py

echo
echo "→ Rendering recipes..."
"$PYTHON_BIN" render-recipes.py

echo
echo "→ Rendering index..."
"$PYTHON_BIN" render-index.py

echo
echo "========================================"
echo " Update complete"
echo "========================================"
