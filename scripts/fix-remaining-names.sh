#!/bin/bash

# Fix remaining people names with educated guesses

set -e

echo "Fixing remaining people names with educated guesses..."

# Function to get proper name for a slug
get_proper_name() {
  local slug="$1"
  case "$slug" in
    "alex-niell") echo "Alex Niell" ;;
    "brent-bokovoy") echo "Brent Bokovoy" ;;
    "carly-delso-saavedra") echo "Carly Delso-Saavedra" ;;
    "harry-kakatsakis") echo "Harry Kakatsakis" ;;
    "jordan-jacobo") echo "Jordan Jacobo" ;;
    "mike-egbert") echo "Mike Egbert" ;;
    "scotty-rodriguez") echo "Scotty Rodriguez" ;;
    *) echo "" ;;
  esac
}

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
  
  # Get proper name for this person
  proper_name=$(get_proper_name "$person_slug")
  
  if [ -n "$proper_name" ]; then
    echo "Fixing name for $person_slug -> $proper_name"
    
    # Update the title in the frontmatter
    sed -i '' "s/^title: \".*\"/title: \"$proper_name\"/" "$index_file"
    
    # Update the "About" section
    sed -i '' "s/^## About .*/## About $proper_name/" "$index_file"
    sed -i '' "s/^.* is an actor participating in the San Diego 48 Hour Film Project\./$proper_name is an actor participating in the San Diego 48 Hour Film Project./" "$index_file"
    
    echo "  ✓ Updated to: $proper_name"
  else
    echo "  No mapping for $person_slug, keeping as is"
  fi
done

echo "Done! Remaining people names fixed." 