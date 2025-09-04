#!/usr/bin/env python3
"""
Debug script to examine the actual URLs from 48hourfilm.com
and understand why the numbering is incorrect.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the common module
sys.path.append(str(Path(__file__).parent.parent))

from scripts.download_film_images import load_cookie, classify_image_from_url, extract_number_from_filename

def debug_film_urls(film_url: str, cookie_str: str):
    """Debug the URLs found on a film page."""
    session = requests.Session()
    session.cookies.update(load_cookie(cookie_str))
    
    print(f"Fetching {film_url}...")
    resp = session.get(film_url)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    print(f"\nFound {len(soup.find_all('a', href=True))} total links")
    
    # Look for all links and check if they match our upload URL patterns
    upload_urls = []
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if not href:
            continue
            
        # Check if this is a direct upload URL
        if href.startswith("https://www.48hourfilm.com/uploads/2025/48HFP/48%20Hour%20Film%20Project%20-%20San%20Diego/"):
            image_type = classify_image_from_url(href)
            if image_type != "unknown":
                upload_urls.append((href, image_type))
                
                # Debug the URL parsing
                filename = os.path.basename(urlparse(href).path)
                extracted_number = extract_number_from_filename(href)
                
                print(f"\nURL: {href}")
                print(f"  Filename: {filename}")
                print(f"  Image type: {image_type}")
                print(f"  Extracted number: {extracted_number}")
                
                # Show what patterns we're looking for
                print(f"  Looking for 'file X' pattern: {bool(re.search(r'file\s+(\d+)', filename, re.IGNORECASE))}")
                print(f"  Looking for number before extension: {bool(re.search(r'(\d+)\.(?:png|jpg|jpeg|gif|webp)$', filename, re.IGNORECASE))}")
                
                # Show the actual regex matches
                file_match = re.search(r'file\s+(\d+)', filename, re.IGNORECASE)
                if file_match:
                    print(f"  'file X' match: {file_match.group(1)}")
                
                ext_match = re.search(r'(\d+)\.(?:png|jpg|jpeg|gif|webp)$', filename, re.IGNORECASE)
                if ext_match:
                    print(f"  'number before extension' match: {ext_match.group(1)}")
    
    print(f"\nTotal upload URLs found: {len(upload_urls)}")
    
    if not upload_urls:
        print("\nNo upload URLs found. Let's look at all URLs that might be relevant:")
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if "upload" in href.lower() or "image" in href.lower() or "file" in href.lower():
                print(f"  {href}")
    
    return upload_urls

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 debug-urls.py <film_url> <cookie_string>")
        print("Example: python3 debug-urls.py 'https://www.48hourfilm.com/film/12345' 'your_cookie_string'")
        return 1
    
    film_url = sys.argv[1]
    cookie_str = sys.argv[2]
    
    try:
        debug_film_urls(film_url, cookie_str)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
