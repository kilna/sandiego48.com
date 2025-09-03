#!/usr/bin/env python3
"""
Update film index.md files to use downloaded images instead of placeholders.

This script scans all film directories and updates the image field in index.md
files to use the most appropriate downloaded image (poster first, then still, then placeholder).
"""

import os
import re
from pathlib import Path
from typing import List, Optional


def get_available_images(film_dir: Path) -> List[str]:
    """Get list of available image files in a film directory."""
    image_files = []
    for ext in ['.jpg', '.jpeg', '.png']:
        image_files.extend(film_dir.glob(f"*{ext}"))
        image_files.extend(film_dir.glob(f"*{ext.upper()}"))
    
    return [f.name for f in image_files]


def prioritize_image(image_files: List[str]) -> Optional[str]:
    """
    Prioritize images: poster first, then still, then BTS.
    Returns the best image filename or None if no suitable image.
    """
    if not image_files:
        return None
    
    # Look for poster first (highest priority)
    poster_files = [f for f in image_files if f.startswith('poster-')]
    if poster_files:
        # Sort by number to get the first poster
        poster_files.sort(key=lambda x: int(re.search(r'poster-(\d+)', x).group(1)) if re.search(r'poster-(\d+)', x) else 0)
        return poster_files[0]
    
    # Look for still images second
    still_files = [f for f in image_files if f.startswith('still-')]
    if still_files:
        # Sort by number to get the first still
        still_files.sort(key=lambda x: int(re.search(r'still-(\d+)', x).group(1)) if re.search(r'still-(\d+)', x) else 0)
        return still_files[0]
    
    # Look for BTS images third
    bts_files = [f for f in image_files if f.startswith('bts-')]
    if bts_files:
        # Sort by number to get the first BTS
        bts_files.sort(key=lambda x: int(re.search(r'bts-(\d+)', x).group(1)) if re.search(r'bts-(\d+)', x) else 0)
        return bts_files[0]
    
    # If no categorized images, return the first image file
    return image_files[0]


def update_film_image(film_dir: Path, dry_run: bool = False) -> bool:
    """
    Update a film's index.md to use the best available image.
    Returns True if updated, False if no update needed.
    """
    index_file = film_dir / "index.md"
    if not index_file.exists():
        print(f"  No index.md found in {film_dir.name}")
        return False
    
    # Read current index.md
    with open(index_file, 'r') as f:
        content = f.read()
    
    # Check if it already has a non-placeholder image
    if 'image:' in content and 'placeholder-poster' not in content:
        print(f"  {film_dir.name}: Already has non-placeholder image")
        return False
    
    # Get available images
    available_images = get_available_images(film_dir)
    if not available_images:
        print(f"  {film_dir.name}: No images found")
        return False
    
    # Choose the best image
    best_image = prioritize_image(available_images)
    if not best_image:
        print(f"  {film_dir.name}: Could not determine best image")
        return False
    
    # Check if the image is already set correctly
    if f'image: "{best_image}"' in content:
        print(f"  {film_dir.name}: Already using best image {best_image}")
        return False
    
    # Update the image field
    if 'image:' in content:
        # Replace existing image field
        new_content = re.sub(r'image: "[^"]*"', f'image: "{best_image}"', content)
    else:
        # Add image field after title
        new_content = re.sub(r'(title: "[^"]*")', f'\\1\nimage: "{best_image}"', content)
    
    if new_content != content:
        if dry_run:
            print(f"  {film_dir.name}: Would update image to {best_image}")
        else:
            # Write updated content
            with open(index_file, 'w') as f:
                f.write(new_content)
            print(f"  {film_dir.name}: Updated image to {best_image}")
        return True
    else:
        print(f"  {film_dir.name}: No changes needed")
        return False


def main():
    """Update all film index.md files."""
    films_dir = Path("content/films")
    if not films_dir.exists():
        print("Error: content/films directory not found")
        return
    
    # Get all film directories
    film_dirs = [d for d in films_dir.iterdir() if d.is_dir() and d.name.startswith('2025-')]
    film_dirs.sort()
    
    print(f"Found {len(film_dirs)} film directories")
    print("=" * 50)
    
    updated_count = 0
    total_count = 0
    
    for film_dir in film_dirs:
        print(f"Processing: {film_dir.name}")
        total_count += 1
        
        if update_film_image(film_dir, dry_run=False):
            updated_count += 1
        
        print()
    
    print("=" * 50)
    print(f"Update complete!")
    print(f"  Updated: {updated_count} films")
    print(f"  No changes needed: {total_count - updated_count} films")
    print(f"  Total processed: {total_count} films")
    
    if updated_count > 0:
        print("\nNext steps:")
        print("1. Review the updated index.md files")
        print("2. Commit the changes: git add . && git commit -m 'Update film images to use downloaded media'")
        print("3. Test the Hugo site: hugo --minify")


if __name__ == "__main__":
    main()
