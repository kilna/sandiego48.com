#!/usr/bin/env python3
"""Create 2026 film pages from sd48hfp-2026 films.csv, premiere files, and downloads."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

SITE = Path("/Users/kilna/Code/48hfp/sandiego48.com")
PROJECT = Path("/Users/kilna/NAS/project/sd48hfp-2026")
CSV_PATH = PROJECT / "films.csv"
PREMIERE_DIR = PROJECT / "films" / "premiere"
DOWNLOAD_DIR = PROJECT / "download"
FILMS_DIR = SITE / "content" / "films"

PLACEHOLDER_TITLES = {"", "untitled", "n/a", "none", "no film title"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
EVENT_BY_GROUP = {
  "A": "2026-09-21-group-a-premiere",
  "B": "2026-09-21-group-b-premiere",
  "C": "2026-09-22-group-c-premiere",
  "D": "2026-09-22-group-d-premiere",
}
TEAMS_CSV = PROJECT / "teams.csv"


def q(value: str) -> str:
  return json.dumps((value or "").strip(), ensure_ascii=False)


def slugify(text: str) -> str:
  text = text.strip().lower()
  text = re.sub(r"['’]", "", text)
  text = re.sub(r"[^a-z0-9]+", "-", text)
  return text.strip("-")


def pretty_title(title: str) -> str:
  title = (title or "").strip()
  letters = [c for c in title if c.isalpha()]
  if not letters:
    return title
  all_upper = all(c.isupper() for c in letters)
  all_lower = all(c.islower() for c in letters)
  if not (all_upper or all_lower):
    return title
  small = {"a", "an", "and", "or", "the", "of", "to", "for", "in", "on"}
  words = re.split(r"(\s+)", title.lower())
  out = []
  word_i = 0
  for part in words:
    if not part.strip():
      out.append(part)
      continue
    if word_i == 0 or part not in small:
      out.append(part[:1].upper() + part[1:])
    else:
      out.append(part)
    word_i += 1
  return "".join(out)


def genre_pair(row: dict) -> tuple[str, str]:
  g1 = (row.get("film_genre_1") or "").strip()
  g2 = (row.get("film_genre_2") or "").strip()
  return g1, g2


def genre_text(row: dict) -> str:
  g1, g2 = genre_pair(row)
  if g1 and g2:
    return f"{g1} / {g2}"
  return g1 or g2


def find_poster(slug: str, team_slug: str) -> Path | None:
  candidates = []
  for path in PREMIERE_DIR.iterdir():
    if path.suffix.lower() in IMAGE_EXTS and path.stem == slug:
      candidates.append(path)
  posters = sorted(DOWNLOAD_DIR.glob(f"{team_slug}/{team_slug}-poster-*"))
  posters += sorted(DOWNLOAD_DIR.glob(f"{team_slug}/*poster*"))
  for path in posters:
    if path.suffix.lower() in IMAGE_EXTS and path.is_file():
      candidates.append(path)
  return candidates[0] if candidates else None


def convert_poster(src: Path, dest: Path) -> bool:
  dest.parent.mkdir(parents=True, exist_ok=True)
  cmd = [
    "sips", "-s", "format", "jpeg", "-Z", "1920",
    str(src), "--out", str(dest),
  ]
  result = subprocess.run(cmd, capture_output=True, text=True)
  if result.returncode != 0 or not dest.exists():
    print(f"  poster convert failed for {src}: {result.stderr.strip()}")
    return False
  return True


def write_film_page(row: dict) -> dict | None:
  status = (row.get("film_status") or "").strip().lower()
  dropoff = (row.get("film_dropoff_status") or "").strip().lower()
  if status in {"disqualified", "rejected"} or dropoff in {"disqualified", "rejected"}:
    print(f"  skip {row.get('slug')}: {status or dropoff}")
    return None
  raw_title = (row.get("film_title") or "").strip()
  title = raw_title if row.get("_preserve_title") else pretty_title(raw_title)
  if title.lower() in PLACEHOLDER_TITLES:
    return None
  group = (row.get("screening_group") or row.get("team_draw_group") or "").strip().upper()
  event = EVENT_BY_GROUP.get(group)
  if not event:
    print(f"  skip {row.get('slug')}: unknown group {group!r}")
    return None
  team = (row.get("team_name") or "").strip()
  csv_slug = (row.get("slug") or "").strip()
  dir_name = f"2026-{csv_slug}"
  film_dir = FILMS_DIR / dir_name
  film_dir.mkdir(parents=True, exist_ok=True)

  image_line = ""
  poster_src = find_poster(csv_slug, row.get("team_slug") or "")
  if poster_src:
    dest = film_dir / "poster.jpg"
    if dest.exists() and dest.stat().st_mtime >= poster_src.stat().st_mtime:
      image_line = 'image: poster.jpg\n'
    elif convert_poster(poster_src, dest):
      image_line = 'image: poster.jpg\n'

  logline = (row.get("film_logline") or "").strip()
  synopsis = (row.get("film_synopsis") or "").strip()
  genre = genre_text(row)
  body = synopsis or logline or f"{title} by {team}."

  page = f"""---
