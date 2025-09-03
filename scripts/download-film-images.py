#!/usr/bin/env python3
"""
Download still images (posters, film stills and behind‑the‑scenes photos)
for each film listed in a CSV from the 48 Hour Film Project site.

The script requires the same CSV format as used by the film downloader: each
row must include `id` (team ID), `slug` (directory name), and `film` (film title).
It also needs an authentication cookie that you capture via your browser's developer tools after logging in to
48hourfilm.com. Supply that cookie using the `--cookie` option or the
48HFP_COOKIE environment variable.

Images are saved into the structure:

    ~/Code/kilna/sandiego48.com/content/films/{year}-{slug}/

Each file is named with a prefix derived from its type (poster, still,
behind) followed by a sequence number and the original file extension.

Media to download is determined solely based on the presence of direct upload URLs
in these specific formats:

Still: https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/{TeamName}/Film%20Stills/{filename}

Poster: https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/{TeamName}/Poster/{filename}

BTS: https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/{TeamName}/Behind%20the%20Scenes%20Pictures/{filename}

The script parses the number from the original filename (e.g., "file 1", "file 2") and uses it
in the local filename to preserve the original numbering.

Images larger than 1920x1920 are automatically resized to fit within those dimensions
while preserving aspect ratio. Smaller images remain at their original size. All images
are compressed to meet GitHub Pages requirements (<25MB by default). Downloads are
processed in parallel for faster processing. This ensures consistent maximum dimensions
and requires ImageMagick to be installed (brew install imagemagick).

For background about the 2025 San Diego competition, the official
website explains that the event occurred August 15‑17th【875466236829739†L110-L120】
and lists entries like "Extra Toppings" by Breakfast for Dinner!【652804158881346†L152-L166】.
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
    else:
        return "unknown"


def extract_number_from_filename(url: str) -> int:
    """Extract the number from a filename like 'Film Stills - file 1.png' or 'Poster - file 2.png'."""
    try:
        # Get the filename from the URL
        filename = os.path.basename(urlparse(url).path)
        
        # Look for patterns like "file 1", "file 2", etc.
        match = re.search(r'file\s+(\d+)', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Alternative pattern: look for numbers before the extension
        match = re.search(r'(\d+)\.(?:png|jpg|jpeg|gif|webp)$', filename, re.IGNORECASE)
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
        
        ext = os.path.splitext(urlparse(upload_url).path)[1].lower()
        # Normalize JPEG extensions to JPG
        if ext in ['.jpeg', '.jpg']:
            ext = '.jpg'
        elif not ext:
            ext = '.jpg'  # Default to JPG if no extension
        
        fname = f"{image_type}-{file_number}{ext}"
        dest = dest_root / fname
        
        # Check if existing image has correct dimensions (1920x1920 or smaller)
        if not args.no_skip_existing and dest.exists():
            try:
                result = subprocess.run(['identify', '-format', '%wx%h', str(dest)], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    dimensions = result.stdout.strip()
                    width, height = map(int, dimensions.split('x'))
                    if width <= 1920 and height <= 1920:
                        return f"{film_name}:{fname}", True, f"Skipped (dimensions {dimensions} are correct)"
            except Exception:
                # If we can't read the image, assume it needs to be downloaded
                pass
        
        if args.dry_run:
            return f"{film_name}:{fname}", True, "Would download (dry run)"
        
        # Create a new session for this thread
        session = requests.Session()
        if args.cookie:
            session.cookies.update(load_cookie(args.cookie))
        
        print(f"Downloading {fname} for {film_name}...")
        download_file(session, upload_url, dest)
        
        # Check if image needs resizing for GitHub Pages compatibility
        if dest.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            resize_large_image_if_needed(dest, max_size_mb=args.max_image_size)
        
        return f"{film_name}:{fname}", True, "Downloaded and processed successfully"
        
    except Exception as exc:
        return f"{film_name}:{image_type}", False, f"Failed: {exc}"


def resize_large_image_if_needed(image_path: Path, max_size_mb: int = 25) -> bool:
    """
    Resize image only if it's larger than 1920x1920 dimensions or exceeds max_size_mb.
    Smaller images are left unchanged. Returns True if image was resized, False if no resize was needed.
    """
    try:
        # Check if ImageMagick is available
        try:
            subprocess.run(['convert', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"  Warning: ImageMagick not available, cannot resize {image_path.name}")
            print(f"  Please install ImageMagick: brew install imagemagick")
            return False
        
        # Get current image dimensions
        result = subprocess.run(['identify', '-format', '%wx%h', str(image_path)], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Warning: Could not get image dimensions for {image_path.name}")
            return False
        
        current_dimensions = result.stdout.strip()
        width, height = map(int, current_dimensions.split('x'))
        
        # Check if image needs resizing (only if dimensions are too large OR file size exceeds limit)
        file_size_mb = image_path.stat().st_size / (1024 * 1024)
        needs_resize = (width > 1920 or height > 1920 or file_size_mb > max_size_mb)
        
        if not needs_resize:
            return False
        
        print(f"  Image {image_path.name} is {width}x{height} ({file_size_mb:.1f}MB), resizing to 1920x1920 or smaller...")
        
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
        
        # Get new dimensions and file size
        result = subprocess.run(['identify', '-format', '%wx%h', str(image_path)], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            new_dimensions = result.stdout.strip()
            print(f"  Resized to {new_dimensions}")
        
        new_size_mb = image_path.stat().st_size / (1024 * 1024)
        print(f"  File size: {new_size_mb:.1f}MB")
        
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Download 48 HFP film images")
    parser.add_argument("--csv", default="data/teams.csv", help="CSV file with film data")
    parser.add_argument("--year", default=2025, type=int, help="Competition year")
    parser.add_argument("--base-dir", default=os.path.expanduser("content/films"), help="Root directory for image storage")
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
        "--max-image-size",
        type=int,
        default=25,
        help="Maximum image size in MB (default: 25MB for GitHub Pages). Images larger than 1920x1920 are resized to fit within those dimensions."
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
