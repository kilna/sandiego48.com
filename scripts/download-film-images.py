#!/usr/bin/env python3
"""
Download still images (posters, film stills and behind‑the‑scenes photos)
for each film listed in a CSV from the 48 Hour Film Project site.

The script requires the same CSV format as used by the film downloader: each
row must include `film_id`, `team_name`, `film_title` and `film_url` (the
URL of the drop‑off/gallery page).  It also needs an authentication cookie
that you capture via your browser's developer tools after logging in to
48hourfilm.com.  Supply that cookie using the `--cookie` option or the
48HFP_COOKIE environment variable.

Images are saved into the structure:

    ~/Code/kilna/sandiego48.com/content/films/{year}-{team_slug}-{film_slug}/

Each file is named with a prefix derived from its type (poster, still,
behind) followed by a sequence number and the original file extension.

The heuristic used to classify images simply looks for keywords in the
image's alt text or filename.  You may need to adjust the `classify_image`
function if your site's markup differs.

Images larger than 1920x1920 are automatically resized to fit within those dimensions
while preserving aspect ratio. Smaller images remain at their original size. All images
are compressed to meet GitHub Pages requirements (<25MB by default). Downloads are
processed in parallel for faster processing. This ensures consistent maximum dimensions
and requires ImageMagick to be installed (brew install imagemagick).

For background about the 2025 San Diego competition, the official
website explains that the event occurred August 15‑17th【875466236829739†L110-L120】
and lists entries like "Extra Toppings" by Breakfast for Dinner!【652804158881346†L152-L166】.
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
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

film_base_url="https://www.48hourfilm.com/dash/cp/production/team-more-info/"

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


def classify_image(link_text: str) -> str:
    """Return a prefix describing the image type based on download button text."""
    text = link_text.lower()
    if "poster" in text:
        return "poster"
    elif "film stills" in text:
        return "still"
    elif "behind the scenes pictures" in text:
        return "bts"
    else:
        return "unknown"


def download_images(session: requests.Session, film_url: str) -> List[Tuple[str, str]]:
    """Return list of (image_url, link_text) pairs found in download buttons."""
    resp = session.get(film_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    images: List[Tuple[str, str]] = []
    
    # Look for table rows that contain our target image types
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
            
        # Check if the first cell contains our target descriptive text
        first_cell_text = cells[0].get_text(strip=True)
        if not any(pattern in first_cell_text.lower() for pattern in [
            "poster",
            "film stills", 
            "behind the scenes pictures"
        ]):
            continue
            
        # Look for a download link in the second cell
        download_link = cells[1].find("a")
        if not download_link or download_link.get_text(strip=True).lower() != "download":
            continue
            
        href = download_link.get("href")
        if not href:
            continue
            
        # Extract the download URL
        if href.startswith("http"):
            download_url = href
        else:
            # Handle relative URLs
            download_url = requests.compat.urljoin(film_url, href)
        
        images.append((download_url, first_cell_text))
    
    return images


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
    film_name, download_url, link_text, dest_root, counters, args = args_tuple
    
    try:
        prefix = classify_image(link_text)
        if prefix == "unknown":
            return f"{film_name}:{prefix}", False, "Unknown image type"
        
        counters[prefix] = counters.get(prefix, 0) + 1
        ext = os.path.splitext(urlparse(download_url).path)[1].lower()
        # Normalize JPEG extensions to JPG
        if ext in ['.jpeg', '.jpg']:
            ext = '.jpg'
        elif not ext:
            ext = '.jpg'  # Default to JPG if no extension
        
        fname = f"{prefix}-{counters[prefix]}{ext}"
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
        download_file(session, download_url, dest)
        
        # Check if image needs resizing for GitHub Pages compatibility
        if dest.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            resize_large_image_if_needed(dest, max_size_mb=args.max_image_size)
        
        return f"{film_name}:{fname}", True, "Downloaded and processed successfully"
        
    except Exception as exc:
        return f"{film_name}:{prefix}", False, f"Failed: {exc}"


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
    parser = argparse.ArgumentParser(description="Download 48 HFP film images")
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
            team = row.get("team", "unknown_team")
            film = row.get("film", "unknown_film")
            dir = row.get("dir", "unknown_film")
            team_id = row.get("id", "unknown_id")
            film_url = film_base_url + team_id
            if not team_id:
                print(f"Skipping {film}: no film_url provided")
                continue
            dest_root = base_dir / f"{args.year}-{dir}"

            try:
                images = download_images(session, film_url)
            except Exception as exc:
                print(f"Error fetching images for {film}: {exc}")
                continue
            if not images:
                print(f"No images found for {film}")
                continue

            counters: Dict[str, int] = {}
            
            # Prepare arguments for parallel processing
            download_tasks = []
            for download_url, link_text in images:
                download_tasks.append((film, download_url, link_text, dest_root, counters, args))
            
            if download_tasks:
                print(f"Processing {len(download_tasks)} images for {film} with {args.workers} workers...")
                
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
