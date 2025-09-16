#!/usr/bin/env python3
"""
Download film images from 48hourfilm.com and save them to the CDN directory structure.

This script looks for URLs in the following formats:
- Still: https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/TeamName/Film%20Stills/48HFP%20San%20Diego%202025%20-%20TeamName%20-%20Film%20Stills%20-%20file%20X.jpg
- BTS: https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/TeamName/Behind%20the%20Scenes%20Pictures/48HFP%20San%20Diego%202025%20-%20TeamName%20-%20Behind%20the%20Scenes%20Pictures%20-%20file%20X.jpg
- Poster: https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/TeamName/Poster/48HFP%20San%20Diego%202025%20-%20TeamName%20-%20Poster%20-%20file%20X.jpg
- Group: https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/TeamName/Group%20Picture/48HFP%20San%20Diego%202025%20-%20TeamName%20-%20Group%20Picture%20-%20file%20X.jpg

Images are saved to the CDN directory structure:
- cdn/films/<film-slug>/poster-001.jpg, poster-002.jpg, etc.
- cdn/films/<film-slug>/still-001.jpg, still-002.jpg, etc.
- cdn/films/<film-slug>/bts-001.jpg, bts-002.jpg, etc.
- cdn/films/<film-slug>/group-001.jpg, group-002.jpg, etc.

The script properly decodes URLs, extracts the file number from the "file X" part,
and uses 3-digit padding for filenames. Images larger than 1920x1920 are automatically
resized to fit within those dimensions while preserving aspect ratio. All images are
converted to JPG format to match gallery specifications. Downloads are processed
in parallel for faster processing. This requires vips to be installed (brew install vips).
"""

import argparse
import csv
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup

# Base URL for team/film pages - CSV is definitive, construct URL from team ID
film_base_url = "https://www.48hourfilm.com/dash/cp/production/team-more-info/"

def load_cookie(cookie_str: str) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    for item in cookie_str.split(";"):
        if not item.strip():
            continue
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        jar.set(name.strip(), value.strip())
    return jar


def classify_image_from_url(url: str) -> str:
    """Return a prefix describing the image type based on the upload URL format."""
    url_lower = url.lower()
    
    if "/film%20stills/" in url_lower or "/film stills/" in url_lower:
        return "still"
    elif "/poster/" in url_lower:
        return "poster"
    elif "/behind%20the%20scenes%20pictures/" in url_lower or "/behind the scenes pictures/" in url_lower:
        return "bts"
    elif "/group%20picture/" in url_lower or "/group picture/" in url_lower:
        return "group"
    else:
        return "unknown"


def extract_number_from_filename(url: str) -> int:
    """Extract the number from a filename like '48HFP San Diego 2025 - TeamName - Film Stills - file 1.jpg'."""
    try:
        # First, properly decode the URL to handle %20 and other encodings
        decoded_url = unquote(url)
        
        # Look for the "file X" pattern in the decoded URL
        match = re.search(r'file (\d+)', decoded_url, re.IGNORECASE)
        if match:
            return int(match.group(1))
            
    except Exception:
        pass
    
    # Default to 1 if we can't parse the number
    return 1


