#!/usr/bin/env python3
"""
Script to remove all images from film directories except the main poster image
specified in the image: field of each film's index.md file.
"""

import os
import sys
import re
from pathlib import Path

def get_image_from_frontmatter(film_dir):
    """Extract the image field from a film's index.md frontmatter."""
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

def clean_film_directory(film_dir, dry_run=True):
    """Remove all images except the main poster image from a film directory."""
    film_name = film_dir.name
    print(f"\nProcessing {film_name}...")
    
    # Get the main image from frontmatter
    main_image = get_image_from_frontmatter(film_dir)
    if not main_image:
        print(f"  No image field found in frontmatter, skipping")
        return
    
    print(f"  Main image: {main_image}")
    
    # Find all image files in the directory
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
    image_files = []
    
    for file_path in film_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)
    
    if not image_files:
        print(f"  No image files found")
        return
    
    print(f"  Found {len(image_files)} image files:")
    for img_file in image_files:
        print(f"    - {img_file.name}")
    
    # Remove images that are not the main image
    removed_count = 0
    for img_file in image_files:
        if img_file.name != main_image:
            if dry_run:
                print(f"  [DRY RUN] Would remove: {img_file.name}")
            else:
                try:
                    img_file.unlink()
                    print(f"  Removed: {img_file.name}")
                except Exception as e:
                    print(f"  Error removing {img_file.name}: {e}")
            removed_count += 1
    
    if dry_run:
        print(f"  [DRY RUN] Would remove {removed_count} files")
    else:
        print(f"  Removed {removed_count} files")

def main():
    """Main function to clean all film directories."""
    content_dir = Path("content/films")
    if not content_dir.exists():
        print("content/films directory not found")
        sys.exit(1)
    
    # Check if this is a dry run
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        dry_run = False
        print("EXECUTING - Files will be permanently deleted!")
    else:
        print("DRY RUN MODE - No files will be deleted. Use --execute to actually delete files.")
    
    # Process each film directory
    film_dirs = [d for d in content_dir.iterdir() if d.is_dir() and d.name != "_index.md"]
    film_dirs.sort()
    
    print(f"Found {len(film_dirs)} film directories")
    
    total_removed = 0
    for film_dir in film_dirs:
        clean_film_directory(film_dir, dry_run)
    
    print(f"\nSummary:")
    if dry_run:
        print("This was a dry run. Use --execute to actually delete files.")
    else:
        print("Files have been deleted.")

if __name__ == "__main__":
    main()
