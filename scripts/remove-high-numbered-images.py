#!/usr/bin/env python3
"""
Remove any film images numbered >19 as a one-off cleanup.

This script removes images with numbers higher than 19 (like bts-20.jpg, still-25.png, etc.)
so we can re-download without the extra images.
"""

import os
import re
from pathlib import Path
import argparse
from typing import List


def find_high_numbered_images(film_dir: Path) -> List[Path]:
    """
    Find images in a film directory with numbers >19.
    Returns list of file paths to remove.
    """
    high_numbered = []
    
    # Get all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(film_dir.glob(ext))
    
    for image_file in image_files:
        filename = image_file.name
        
        # Check if this is a numbered image (bts-1.jpg, poster-2.png, etc.)
        match = re.match(r'^(bts|poster|still|group)-(\d+)\.(jpg|jpeg|png)$', filename)
        if match:
            image_type, number_str, extension = match.groups()
            number = int(number_str)
            
            # If the number is > 19, mark for removal
            if number > 19:
                high_numbered.append(image_file)
                print(f"  Found high-numbered image: {image_file.name} (number {number})")
    
    return high_numbered


def cleanup_film_directory(film_dir: Path, dry_run: bool = False) -> int:
    """
    Clean up high-numbered images in a film directory.
    Returns the number of files removed.
    """
    print(f"Processing {film_dir.name}...")
    
    high_numbered = find_high_numbered_images(film_dir)
    
    if not high_numbered:
        print(f"  No high-numbered images found")
        return 0
    
    removed_count = 0
    for image_path in high_numbered:
        if dry_run:
            print(f"  Would remove: {image_path.name}")
        else:
            try:
                image_path.unlink()
                print(f"  Removed: {image_path.name}")
                removed_count += 1
            except Exception as e:
                print(f"  Error removing {image_path.name}: {e}")
    
    return removed_count


def main():
    parser = argparse.ArgumentParser(description="Remove film images numbered >19 as a one-off cleanup")
    parser.add_argument("--base-dir", default="content/films", help="Root directory for film images")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without actually removing")
    args = parser.parse_args()
    
    base_dir = Path(args.base_dir)
    if not base_dir.exists():
        print(f"Error: Directory {base_dir} does not exist")
        return 1
    
    # Find all film directories
    film_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith('2025-')]
    print(f"Found {len(film_dirs)} film directories")
    
    total_removed = 0
    for film_dir in sorted(film_dirs):
        removed = cleanup_film_directory(film_dir, dry_run=args.dry_run)
        total_removed += removed
    
    print(f"\nCleanup complete!")
    if args.dry_run:
        print(f"Would remove {total_removed} high-numbered images")
    else:
        print(f"Removed {total_removed} high-numbered images")
    
    return 0


if __name__ == "__main__":
    exit(main())
