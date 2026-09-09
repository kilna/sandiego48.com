#!/usr/bin/env python3
"""Import 2026 NAS download media into sandiego48.com CDN + film pages.

Source (sd48hfp-2026):

  download/<team>/<team>-{poster,still,bts,group-picture}-N.ext
  posters/<team>.ext                  # operator poster v0; HQ poster-1+ overrides
  thumb/<team>/<team>-thumb-N.jpg

Destination:

  content/films/2026-<team>-<film>/poster.jpg
  cdn/films/2026-<team>-<film>/{poster,still,bts,group}-NNN.jpg
  cdn/films/2026-<team>-<film>/thumb-NNN.jpg

Operator posters in posters/<team>.ext are treated as version 0. The film
page image uses the highest-numbered poster, so a dashboard upload
(<team>-poster-1+) replaces v0. v0 is omitted from the poster gallery once
an HQ poster exists.

Filmmaker stills/BTS/group/poster are compacted to sequential 001..N.
Generated thumbs keep their source numbers so culled gaps survive:

  thumb/axiomatic-twist/axiomatic-twist-thumb-7.jpg -> thumb-007.jpg

Frontmatter:

  params.galleries.still.count
  params.galleries.thumb.numbers   # [1, 7, 12] after culling

Do not publish (`make cdn` / git push) until generated thumbs have been culled.

Usage:

  python3 scripts/import-2026-media.py
  python3 scripts/import-2026-media.py --dry-run
  python3 scripts/import-2026-media.py --only-team axiomatic-twist
  python3 scripts/import-2026-media.py --skip-thumbs

Author: Kilna, Anthony <kilna@kilna.com>
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

SITE = Path("/Users/kilna/Code/48hfp/sandiego48.com")
NAS = Path("/Users/kilna/NAS/project/sd48hfp-2026")
DOWNLOAD = NAS / "download"
POSTERS = NAS / "posters"
THUMB = NAS / "thumb"
CONTENT = SITE / "content" / "films"
CDN = SITE / "cdn" / "films"
TEAMS_CSV = NAS / "teams.csv"

SKIP_TEAMS = {"dampt"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
KIND_RE = re.compile(
  r"-(poster|still|bts|group-picture)-(\d+)(?:-\d+)?(\.[^.]+)$",
  re.I,
)
THUMB_RE = re.compile(r"-thumb-(\d+)\.jpg$", re.I)


def convert(src: Path, dest: Path, dry_run: bool) -> bool:
  dest.parent.mkdir(parents=True, exist_ok=True)
  if dry_run:
    return True
  tmp = dest.with_suffix(dest.suffix + ".tmp.jpg")
  cmd = [
    "sips", "-s", "format", "jpeg", "-Z", "1920",
    str(src), "--out", str(tmp),
  ]
  result = subprocess.run(cmd, capture_output=True, text=True)
  if result.returncode != 0 or not tmp.exists():
    print(f"  convert failed {src.name}: {result.stderr.strip()}")
    tmp.unlink(missing_ok=True)
    return False
  tmp.replace(dest)
  return True


def needs_update(src: Path, dest: Path) -> bool:
  if not dest.exists():
    return True
  return src.stat().st_mtime > dest.stat().st_mtime + 1


def team_slugs() -> list[str]:
  slugs: set[str] = set()
  for root in (DOWNLOAD, THUMB):
    if not root.is_dir():
      continue
    for path in root.iterdir():
      if path.is_dir() and path.name not in {"thumb", "thumbs", "poster-thumb"}:
        slugs.add(path.name)
  if POSTERS.is_dir():
    for path in POSTERS.iterdir():
      if path.is_file() and not path.name.startswith("._"):
        if path.suffix.lower() in IMAGE_EXTS:
          slugs.add(path.stem)
  if TEAMS_CSV.exists():
    with TEAMS_CSV.open(encoding="utf-8") as handle:
      next(handle, None)
      for line in handle:
        slug = line.split(",", 1)[0].strip()
        if slug and slug != "team_slug":
          slugs.add(slug)
  return sorted(slugs, key=len, reverse=True)


def film_dir_for_team(team: str, film_dirs: list[Path]) -> Path | None:
  prefix = f"2026-{team}"
  matches = [
    path for path in film_dirs
    if path.name == prefix or path.name.startswith(prefix + "-")
  ]
  if not matches:
    return None
  matches.sort(key=lambda path: len(path.name))
  return matches[0]


def operator_poster_v0(team: str) -> Path | None:
  """Return posters/<team>.ext, the operator fallback (version 0)."""
  if not POSTERS.is_dir():
    return None
  matches: list[Path] = []
  for path in POSTERS.iterdir():
    if not path.is_file() or path.name.startswith("._"):
      continue
    if path.suffix.lower() not in IMAGE_EXTS:
      continue
    if path.stem.lower() == team.lower():
      matches.append(path)
  if not matches:
    return None
  matches.sort(key=lambda path: path.stat().st_mtime)
  return matches[-1]


def copy_poster_v0(team: str, src: Path, dry_run: bool) -> Path:
  """Place operator posters in download as <team>-poster-0 so HQ v1+ wins."""
  dest_dir = DOWNLOAD / team
  dest = dest_dir / f"{team}-poster-0{src.suffix.lower()}"
  if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime - 1:
    return dest
  dest_dir.mkdir(parents=True, exist_ok=True)
  if not dry_run:
    shutil.copy2(src, dest)
  return dest


def collect_kinds(src_dir: Path) -> dict[str, list[tuple[int, Path]]]:
  by_kind: dict[str, list[tuple[int, Path]]] = {}
  if not src_dir.is_dir():
    return by_kind
  for path in src_dir.iterdir():
    if not path.is_file() or path.name.startswith("._"):
      continue
    if path.suffix.lower() not in IMAGE_EXTS:
      continue
    match = KIND_RE.search(path.name)
    if not match:
      continue
    kind = match.group(1).lower()
    if kind == "group-picture":
      kind = "group"
    by_kind.setdefault(kind, []).append((int(match.group(2)), path))
  for kind in by_kind:
    by_kind[kind].sort()
  return by_kind


def collect_thumbs(team: str) -> list[tuple[int, Path]]:
  thumb_dir = THUMB / team
  if not thumb_dir.is_dir():
    return []
  items: list[tuple[int, Path]] = []
  prefix = f"{team}-thumb-"
  for path in thumb_dir.iterdir():
    if not path.is_file() or path.name.startswith("._"):
      continue
    if not path.name.lower().startswith(prefix):
      continue
    match = THUMB_RE.search(path.name)
    if not match:
      continue
    items.append((int(match.group(1)), path))
  items.sort()
  return items


def set_image_line(index: Path, dry_run: bool) -> None:
  text = index.read_text(encoding="utf-8")
  if re.search(r"^image:", text, re.M):
    if "image: poster.jpg" not in text.split("---", 2)[1]:
      text = re.sub(
        r"^image:.*$", "image: poster.jpg", text, count=1, flags=re.M,
      )
      if not dry_run:
        index.write_text(text, encoding="utf-8")
    return
  text = re.sub(
    r"(^title: .+\n)", r"\1image: poster.jpg\n", text, count=1, flags=re.M,
  )
  if not dry_run:
    index.write_text(text, encoding="utf-8")


def set_galleries(
  index: Path,
  counts: dict[str, int],
  thumb_numbers: list[int],
  dry_run: bool,
) -> None:
  text = index.read_text(encoding="utf-8")
  parts = text.split("---", 2)
  if len(parts) < 3:
    return
  fm = parts[1]
  lines: list[str] = []
  for kind in ("poster", "still", "bts", "group"):
    n = counts.get(kind, 0)
    if n:
      lines.append(f"    {kind}:\n      count: {n}")
  if thumb_numbers:
    nums = ", ".join(str(n) for n in thumb_numbers)
    lines.append(f"    thumb:\n      numbers: [{nums}]")
  if not lines:
    return
  block = "  galleries:\n" + "\n".join(lines) + "\n"
  if re.search(r"^  galleries:", fm, re.M):
    fm = re.sub(
      r"^  galleries:\n(?:    .+\n(?:      .+\n)*)+",
      block,
      fm,
      count=1,
      flags=re.M,
    )
  elif re.search(r"^  genre:", fm, re.M):
    fm = re.sub(r"(^  genre: .+\n)", r"\1" + block, fm, count=1, flags=re.M)
  else:
    fm = fm.rstrip() + "\n" + block
  if not dry_run:
    index.write_text("---" + fm + "---" + parts[2], encoding="utf-8")


def sync_thumbs(
  team: str,
  items: list[tuple[int, Path]],
  cdn_dir: Path,
  dry_run: bool,
) -> tuple[list[int], list[str], list[str]]:
  wanted = {n: src for n, src in items}
  written: list[str] = []
  removed: list[str] = []
  cdn_dir.mkdir(parents=True, exist_ok=True)
  existing = {
    int(match.group(1)): path
    for path in cdn_dir.glob("thumb-*.jpg")
    if (match := re.match(r"thumb-(\d+)\.jpg$", path.name))
  }
  for num, src in items:
    dest = cdn_dir / f"thumb-{num:03d}.jpg"
    if needs_update(src, dest):
      if convert(src, dest, dry_run):
        written.append(
          f"{cdn_dir.name}/{dest.name} <- thumb/{team}/{src.name}"
        )
  for num, path in existing.items():
    if num not in wanted:
      removed.append(f"{cdn_dir.name}/{path.name}")
      if not dry_run:
        path.unlink(missing_ok=True)
        for leftover in (cdn_dir / "thumbs").glob(f"thumb-{num:03d}-*.webp"):
          leftover.unlink(missing_ok=True)
  return sorted(wanted), written, removed


def import_team(
  team: str,
  film_dir: Path,
  skip_thumbs: bool,
  dry_run: bool,
) -> dict[str, list[str]]:
  src_dir = DOWNLOAD / team
  cdn_dir = CDN / film_dir.name
  index = film_dir / "index.md"
  stats: dict[str, list[str]] = {
    "cdn": [], "poster": [], "thumbs": [], "removed": [],
  }
  by_kind = collect_kinds(src_dir)
  v0 = operator_poster_v0(team)
  posters = list(by_kind.get("poster") or [])
  if v0:
    dest_v0 = copy_poster_v0(team, v0, dry_run)
    posters = [item for item in posters if item[0] != 0]
    posters.append((0, dest_v0 if dest_v0.exists() else v0))
  posters.sort()
  if posters:
    by_kind["poster"] = posters
  elif "poster" in by_kind:
    del by_kind["poster"]
  counts: dict[str, int] = {}

  if posters:
    _n, poster_src = posters[-1]
    dest = film_dir / "poster.jpg"
    if needs_update(poster_src, dest):
      if convert(poster_src, dest, dry_run):
        set_image_line(index, dry_run)
        stats["poster"].append(f"{film_dir.name} <- {poster_src.name}")
    else:
      set_image_line(index, dry_run)

  gallery_kinds = dict(by_kind)
  hq_posters = [item for item in posters if item[0] >= 1]
  if hq_posters:
    gallery_kinds["poster"] = hq_posters
  for kind, items in gallery_kinds.items():
    counts[kind] = len(items)
    cdn_dir.mkdir(parents=True, exist_ok=True)
    for i, (_n, src) in enumerate(items, start=1):
      dest = cdn_dir / f"{kind}-{i:03d}.jpg"
      if needs_update(src, dest):
        if convert(src, dest, dry_run):
          stats["cdn"].append(f"{film_dir.name}/{dest.name} <- {src.name}")

  thumb_numbers: list[int] = []
  if skip_thumbs:
    thumb_numbers = sorted(
      int(match.group(1))
      for path in cdn_dir.glob("thumb-*.jpg")
      if (match := re.match(r"thumb-(\d+)\.jpg$", path.name))
    )
  else:
    thumb_numbers, written, removed = sync_thumbs(
      team, collect_thumbs(team), cdn_dir, dry_run,
    )
    stats["thumbs"].extend(written)
    stats["removed"].extend(removed)

  set_galleries(index, counts, thumb_numbers, dry_run)
  return stats


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Import 2026 NAS media into sandiego48.com",
  )
  parser.add_argument("--dry-run", action="store_true")
  parser.add_argument("--only-team", action="append", default=[])
  parser.add_argument(
    "--skip-thumbs",
    action="store_true",
    help="Do not copy or delete generated thumbs",
  )
  args = parser.parse_args()
  only = {slug.strip() for slug in args.only_team if slug.strip()}

  film_dirs = sorted(
    path for path in CONTENT.iterdir()
    if path.is_dir() and path.name.startswith("2026-")
  )
  stats = {"cdn": [], "poster": [], "thumbs": [], "removed": [], "skip": []}
  imported = 0
  for team in team_slugs():
    if team in SKIP_TEAMS:
      continue
    if only and team not in only:
      continue
    film_dir = film_dir_for_team(team, film_dirs)
    if film_dir is None:
      stats["skip"].append(team)
      continue
    result = import_team(team, film_dir, args.skip_thumbs, args.dry_run)
    imported += 1
    for key in ("cdn", "poster", "thumbs", "removed"):
      stats[key].extend(result[key])

  prefix = "dry-run " if args.dry_run else ""
  print(f"{prefix}films processed: {imported}")
  print(f"posters updated: {len(stats['poster'])}")
  for line in stats["poster"]:
    print(f"  {line}")
  print(f"cdn stills/bts/group/poster written: {len(stats['cdn'])}")
  for line in stats["cdn"]:
    print(f"  {line}")
  print(f"generated thumbs written: {len(stats['thumbs'])}")
  for line in stats["thumbs"][:40]:
    print(f"  {line}")
  if len(stats["thumbs"]) > 40:
    print(f"  ... {len(stats['thumbs']) - 40} more")
  print(f"generated thumbs removed: {len(stats['removed'])}")
  for line in stats["removed"][:20]:
    print(f"  {line}")
  if stats["skip"]:
    print("no film page for:", ", ".join(stats["skip"]))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
