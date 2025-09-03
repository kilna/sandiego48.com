#!/usr/bin/env python3
"""
Script to move images from old redirect directories to new slug-based directories.
Since the old directories are now just redirects, we don't need the image files in them.
"""

import os
import shutil
from pathlib import Path

def move_images_from_old_to_new():
    """Move images from old 'the-' directories to new slug-based directories."""
    
    # Define the old to new directory mappings
    mappings = [
        ("2025-the-2880-minute-movie-makers-i-plead-the-fifth", "2025-2880-minute-movie-makers-i-plead-the-fifth"),
        ("2025-the-filmigos-fire-in-my-heart", "2025-filmigos-fire-in-my-heart"),
        ("2025-the-k-concern-tango-of-the-unseen", "2025-k-concern-tango-of-the-unseen"),
        ("2025-the-super-pas-dystopian-cowboys", "2025-super-pas-dystopian-cowboys"),
        ("2025-the-underdogs-crimson-hour", "2025-underdogs-crimson-hour"),
    ]
    
    films_dir = Path("content/films")
    moved_count = 0
    skipped_count = 0
    
    for old_dir, new_dir in mappings:
        old_path = films_dir / old_dir
        new_path = films_dir / new_dir
        
        if not old_path.exists():
            print(f"Warning: Old directory {old_dir} does not exist")
            continue
            
        if not new_path.exists():
            print(f"Warning: New directory {new_dir} does not exist")
            continue
        
        print(f"\nProcessing {old_dir} -> {new_dir}")
        
        # Find all image files in the old directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
        old_images = []
        
        for file_path in old_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                old_images.append(file_path)
        
        if not old_images:
            print(f"  No images found in {old_dir}")
            continue
        
        print(f"  Found {len(old_images)} images in old directory")
        
        # Move each image to the new directory if it doesn't already exist
        for old_image in old_images:
            # Calculate relative path from old directory
            rel_path = old_image.relative_to(old_path)
            new_image_path = new_path / rel_path
            
            if new_image_path.exists():
                print(f"    Skipping {rel_path.name} - already exists in new directory")
                skipped_count += 1
            else:
                # Create parent directories if they don't exist
                new_image_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.move(str(old_image), str(new_image_path))
                    print(f"    Moved {rel_path.name} to new directory")
                    moved_count += 1
                except Exception as e:
                    print(f"    Error moving {rel_path.name}: {e}")
    
    print(f"\nMigration Summary:")
    print(f"Images moved: {moved_count}")
    print(f"Images skipped (already exist): {skipped_count}")

def cleanup_old_directories():
    """Remove old directories after images have been moved."""
    
    old_dirs = [
        "2025-the-2880-minute-movie-makers-i-plead-the-fifth",
        "2025-the-filmigos-fire-in-my-heart", 
        "2025-the-k-concern-tango-of-the-unseen",
        "2025-the-super-pas-dystopian-cowboys",
        "2025-the-underdogs-crimson-hour",
    ]
    
    films_dir = Path("content/films")
    removed_count = 0
    
    for old_dir in old_dirs:
        old_path = films_dir / old_dir
        
        if old_path.exists():
            # Check if there are any remaining files (should only be index.md for redirects)
            remaining_files = list(old_path.rglob('*'))
            if len(remaining_files) <= 1:  # Only index.md should remain
                try:
                    shutil.rmtree(old_path)
                    print(f"Removed old directory: {old_dir}")
                    removed_count += 1
                except Exception as e:
                    print(f"Error removing {old_dir}: {e}")
            else:
                print(f"Warning: {old_dir} still has {len(remaining_files)} files, not removing")
        else:
            print(f"Directory {old_dir} already removed")
    
    print(f"\nCleanup Summary:")
    print(f"Directories removed: {removed_count}")

def main():
    """Main function."""
    print("Starting image migration from old redirect directories...")
    
    # First move the images
    move_images_from_old_to_new()
    
    print("\n" + "="*50)
    
    # Ask user if they want to clean up old directories
    response = input("\nDo you want to remove the old directories now? (y/N): ")
    if response.lower() in ['y', 'yes']:
        cleanup_old_directories()
    else:
        print("Old directories preserved. You can run cleanup later with:")
        print("python3 scripts/move-images.py --cleanup")

if __name__ == "__main__":
    main()
