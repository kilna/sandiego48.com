#!/bin/bash
set -euo pipefail

# Copy assets/images to static/images, respecting Hugo's ignoreFiles patterns

# yq should be installed by Makefile

echo "Copying images from assets/images to static/images..."

# Clean and create destination
rm -rf static/images/
mkdir -p static/images

# Extract ignore patterns from hugo.yaml and convert from Go regex to POSIX regex
yq '.ignoreFiles[]' hugo.yaml | sed 's/^"//' | sed 's/"$//' | sed 's/\\\\/\\/g' > /tmp/ignore_patterns.txt

# Copy files that don't match ignore patterns
find assets/images -type f | while read -r file; do
  should_copy=true
  
  # Check against each ignore pattern
  while IFS= read -r pattern; do
    if echo "$file" | grep -qE "$pattern"; then
      echo "Skipping $file (matches pattern: $pattern)"
      should_copy=false
      break
    fi
  done < /tmp/ignore_patterns.txt
  
  # Copy if it doesn't match any ignore pattern
  if [ "$should_copy" = "true" ]; then
    dest="static/images/$(basename "$file")"
    cp "$file" "$dest"
    echo "Copied $(basename "$file")"
  fi
done

# Clean up
rm -f /tmp/ignore_patterns.txt

echo "Image copy complete!"
