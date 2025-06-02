#!/usr/bin/env bash

set -euo pipefail

# Create black directory if it doesn't exist
mkdir -p assets/icons/black

# Convert each white icon to black
for icon in assets/icons/white/*.png; do
  filename=$(basename "$icon")
  echo "Converting $filename to black..."
  magick "$icon" -colorspace RGB -fill black -colorize 100% "assets/icons/black/$filename"
done

echo "Conversion complete!" 