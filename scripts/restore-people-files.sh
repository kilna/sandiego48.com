#!/bin/bash

# Restore all people files to proper format

set -e

echo "Restoring people files to proper format..."

# Find all people directories
for person_dir in content/people/*/; do
  if [ ! -d "$person_dir" ]; then
    continue
  fi
  
  person_name=$(basename "$person_dir")
  index_file="$person_dir/index.md"
  
  if [ ! -f "$index_file" ]; then
    continue
  fi
  
  echo "Restoring $person_name..."
  
  # Extract the person's name for the title
  title=$(echo "$person_name" | sed 's/-/ /g' | sed 's/\b\w/\U&/g')
  
  # Create a clean file
  cat > "$index_file" << EOF
---
title: "$title"
image: "headshot.jpg"
roles: ["Actor"]
draft: false
contact_email: ""
contact_phone: ""
open_auditions:
  2025:
    monologue: ""
    audition_number: ""
credits: []
social: []
EOF
  
  # Add image_credit if this person has edited-* images
  has_edited_images=false
  for file in "$person_dir"edited-*; do
    if [ -f "$file" ]; then
      has_edited_images=true
      break
    fi
  done
  
  if [ "$has_edited_images" = true ]; then
    echo "image_credit: \"Headshot by [Jon Medel](https://www.jonmedel.com)\"" >> "$index_file"
  fi
  
  # Close frontmatter and add content
  cat >> "$index_file" << EOF
---

## About $title

$title is an actor participating in the San Diego 48 Hour Film Project.
EOF
  
  echo "  ✓ Restored"
done

echo "Done! All people files restored." 