def find_upload_urls(session: requests.Session, film_url: str) -> List[Tuple[str, str]]:
    """Find direct upload URLs in the page content based on specific URL patterns."""
    resp = session.get(film_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
    upload_urls: List[Tuple[str, str]] = []
    
    # Look for all links and check if they match our upload URL patterns
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if not href:
            continue
            
        # Check if this is a direct upload URL
        if href.startswith("https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/"):
            # Classify the image type based on URL format
            image_type = classify_image_from_url(href)
            if image_type != "unknown":
                upload_urls.append((href, image_type))
    
    return upload_urls


def cleanup_old_images_with_wrong_numbers(film_dir: Path, image_type: str, correct_number: int) -> None:
    """
    Remove old images with wrong numbers for the same image type.
    For example, if we're about to create poster-001.jpg, remove any existing poster-002.jpg, poster-003.jpg, etc.
    """
    try:
        # Look for existing images of the same type with different numbers
        for existing_file in film_dir.glob(f"{image_type}-*.jpg"):
            # Extract the number from the filename
            match = re.match(rf'{image_type}-(\d+)\.jpg$', existing_file.name)
            if match:
                existing_number = int(match.group(1))
                # If the number is different from the correct number, remove it
                if existing_number != correct_number:
                    print(f"  Removing old image with wrong number: {existing_file.name}")
                    existing_file.unlink()
    except Exception as e:
        print(f"  Warning: Error cleaning up old images: {e}")


def download_file(session: requests.Session, url: str, dest_path: Path) -> None:
    """Download file to a temporary location, then atomically move to destination."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temporary file in the same directory
    temp_path = dest_path.with_suffix(dest_path.suffix + '.tmp')
    
    try:
        with session.get(url, stream=True) as resp:
            resp.raise_for_status()
            with open(temp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        
        # Atomically move the temporary file to the destination
        temp_path.replace(dest_path)
        
    except Exception:
        # Clean up temporary file on error
        if temp_path.exists():
            temp_path.unlink()
        raise


def get_image_dimensions(image_path: Path) -> Optional[Tuple[int, int]]:
    """Get image dimensions using vips. Returns (width, height) or None if failed."""
    try:
        result = subprocess.run(['vips', 'header', 'image', str(image_path), 'width'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            return None
        
        width = int(result.stdout.strip())
        
        result = subprocess.run(['vips', 'header', 'image', str(image_path), 'height'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            return None
        
        height = int(result.stdout.strip())
        return (width, height)
        
    except Exception:
        return None


def resize_image_with_vips(input_path: Path, output_path: Path, max_dimension: int = 1920) -> bool:
    """
    Resize image using vips if it's larger than max_dimension in any dimension.
    Returns True if resized, False if no resize was needed.
    """
    try:
        # Get current dimensions
        dimensions = get_image_dimensions(input_path)
        if not dimensions:
            print(f"  Warning: Could not get image dimensions for {input_path.name}")
            return False
        
        width, height = dimensions
        
        # Check if resize is needed
        if width <= max_dimension and height <= max_dimension:
            return False
        
        print(f"  Image {input_path.name} is {width}x{height}, resizing to fit within {max_dimension}x{max_dimension}...")
        
        # Create backup of original
        backup_path = input_path.with_suffix(input_path.suffix + '.original')
        input_path.rename(backup_path)
        
        # Use vips to resize the image
        # Calculate new dimensions while maintaining aspect ratio
        if width > height:
            new_width = max_dimension
            new_height = int((height * max_dimension) / width)
        else:
            new_height = max_dimension
            new_width = int((width * max_dimension) / height)
        
        cmd = [
            'vips', 'resize', str(backup_path), str(output_path),
            f'{new_width / width}', f'{new_height / height}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Warning: vips resize failed: {result.stderr}")
            # Restore original if resize failed
            backup_path.rename(input_path)
            return False
        
        # Get new dimensions
        new_dimensions = get_image_dimensions(output_path)
        if new_dimensions:
            print(f"  Resized to {new_dimensions[0]}x{new_dimensions[1]}")
        
        # Remove backup if resize was successful
        backup_path.unlink()
        return True
        
    except Exception as e:
        print(f"  Warning: Error during image resize: {e}")
        # Try to restore original if something went wrong
        try:
            if backup_path.exists():
                backup_path.rename(input_path)
        except:
            pass
        return False


def convert_to_jpg_with_vips(input_path: Path, output_path: Path) -> bool:
    """
    Convert image to JPG format using vips.
    Returns True if conversion was successful, False otherwise.
    """
    try:
        # Check if vips is available
        try:
            subprocess.run(['vips', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"  Warning: vips not available, cannot convert {input_path.name}")
            print(f"  Please install vips: brew install vips")
            return False
        
        # Use vips to convert to JPG with good quality
        cmd = [
            'vips', 'jpegsave', str(input_path), str(output_path),
            '--Q', '90'  # Quality 90
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Warning: vips conversion failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  Warning: Error during image conversion: {e}")
        return False


def process_downloaded_image(dest_path: Path, image_type: str) -> bool:
    """
    Post-process downloaded image: resize if needed and convert to JPG.
    Returns True if processing was successful, False otherwise.
    """
    try:
        # Check if the image is already JPG
        is_jpg = dest_path.suffix.lower() in ['.jpg', '.jpeg']
        
        # Get dimensions to check if resize is needed
        dimensions = get_image_dimensions(dest_path)
        if not dimensions:
            print(f"  Warning: Could not get image dimensions for {dest_path.name}")
            return False
        
        width, height = dimensions
        needs_resize = width > 1920 or height > 1920
        
        # Determine output path
        if is_jpg:
            final_path = dest_path
            temp_path = None
        else:
            # Need to convert to JPG
            final_path = dest_path.with_suffix('.jpg')
            temp_path = dest_path
        
        # Resize if needed
        if needs_resize:
            if is_jpg:
                # Resize in place
                resize_image_with_vips(dest_path, dest_path)
            else:
                # Convert and resize in one step using vips
                print(f"  Converting {dest_path.name} to JPG and resizing...")
                if convert_to_jpg_with_vips(dest_path, final_path):
                    # Now resize the JPG
                    resize_image_with_vips(final_path, final_path)
                    # Remove original non-JPG file
                    temp_path.unlink()
                else:
                    return False
        elif not is_jpg:
            # Just convert to JPG without resizing
            print(f"  Converting {dest_path.name} to JPG...")
            if convert_to_jpg_with_vips(dest_path, final_path):
                # Remove original non-JPG file
                temp_path.unlink()
            else:
                return False
        
        return True
        
    except Exception as e:
        print(f"  Warning: Error during image processing: {e}")
        return False


def is_image_already_downloaded(dest_path: Path) -> bool:
    """
    Check if image is already downloaded with correct dimensions.
    Returns True if image exists and is <= 1920 in all dimensions (already processed).
    """
    if not dest_path.exists():
        return False
    
    try:
        dimensions = get_image_dimensions(dest_path)
        if not dimensions:
            return False
        
        width, height = dimensions
        # Consider it already downloaded if dimensions are correct (<= 1920)
        return width <= 1920 and height <= 1920
        
    except Exception:
        return False


def download_and_process_image(args_tuple: Tuple) -> Tuple[str, bool, str]:
    """
    Download and process a single image. Returns (image_name, success, message).
    This function is designed to be run in parallel.
    """
    film_name, upload_url, image_type, dest_root, args = args_tuple
    
    try:
        if image_type == "unknown":
            return f"{film_name}:{image_type}", False, "Unknown image type"
        
        # Extract the number from the original filename
        file_number = extract_number_from_filename(upload_url)
        
        # Use 3-digit padding for filename, always save as .jpg
        fname = f"{image_type}-{file_number:03d}.jpg"
        
        # Create CDN directory structure: cdn/films/<film-slug>/
        film_dir = dest_root / "films" / film_name
        dest = film_dir / fname
        
        # Clean up any old images with wrong numbers for this image type
        if not args.dry_run and args.cleanup_old:
            cleanup_old_images_with_wrong_numbers(film_dir, image_type, file_number)
        
        # Check if image is already downloaded with correct dimensions
        if not args.no_skip_existing and is_image_already_downloaded(dest):
            dimensions = get_image_dimensions(dest)
            if dimensions:
                return f"{film_name}:{fname}", True, f"Skipped (dimensions {dimensions[0]}x{dimensions[1]} are correct)"
        
        if args.dry_run:
            return f"{film_name}:{fname}", True, "Would download (dry run)"
        
        # Create a new session for this thread
        session = requests.Session()
        if args.cookie:
            session.cookies.update(load_cookie(args.cookie))
        
        print(f"Downloading {fname} for {film_name}...")
        
        # Download to temporary file first
        temp_dest = dest.with_suffix('.tmp')
        download_file(session, upload_url, temp_dest)
        
        # Post-process: resize if needed and convert to JPG
        if process_downloaded_image(temp_dest, image_type):
            # Move to final destination
            temp_dest.replace(dest)
            
            # If this is a poster and no image was previously set, update the film's index.md
            if image_type == "poster":
                update_film_index_if_needed(dest_root, fname)
            
            return f"{film_name}:{fname}", True, "Downloaded and processed successfully"
        else:
            # Clean up temp file if processing failed
            if temp_dest.exists():
                temp_dest.unlink()
            return f"{film_name}:{fname}", False, "Failed to process image"
        
    except Exception as exc:
        return f"{film_name}:{image_type}", False, f"Failed: {exc}"


def update_film_index_if_needed(film_dir: Path, poster_filename: str) -> None:
    """
    Update the film's index.md file to set the image field if no image was previously set.
    Only updates if the image field is missing or empty.
    """
    index_file = film_dir / "index.md"
    if not index_file.exists():
        return
    
    try:
        content = index_file.read_text(encoding='utf-8')
        
        # Check if image field already exists and has a value
        if re.search(r'^image:\s*["\']?[^"\'\s]+["\']?\s*$', content, re.MULTILINE):
            return  # Image already set, don't update
        
        # Look for the frontmatter section (between --- markers)
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not frontmatter_match:
            return  # No frontmatter found
        
        frontmatter = frontmatter_match.group(1)
        
        # Add image field to frontmatter
        if frontmatter.strip():
            # Add image field after the last existing field
            updated_frontmatter = frontmatter.rstrip() + f"\nimage: {poster_filename}\n"
        else:
            # Empty frontmatter, just add the image field
            updated_frontmatter = f"image: {poster_filename}\n"
        
        # Reconstruct the file content
        updated_content = content.replace(frontmatter, updated_frontmatter)
        
        # Write back to file
        index_file.write_text(updated_content, encoding='utf-8')
        print(f"  Updated {index_file.name} to set image: {poster_filename}")
        
    except Exception as e:
        print(f"  Warning: Could not update {index_file.name}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download 48 HFP film images")
    parser.add_argument("--csv", default="data/teams.csv", help="CSV file with film data")
    parser.add_argument("--year", default=2025, type=int, help="Competition year")
    parser.add_argument("--base-dir", default=os.path.expanduser("cdn"), help="Root directory for image storage")
    parser.add_argument("--cookie", default=os.environ.get("COOKIE"), help="Raw authentication cookie string")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without downloading")
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help=(
            "Download all files even if they already exist. By default, files are skipped if they exist "
            "and have correct dimensions (1920x1920 or smaller)."
        ),
    )
    parser.add_argument(
        "--cleanup-old",
        action="store_true",
        help=(
            "Remove old images with wrong numbers. By default, old images are preserved. "
            "When enabled, images with different numbers for the same type are removed before downloading."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Delay in seconds between image downloads"
    )
    parser.add_argument(
        "--film-delay",
        type=float,
        default=0,
        help="Delay in seconds between films"
    )
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=1920,
        help="Maximum dimension for images (default: 1920px). Images larger than this are resized."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for downloading (default: 4)"
    )
    args = parser.parse_args()

    if not args.cookie:
        raise SystemExit("You must provide an authentication cookie via --cookie or COOKIE env var")

    base_dir = Path(args.base_dir)

    session = requests.Session()
    session.cookies.update(load_cookie(args.cookie))

    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # CSV is definitive - use these fields directly
            team_id = row.get("id")
            slug = row.get("slug")  # Use slug directly from CSV
            film_title = row.get("film", "unknown_film")
            
            if not team_id:
                print(f"Skipping {film_title}: no team ID provided")
                continue
                
            if not slug:
                print(f"Skipping {film_title}: no slug provided")
                continue
            
            # Construct URL directly from team ID - CSV is definitive
            film_url = film_base_url + str(team_id)
            
            # Use slug directly from CSV for directory name
            dest_root = base_dir / f"{args.year}-{slug}"
            
            print(f"Processing {film_title} (ID: {team_id}, Slug: {slug})")
            print(f"  URL: {film_url}")
            print(f"  Directory: {dest_root}")

            try:
                # Find upload URLs based on specific URL patterns
                upload_urls = find_upload_urls(session, film_url)
            except Exception as exc:
                print(f"Error fetching images for {film_title}: {exc}")
                continue
            if not upload_urls:
                print(f"No upload URLs found for {film_title}")
                continue

            print(f"  Found {len(upload_urls)} upload URLs")
            
            # Prepare arguments for parallel processing
            download_tasks = []
            for upload_url, image_type in upload_urls:
                download_tasks.append((film_title, upload_url, image_type, dest_root, args))
            
            if download_tasks:
                print(f"Processing {len(download_tasks)} images for {film_title} with {args.workers} workers...")
                
                # Use ThreadPoolExecutor for parallel downloads
                with ThreadPoolExecutor(max_workers=args.workers) as executor:
                    # Submit all tasks
                    future_to_task = {executor.submit(download_and_process_image, task): task for task in download_tasks}
                    
                    # Process completed tasks
                    for future in as_completed(future_to_task):
                        task = future_to_task[future]
                        try:
                            image_name, success, message = future.result()
                            if success:
                                print(f"  ✅ {image_name}: {message}")
                            else:
                                print(f"  ❌ {image_name}: {message}")
                        except Exception as exc:
                            print(f"  ❌ {task[0]}: Exception occurred: {exc}")
                
                # Add delay between films to avoid overwhelming the server
                time.sleep(args.film_delay)


if __name__ == "__main__":
    main()