#!/usr/bin/env bash
# Import a folder of event photos into cdn/photos/<slug>/ as photo-NNN.jpg.
#
# Photos are ordered by filename (camera sequence), auto-rotated, resized to
# fit within MAX_EDGE px, metadata-stripped, and numbered after any photos
# already in the destination so batches can be appended.
#
# Usage: scripts/import-event-photos.sh <source-dir> <slug>
# Env:   MAX_EDGE (default 2560), QUALITY (default 85), JOBS (default 6)

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <source-dir> <slug>" >&2
  exit 1
fi

src=$1
slug=$2
max_edge=${MAX_EDGE:-2560}
quality=${QUALITY:-85}
jobs=${JOBS:-6}

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dest="$project_root/cdn/photos/$slug"

if [ ! -d "$src" ]; then
  echo "Source directory not found: $src" >&2
  exit 1
fi
command -v vips >/dev/null || { echo "vips is required (brew install vips)" >&2; exit 1; }

mkdir -p "$dest"

last=$(find "$dest" -maxdepth 1 -name 'photo-[0-9][0-9][0-9].jpg' \
  | sed -E 's/.*photo-0*([0-9]+)\.jpg$/\1/' | sort -n | tail -1)
last=${last:-0}

plan=$(mktemp)
trap 'rm -f "$plan"' EXIT

n=$last
while IFS= read -r f; do
  n=$((n + 1))
  printf '%s\t%s/photo-%03d.jpg\n' "$f" "$dest" "$n" >> "$plan"
done < <(find "$src" -maxdepth 1 -type f -iregex '.*\.\(jpe?g\|png\|tiff?\|heic\)$' | LC_ALL=C sort)

count=$(wc -l < "$plan" | tr -d ' ')
if [ "$count" -eq 0 ]; then
  echo "No images found in $src" >&2
  exit 1
fi

echo "Importing $count photos into $dest (starting at $((last + 1)))"

export max_edge quality
tr '\t\n' '\0\0' < "$plan" | xargs -0 -n 2 -P "$jobs" sh -c '
  vips thumbnail "$0" "$1[Q=$quality,strip,optimize_coding]" "$max_edge" \
    --height "$max_edge" --size down
'

echo "Done. Next: make gallery-thumbs gallery-update-counts"
