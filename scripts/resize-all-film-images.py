#!/usr/bin/env python3
"""
Resize all existing film images to 1920x1920 or smaller dimensions.
This ensures consistent image sizes across the site and reduces repository size.
"""

import subprocess
import sys
from pathlib import Path

def resize_image_to_standard_size(image_path: Path) -> bool:
    """
    Resize image to standard dimensions (1920x1920 or smaller).
    Returns True if image was resized, False if no resize was needed.
    """
    try:
        # Check if ImageMagick is available
        try:
            subprocess.run(['convert', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Error: ImageMagick not available. Please install: brew install imagemagick")
            return False
        
        # Get current image dimensions
        result = subprocess.run(['identify', '-format', '%wx%h', str(image_path)], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: Could not get image dimensions for {image_path.name}")
            return False
        
        current_dimensions = result.stdout.strip()
        width, height = map(int, current_dimensions.split('x'))
        
        # Check if image needs resizing (only if dimensions are too large)
        needs_resize = (width > 1920 or height > 1920)
        
        if not needs_resize:
            print(f"  {image_path.name}: {width}x{height} (no resize needed)")
            return False
        
        print(f"  {image_path.name}: {width}x{height} -> resizing to 1920x1920 or smaller...")
        
        # Create backup of original
        backup_path = image_path.with_suffix(image_path.suffix + '.original')
        image_path.rename(backup_path)
        
        # Use ImageMagick to resize the image
        # Resize to fit within 1920x1920 while maintaining aspect ratio
        cmd = [
            'convert', str(backup_path),
            '-resize', '1920x1920>',  # Resize if larger, maintain aspect ratio
            '-quality', '85',          # Good quality, reasonable file size
            str(image_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Warning: ImageMagick resize failed: {result.stderr}")
            # Restore original if resize failed
            backup_path.rename(image_path)
            return False
        
        # Get new dimensions
        result = subprocess.run(['identify', '-format', '%wx%h', str(image_path)], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            new_dimensions = result.stdout.strip()
            print(f"    Resized to {new_dimensions}")
        
        # Get file sizes
        old_size = backup_path.stat().st_size / (1024 * 1024)
        new_size = image_path.stat().st_size / (1024 * 1024)
        print(f"    File size: {old_size:.1f}MB -> {new_size:.1f}MB")
        
        # Remove backup if resize was successful
        backup_path.unlink()
        return True
        
    except Exception as e:
        print(f"  Warning: Error during image resize: {e}")
        # Try to restore original if something went wrong
        try:
            if backup_path.exists():
                backup_path.rename(image_path)
        except:
            pass
        return False

def main():
    """Resize all film images in the content/films directory."""
    films_dir = Path("content/films")
    
    if not films_dir.exists():
        print("Error: content/films directory not found")
        sys.exit(1)
    
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png'}
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(films_dir.rglob(f"*{ext}"))
        image_files.extend(films_dir.rglob(f"*{ext.upper()}"))
    
    if not image_files:
        print("No image files found in content/films directory")
        return
    
    print(f"Found {len(image_files)} image files to process")
    print("=" * 50)
    
    resized_count = 0
    skipped_count = 0
    
    for image_path in sorted(image_files):
        print(f"Processing: {image_path.relative_to(films_dir)}")
        
        if resize_image_to_standard_size(image_path):
            resized_count += 1
        else:
            skipped_count += 1
        
        print()
    
    print("=" * 50)
    print(f"Resize complete!")
    print(f"  Resized: {resized_count} images")
    print(f"  Skipped: {skipped_count} images (already correct size)")
    print(f"  Total: {len(image_files)} images")
    
    if resized_count > 0:
        print("\nNext steps:")
        print("1. Review the resized images")
        print("2. Commit the changes: git add . && git commit -m 'Resize all film images to 1920x1920'")
        print("3. Clean git history: git filter-repo --path content/films --invert-paths --force")

if __name__ == "__main__":
    main()
