#!/bin/bash

# Fix people names to proper case using CSV data as source of truth

set -e

echo "Fixing people names to proper case..."

# CSV file path
csv_file="/Users/kilna/Library/CloudStorage/GoogleDrive-sandiego@48hourfilm.com/My Drive/Events/Open Auditions/2025-contacts/Audition_Sign-In.csv"

if [ ! -f "$csv_file" ]; then
  echo "Error: CSV file not found at $csv_file"
  exit 1
fi

# Create a temporary file for name mappings
temp_mappings=$(mktemp)

# Extract names from CSV (second column is Name)
# Skip header row and extract names, handling potential quotes
tail -n +2 "$csv_file" | cut -d',' -f2 | sed 's/^"//;s/"$//' | while read -r csv_name; do
  if [ -n "$csv_name" ]; then
    # Convert to slug for matching
    slug=$(echo "$csv_name" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
    echo "$slug|$csv_name" >> "$temp_mappings"
  fi
done

# Process each people directory
for person_dir in content/people/*/; do
  if [ ! -d "$person_dir" ]; then
    continue
  fi
  
  person_slug=$(basename "$person_dir")
  index_file="$person_dir/index.md"
  
  if [ ! -f "$index_file" ]; then
    continue
  fi
  
  # Find matching name from CSV
  csv_name=$(grep "^$person_slug|" "$temp_mappings" | cut -d'|' -f2)
  
  if [ -n "$csv_name" ]; then
    echo "Fixing name for $person_slug -> $csv_name"
    
    # Update the title in the frontmatter
    sed -i '' "s/^title: \".*\"/title: \"$csv_name\"/" "$index_file"
    
    # Update the "About" section
    sed -i '' "s/^## About .*/## About $csv_name/" "$index_file"
    sed -i '' "s/^.* is an actor participating in the San Diego 48 Hour Film Project\./$csv_name is an actor participating in the San Diego 48 Hour Film Project./" "$index_file"
    
    echo "  ✓ Updated to: $csv_name"
  else
    echo "  No CSV match found for $person_slug, keeping as is"
  fi
done

# Clean up
rm "$temp_mappings"

echo "Done! People names fixed to proper case." 