title: {q(title)}
{image_line}date: 2026-08-30T19:00:00-07:00
draft: false
params:
  year: 2026
  team: {q(team)}
  logline: {q(logline)}
  synopsis: {q(synopsis)}
  order: 999
  genre: {q(genre)}
screening_groups:
  - "group-{group.lower()}"
screening_events:
  - "{event}"
---
{body}
"""
  (film_dir / "index.md").write_text(page, encoding="utf-8")
  return {
    "dir": dir_name,
    "title": title,
    "team": team,
    "group": group,
    "event": event,
    "genre": genre,
    "genre_1": genre_pair(row)[0],
    "genre_2": genre_pair(row)[1],
    "logline": logline,
    "has_poster": bool(image_line),
  }


def sort_title(title: str) -> str:
  t = title.strip()
  if t.lower().startswith("the "):
    t = t[4:]
  return re.sub(r'["\']', "", t).lower()


def patch_event_page(group: str, films: list[dict]) -> None:
  event = EVENT_BY_GROUP[group]
  path = SITE / "content" / "events" / event / "index.md"
  text = path.read_text(encoding="utf-8")
  films = sorted(films, key=lambda f: sort_title(f["title"]))
  lines = [f"## Screening Group {group}", ""]
  for film in films:
    item = f"- **{film['title']}** by {film['team']}"
    g1, g2 = film.get("genre_1") or "", film.get("genre_2") or ""
    if g1 and g2:
      item += f" — {g1} and/or {g2}"
    elif film["genre"]:
      item += f" — {film['genre']}"
    lines.append(item)
  block = "\n".join(lines) + "\n"
  text = re.sub(
    r"## Screening Group [A-E]\n\n(?:- .+\n)+",
    block,
    text,
    count=1,
  )
  text = text.replace(
    " Drawn genres are listed below; film titles will be added after drop-off.",
    "",
  )
  text = text.replace(
    " Film titles, teams, and drawn genres are listed below.",
    "",
  )
  text = text.replace(
    "Drawn genres are listed with each team; film titles will be added after drop-off.",
    "Each film screens once, with live Audience Choice voting at the end of the night.",
  )
  text = text.replace(
    "    - Film titles and TixTree ticket details will be added after drop-off.\n",
    "    - Tickets will be sold in advance. There will be no on-site ticket sales.\n",
  )
  # Avoid duplicating the tickets note if it is now consecutive.
  text = re.sub(
    r"(    - Tickets will be sold in advance\. There will be no on-site ticket sales\.\n)\1",
    r"\1",
    text,
  )
  path.write_text(text, encoding="utf-8")


def main() -> int:
  team_info = {}
  if TEAMS_CSV.exists():
    with TEAMS_CSV.open(newline="", encoding="utf-8") as f:
      for row in csv.DictReader(f):
        slug = (row.get("team_slug") or "").strip()
        if not slug:
          continue
        team_info[slug] = {
          "group": (row.get("group") or "").strip().upper(),
          "title": (row.get("film") or "").strip(),
        }

  with CSV_PATH.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

  created = []
  skipped = []
  for row in rows:
    team_slug = (row.get("team_slug") or "").strip()
    info = team_info.get(team_slug) or {}
    if info.get("group"):
      row["screening_group"] = info["group"]
    if info.get("title"):
      row["film_title"] = info["title"]
      row["_preserve_title"] = True
    result = write_film_page(row)
    if result:
      created.append(result)
      poster = "poster" if result["has_poster"] else "no-poster"
      print(f"wrote {result['dir']} ({poster})")
    else:
      skipped.append(row.get("team_name") or row.get("slug"))

  by_group: dict[str, list[dict]] = {g: [] for g in EVENT_BY_GROUP}
  for film in created:
    by_group[film["group"]].append(film)
  for group in EVENT_BY_GROUP:
    patch_event_page(group, by_group[group])
    print(f"updated group {group}: {len(by_group[group])} films")

  print(f"\ncreated {len(created)} film pages; skipped {len(skipped)}")
  if skipped:
    print("skipped:", ", ".join(str(s) for s in skipped))
  missing = [f["dir"] for f in created if not f["has_poster"]]
  print(f"missing posters: {len(missing)}")
  for name in missing:
    print(" ", name)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
