#!/bin/bash

# Fix placeholder images for people without headshots - remove image parameter to use sitewide placeholder

set -e

echo "Fixing placeholder images for people without headshots..."

# Find all people directories
for person_dir in content/people/*/; do
  if [ ! -d "$person_dir" ]; then
    continue
  fi
  
  person_name=$(basename "$person_dir")
  index_file="$person_dir/index.md"
  headshot_file="$person_dir/headshot.jpg"
  
  if [ ! -f "$index_file" ]; then
    continue
  fi
  
  # Check if this person has a headshot file
  if [ ! -f "$headshot_file" ]; then
    echo "Removing image parameter for $person_name (no headshot found)..."
    
    # Remove the image parameter line entirely
    sed -i '' '/^image:/d' "$index_file"
    
    echo "  ✓ Removed image parameter (will use sitewide placeholder)"
  else
    echo "  $person_name has headshot, keeping as is"
  fi
done

echo "Done! Placeholder images fixed." 