#!/usr/bin/env python3
"""
Rename film images to use film slug format and update index.md files.

This script:
1. Renames new untracked images to <film-slug>.<ext> format
2. Copies existing poster images to <film-slug>.<ext> format
3. Updates index.md files to use the new slug-based image names
"""

import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple


def get_film_slug_from_directory(film_dir: Path) -> str:
    """Extract the film slug from the directory name (everything after the year prefix)."""
    dir_name = film_dir.name
    # Remove the year prefix (e.g., "2025-")
    if dir_name.startswith("2025-"):
        return dir_name[5:]  # Remove "2025-" prefix
    return dir_name


def find_new_untracked_images() -> List[Tuple[Path, str]]:
    """Find all new untracked image files and return (file_path, film_slug) tuples."""
    new_images = []
    
    # Get all untracked image files
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error running git status")
        return []
    
    for line in result.stdout.strip().split('\n'):
        if not line.startswith('??'):
            continue
        
        file_path = Path(line[3:].strip())  # Remove "?? " prefix
        if not file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            continue
        
        # Extract film directory and slug
        film_dir = file_path.parent
        if film_dir.name.startswith('2025-'):
            film_slug = get_film_slug_from_directory(film_dir)
            new_images.append((file_path, film_slug))
    
    return new_images


def find_existing_posters() -> List[Tuple[Path, str]]:
    """Find all existing poster files and return (file_path, film_slug) tuples."""
    existing_posters = []
    films_dir = Path("content/films")
    
    for film_dir in films_dir.iterdir():
        if not film_dir.is_dir() or not film_dir.name.startswith('2025-'):
            continue
        
        film_slug = get_film_slug_from_directory(film_dir)
        
        # Look for poster files
        for poster_file in film_dir.glob("poster-*.jpg"):
            existing_posters.append((poster_file, film_slug))
        for poster_file in film_dir.glob("poster-*.png"):
            existing_posters.append((poster_file, film_slug))
    
    return existing_posters


def update_film_index_image(film_dir: Path, new_image_name: str) -> bool:
    """Update the film's index.md to use the new image name."""
    index_file = film_dir / "index.md"
    if not index_file.exists():
        return False
    
    try:
        content = index_file.read_text(encoding='utf-8')
        
        # Find and update the image field
        image_match = re.search(r'^image:\s*["\']?([^"\'\s]+)["\']?\s*$', content, re.MULTILINE)
        if image_match:
            old_line = image_match.group(0)
            new_line = f'image: {new_image_name}'
            updated_content = content.replace(old_line, new_line)
            
            # Write back to file
            index_file.write_text(updated_content, encoding='utf-8')
            print(f"  Updated {film_dir.name}/index.md: image → {new_image_name}")
            return True
        else:
            print(f"  Warning: No image field found in {film_dir.name}/index.md")
            return False
            
    except Exception as e:
        print(f"  Error updating {film_dir.name}/index.md: {e}")
        return False


def rename_new_images():
    """Rename new untracked images to slug format."""
    print("Processing new untracked images...")
    new_images = find_new_untracked_images()
    
    if not new_images:
        print("No new untracked images found.")
        return
    
    print(f"Found {len(new_images)} new images to rename:")
    
    for file_path, film_slug in new_images:
        film_dir = file_path.parent
        new_name = f"{film_slug}{file_path.suffix}"
        new_path = film_dir / new_name
        
        print(f"  Renaming {file_path.name} → {new_name}")
        
        try:
            # Move the file to the new name
            file_path.rename(new_path)
            
            # Update the index.md file
            update_film_index_image(film_dir, new_name)
            
        except Exception as e:
            print(f"    Error: {e}")


def copy_existing_posters():
    """Copy existing poster images to slug format."""
    print("\nProcessing existing poster images...")
    existing_posters = find_existing_posters()
    
    if not existing_posters:
        print("No existing poster images found.")
        return
    
    print(f"Found {len(existing_posters)} existing posters to copy:")
    
    for poster_path, film_slug in existing_posters:
        film_dir = poster_path.parent
        new_name = f"{film_slug}{poster_path.suffix}"
        new_path = film_dir / new_name
        
        # Skip if the slug-named file already exists
        if new_path.exists():
            print(f"  Skipping {poster_path.name} → {new_name} (already exists)")
            continue
        
        print(f"  Copying {poster_path.name} → {new_name}")
        
        try:
            # Copy the file to the new name
            shutil.copy2(poster_path, new_path)
            
            # Update the index.md file
            update_film_index_image(film_dir, new_name)
            
        except Exception as e:
            print(f"    Error: {e}")


def main():
    """Main function to rename and copy all film images."""
    print("Film Image Renaming Script")
    print("=" * 50)
    
    # Process new untracked images
    rename_new_images()
    
    # Process existing poster images
    copy_existing_posters()
    
    print("\nDone!")


if __name__ == "__main__":
    import subprocess
    main()
