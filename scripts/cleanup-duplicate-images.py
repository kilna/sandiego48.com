#!/usr/bin/env python3
"""
Clean up duplicate images with incorrect numbering.

This script removes duplicate images that have numbers in the hundreds/thousands
(like bts-201.jpg, poster-201.png, etc.) while keeping the original correctly
numbered images (like bts-1.jpg, poster-1.png, etc.).
"""

import os
import re
from pathlib import Path
import argparse
from typing import List, Tuple


def find_duplicate_images(film_dir: Path) -> List[Tuple[Path, Path]]:
    """
    Find duplicate images in a film directory.
    Returns list of (original_path, duplicate_path) tuples.
    """
    duplicates = []
    
    # Get all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(film_dir.glob(ext))
    
    # Group files by type and look for duplicates
    for image_file in image_files:
        filename = image_file.name
        
        # Check if this is a numbered image (bts-1.jpg, poster-2.png, etc.)
        match = re.match(r'^(bts|poster|still)-(\d+)\.(jpg|jpeg|png)$', filename)
        if not match:
            continue
            
        image_type, number_str, extension = match.groups()
        number = int(number_str)
        
        # If the number is > 100, it's likely a duplicate
        if number > 100:
            # Look for the original file with the same type and a reasonable number
            original_number = number % 100  # Extract the original number
            original_filename = f"{image_type}-{original_number}.{extension}"
            original_path = film_dir / original_filename
            
            if original_path.exists():
                duplicates.append((original_path, image_file))
                print(f"  Found duplicate: {image_file.name} -> {original_filename}")
    
    return duplicates


def cleanup_film_directory(film_dir: Path, dry_run: bool = False) -> int:
    """
    Clean up duplicate images in a film directory.
    Returns the number of files removed.
    """
    print(f"Processing {film_dir.name}...")
    
    duplicates = find_duplicate_images(film_dir)
    
    if not duplicates:
        print(f"  No duplicates found")
        return 0
    
    removed_count = 0
    for original_path, duplicate_path in duplicates:
        if dry_run:
            print(f"  Would remove: {duplicate_path.name}")
        else:
            try:
                duplicate_path.unlink()
                print(f"  Removed: {duplicate_path.name}")
                removed_count += 1
            except Exception as e:
                print(f"  Error removing {duplicate_path.name}: {e}")
    
    return removed_count


def main():
    parser = argparse.ArgumentParser(description="Clean up duplicate film images with incorrect numbering")
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
        print(f"Would remove {total_removed} duplicate files")
    else:
        print(f"Removed {total_removed} duplicate files")
    
    return 0


if __name__ == "__main__":
    exit(main())
