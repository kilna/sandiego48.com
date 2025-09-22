#!/usr/bin/env python3
"""
Script to standardize all film poster images to poster.<ext> and update
the image field in each film's index.md file.
"""

import os
import sys
import re
import shutil
from pathlib import Path

def get_current_image_from_frontmatter(film_dir):
    """Extract the current image field from a film's index.md frontmatter."""
    index_path = film_dir / "index.md"
    if not index_path.exists():
        return None
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split frontmatter from content
    if not content.startswith('---'):
        return None
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None
    
    # Simple regex to find image field
    image_match = re.search(r'^image:\s*(.+)$', parts[1], re.MULTILINE)
    if image_match:
        return image_match.group(1).strip().strip('"\'')
    return None

def update_image_field_in_frontmatter(film_dir, new_image_name):
    """Update the image field in a film's index.md frontmatter."""
    index_path = film_dir / "index.md"
    if not index_path.exists():
        return False
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split frontmatter from content
    if not content.startswith('---'):
        return False
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return False
    
    # Replace the image field
    frontmatter = parts[1]
    new_frontmatter = re.sub(
        r'^image:\s*(.+)$',
        f'image: {new_image_name}',
        frontmatter,
        flags=re.MULTILINE
    )
    
    # Reconstruct the file
    new_content = f"---{new_frontmatter}---{parts[2]}"
    
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True

def standardize_poster_in_directory(film_dir, dry_run=True):
    """Standardize the poster image name in a film directory."""
    film_name = film_dir.name
    print(f"\nProcessing {film_name}...")
    
    # Get the current image from frontmatter
    current_image = get_current_image_from_frontmatter(film_dir)
    if not current_image:
        print(f"  No image field found in frontmatter, skipping")
        return
    
    current_image_path = film_dir / current_image
    if not current_image_path.exists():
        print(f"  Current image file '{current_image}' not found, skipping")
        return
    
    # Get the file extension
    file_ext = current_image_path.suffix.lower()
    if not file_ext:
        print(f"  No file extension found for '{current_image}', skipping")
        return
    
    # Create new standardized name
    new_image_name = f"poster{file_ext}"
    new_image_path = film_dir / new_image_name
    
    print(f"  Current image: {current_image}")
    print(f"  New image: {new_image_name}")
    
    # Check if already standardized
    if current_image == new_image_name:
        print(f"  Already standardized, no change needed")
        return
    
    if dry_run:
        print(f"  [DRY RUN] Would rename: {current_image} -> {new_image_name}")
        print(f"  [DRY RUN] Would update index.md image field")
    else:
        try:
            # Rename the file
            shutil.move(str(current_image_path), str(new_image_path))
            print(f"  Renamed: {current_image} -> {new_image_name}")
            
            # Update the frontmatter
            if update_image_field_in_frontmatter(film_dir, new_image_name):
                print(f"  Updated index.md image field")
            else:
                print(f"  Error updating index.md image field")
                
        except Exception as e:
            print(f"  Error: {e}")

def main():
    """Main function to standardize all film poster names."""
    content_dir = Path("content/films")
    if not content_dir.exists():
        print("content/films directory not found")
        sys.exit(1)
    
    # Check if this is a dry run
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        dry_run = False
        print("EXECUTING - Files will be renamed and frontmatter updated!")
    else:
        print("DRY RUN MODE - No files will be changed. Use --execute to actually rename files.")
    
    # Process each film directory
    film_dirs = [d for d in content_dir.iterdir() if d.is_dir() and d.name != "_index.md"]
    film_dirs.sort()
    
    print(f"Found {len(film_dirs)} film directories")
    
    for film_dir in film_dirs:
        standardize_poster_in_directory(film_dir, dry_run)
    
    print(f"\nSummary:")
    if dry_run:
        print("This was a dry run. Use --execute to actually rename files and update frontmatter.")
    else:
        print("Files have been renamed and frontmatter has been updated.")

if __name__ == "__main__":
    main()
