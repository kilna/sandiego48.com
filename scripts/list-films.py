#!/usr/bin/env python3
"""
Utility to enumerate all film upload pages for a given year and city from
the 48 Hour Film Project producer dashboard.

Given the URL of the year overview page (e.g. the Team Drop off Progress
overview) and an authentication cookie, this script locates every link to
the per‑team "more info" page, then visits each page to extract the
team name, film title, film ID and film URL.  The results are written to
a CSV suitable for use with the download scripts.

Example usage:

    python3 48hfp_list_films.py \
        --cookie "_session=..." \
        --output films.csv

The overview URL should reflect the year, city and competition type you
selected in the dashboard.  You must be logged in and copy a valid
session cookie before running the script.
"""

import argparse
import csv
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def load_cookie(cookie_str: str) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    for item in cookie_str.split(";"):
        if not item.strip() or "=" not in item:
            continue
        name, value = item.split("=", 1)
        jar.set(name.strip(), value.strip())
    return jar


def find_team_links(html: str) -> list[str]:
    """Return a list of absolute URLs to team more‑info pages."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a['href']
        if 'team-more-info' in href:
            links.append(href)
    return links


def parse_team_page(html: str) -> tuple[str, str, str]:
    """
    Extract (film_id, team_name, film_title) from a team more‑info page.

    The page contains lines like "Team ID: #94172" and "Film ID: #70874",
    and a heading with the film and team names.  This function uses
    simple regexes to pull out the data.  If parsing fails, empty
    strings are returned.
    """
    film_id = team_id = team_name = film_title = ""
    # Extract film and team IDs
    team_match = re.search(r"Team ID:.*?;(\d+)", html)
    id_match = re.search(r"Film ID:.*?;(\d+)", html)
    if team_match:
        team_id = team_match.group(1)
    if id_match:
        film_id = id_match.group(1)
    # Extract heading: Extra Toppings by Breakfast for Dinner!
    soup = BeautifulSoup(html, "html.parser")
    h2 = soup.find('h2')
    if h2:
        text = h2.get_text(" ", strip=True)
        # Format: "Extra Toppings by Breakfast for Dinner!"
        if ' by ' in text:
            film_title, team_name = [p.strip() for p in text.split(' by ', 1)]
    return film_id, team_id, team_name, film_title


def main() -> None:
    parser = argparse.ArgumentParser(description="List all films for a given year/city from the 48HFP dashboard")
    parser.add_argument("--overview-url", default="https://www.48hourfilm.com/dash/cp/production/team-progress-overview", help="URL of the team progress overview page for the selected year")
    parser.add_argument("--cookie", default=os.environ.get("COOKIE"), help="Raw authentication cookie string")
    parser.add_argument("--output", required=True, help="Path to output CSV file")
    args = parser.parse_args()

    if not args.cookie:
        raise SystemExit("You must provide an authentication cookie via --cookie or COOKIE env var")

    session = requests.Session()
    session.cookies.update(load_cookie(args.cookie))

    # Fetch overview page
    resp = session.get(args.overview_url)
    resp.raise_for_status()
    team_links = find_team_links(resp.text)
    if not team_links:
        print("No team links found on overview page; check that you're using the correct URL and are logged in")
        return

    # Deduplicate and normalise links to absolute
    base = resp.url
    unique_links = []
    seen = set()
    for href in team_links:
        abs_url = urljoin(base, href)
        if abs_url not in seen:
            seen.add(abs_url)
            unique_links.append(abs_url)

    print(f"Found {len(unique_links)} team pages")

    with open(args.output, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['film_id', 'team_id', 'team_name', 'film_title', 'film_url'])
        writer.writeheader()
        for url in unique_links:
            try:
                r = session.get(url)
                r.raise_for_status()
                film_id, team_id, team_name, film_title = parse_team_page(r.text)
                writer.writerow({
                    'film_id': film_id,
                    'team_id': team_id,
                    'team_name': team_name,
                    'film_title': film_title,
                    'film_url': url,
                })
                print(f"Recorded film {film_title} (ID {film_id})")
            except Exception as exc:
                print(f"Failed to process {url}: {exc}")


if __name__ == '__main__':
    main()
