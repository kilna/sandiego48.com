#!/usr/bin/env python3
"""
Test script to examine the HTML structure of a film page
and understand how the download buttons are implemented.
"""

import requests
from bs4 import BeautifulSoup
import sys
from pathlib import Path

# Add the parent directory to the path so we can import the common module
sys.path.append(str(Path(__file__).parent.parent))

from scripts.download_film_images import load_cookie

def examine_html_structure(film_url: str, cookie_str: str):
    """Examine the HTML structure of a film page."""
    session = requests.Session()
    session.cookies.update(load_cookie(cookie_str))
    
    print(f"Fetching {film_url}...")
    resp = session.get(film_url)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    print(f"\nPage title: {soup.title.string if soup.title else 'No title'}")
    
    # Look for tables
    tables = soup.find_all("table")
    print(f"\nFound {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"\n--- Table {i+1} ---")
        rows = table.find_all("tr")
        print(f"  Rows: {len(rows)}")
        
        for j, row in enumerate(rows[:5]):  # Show first 5 rows
            cells = row.find_all(["td", "th"])
            print(f"    Row {j+1}: {len(cells)} cells")
            
            for k, cell in enumerate(cells):
                cell_text = cell.get_text(strip=True)
                if cell_text:
                    print(f"      Cell {k+1}: '{cell_text}'")
                
                # Look for links in this cell
                links = cell.find_all("a")
                if links:
                    for link in links:
                        href = link.get("href", "")
                        text = link.get_text(strip=True)
                        print(f"        Link: '{text}' -> {href}")
    
    # Look for any elements containing our target text
    print(f"\n--- Looking for target text patterns ---")
    
    # Behind the Scenes Pictures
    bts_elements = soup.find_all(text=re.compile(r'Behind the Scenes Pictures', re.IGNORECASE))
    print(f"  'Behind the Scenes Pictures' found in {len(bts_elements)} elements")
    
    # Film Stills
    still_elements = soup.find_all(text=re.compile(r'Film Stills', re.IGNORECASE))
    print(f"  'Film Stills' found in {len(still_elements)} elements")
    
    # Poster
    poster_elements = soup.find_all(text=re.compile(r'Poster', re.IGNORECASE))
    print(f"  'Poster' found in {len(poster_elements)} elements")
    
    # Download
    download_elements = soup.find_all(text=re.compile(r'Download', re.IGNORECASE))
    print(f"  'Download' found in {len(download_elements)} elements")
    
    # Show some examples
    for i, element in enumerate(bts_elements[:3]):
        print(f"    BTS example {i+1}: '{element.strip()}'")
        parent = element.parent
        if parent:
            print(f"      Parent tag: {parent.name}")
            print(f"      Parent text: '{parent.get_text(strip=True)}'")
    
    for i, element in enumerate(still_elements[:3]):
        print(f"    Still example {i+1}: '{element.strip()}'")
        parent = element.parent
        if parent:
            print(f"      Parent tag: {parent.name}")
            print(f"      Parent text: '{parent.get_text(strip=True)}'")
    
    for i, element in enumerate(poster_elements[:3]):
        print(f"    Poster example {i+1}: '{element.strip()}'")
        parent = element.parent
        if parent:
            print(f"      Parent tag: {parent.name}")
            print(f"      Parent text: '{parent.get_text(strip=True)}'")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 test-html-structure.py <film_url> <cookie_string>")
        print("Example: python3 test-html-structure.py 'https://www.48hourfilm.com/dash/cp/production/team-more-info/12345' 'your_cookie_string'")
        return 1
    
    film_url = sys.argv[1]
    cookie_str = sys.argv[2]
    
    try:
        examine_html_structure(film_url, cookie_str)
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import re
    exit(main())
