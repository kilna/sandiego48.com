#!/usr/bin/env python3
"""
Update film index.md files to use actual poster images instead of placeholders.

This script scans all film directories and updates the image field in index.md
to use the highest-numbered poster file from the CDN directory if one exists, 
otherwise keeps the current image.
"""

import re
import shutil
from pathlib import Path
from typing import List, Optional


def find_highest_poster(film_slug: str) -> Optional[tuple[str, Path]]:
    """Find the highest-numbered poster file in the CDN directory for a film."""
    cdn_dir = Path("cdn") / "films" / film_slug
    if not cdn_dir.exists():
        return None
    
    poster_files = []
    
    for file_path in cdn_dir.glob("poster-*.jpg"):
        # Extract number from filename like "poster-001.jpg" (3-digit padding)
        match = re.match(r'poster-(\d+)\.jpg$', file_path.name)
        if match:
            number = int(match.group(1))
            poster_files.append((number, file_path.name, file_path))
    
    if not poster_files:
        return None
    
    # Return the highest-numbered poster (filename, file_path)
    poster_files.sort(key=lambda x: x[0], reverse=True)
    return (poster_files[0][1], poster_files[0][2])


def update_film_image(film_dir: Path) -> bool:
    """Update a single film's index.md and copy the best poster from CDN to content directory."""
    index_file = film_dir / "index.md"
    if not index_file.exists():
        return False
    
    try:
        content = index_file.read_text(encoding='utf-8')
        
        # Extract film slug from directory name (e.g., "2025-team-name" -> "2025-team-name")
        film_slug = film_dir.name
        
        # Find the highest-numbered poster in CDN directory
        poster_result = find_highest_poster(film_slug)
        if not poster_result:
            return False  # No poster files found in CDN
        
        best_poster_filename, best_poster_path = poster_result
        
        # Copy the poster from CDN to content directory
        dest_path = film_dir / best_poster_filename
        if not dest_path.exists() or dest_path.stat().st_mtime < best_poster_path.stat().st_mtime:
            print(f"  Copying {best_poster_filename} from CDN to content directory...")
            shutil.copy2(best_poster_path, dest_path)
        
        # Check if image field already exists
        image_match = re.search(r'^image:\s*["\']?([^"\'\s]+)["\']?\s*$', content, re.MULTILINE)
        if image_match:
            current_image = image_match.group(1)
            if current_image == best_poster_filename:
                return False  # Already using the correct image
            
            # Update the existing image field - handle both quoted and unquoted values
            old_line = image_match.group(0)  # The entire matched line
            new_line = f'image: {best_poster_filename}'
            updated_content = content.replace(old_line, new_line)
            print(f"  Updated {film_dir.name}: {current_image} → {best_poster_filename}")
        else:
            # Add image field to frontmatter
            frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not frontmatter_match:
                return False  # No frontmatter found
            
            frontmatter = frontmatter_match.group(1)
            if frontmatter.strip():
                updated_frontmatter = frontmatter.rstrip() + f"\nimage: {best_poster_filename}\n"
            else:
                updated_frontmatter = f"image: {best_poster_filename}\n"
            
            updated_content = content.replace(frontmatter, updated_frontmatter)
            print(f"  Added image to {film_dir.name}: {best_poster_filename}")
        
        # Write back to file
        index_file.write_text(updated_content, encoding='utf-8')
        return True
        
    except Exception as e:
        print(f"  Error updating {film_dir.name}: {e}")
        return False


def main():
    """Update all film index.md files to use actual poster images."""
    films_dir = Path("content/films")
    if not films_dir.exists():
        print("Error: content/films directory not found")
        return
    
    updated_count = 0
    total_films = 0
    
    print("Scanning film directories for poster updates...")
    
    for film_dir in films_dir.iterdir():
        if not film_dir.is_dir():
            continue
        
        total_films += 1
        if update_film_image(film_dir):
            updated_count += 1
    
    print(f"\nUpdated {updated_count} out of {total_films} films")
    print("Done!")


if __name__ == "__main__":
    main()