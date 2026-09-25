#!/usr/bin/env python3
"""Import 2026 NAS download media into sandiego48.com CDN + film pages.

Source (sd48hfp-2026):

  download/<team>/<team>-{poster,still,bts,group-picture}-N.ext
  download/<team>/<team>-trailer-vN.ext
  placeholder-posters/<team>.ext      # fallback poster v0; HQ poster-1+ overrides
  thumb/<team>/<team>-thumb-N.jpg

Destination:

  content/films/2026-<team>-<film>/poster.jpg
  cdn/films/2026-<team>-<film>/{poster,still,bts,group}-NNN.jpg
  cdn/films/2026-<team>-<film>/thumb-NNN.jpg
  cdn/films/2026-<team>-<film>/trailer.mp4
  cdn/films/2026-<team>-<film>/trailer-poster.jpg

Placeholder posters in placeholder-posters/<team>.ext are treated as
version 0. An HQ dashboard upload (<team>-poster-1+) always replaces a
placeholder on the film page and in the poster gallery, even if the HQ
file's timestamp is older than the already-imported v0. Same fitted
size is not enough — a placeholder with the same aspect ratio scales
to the same pixel size — so the pictures are compared. v0 is omitted
from the poster gallery once an HQ poster exists.

Filmmaker stills/BTS/group/poster are compacted to sequential 001..N.
Generated thumbs keep their source numbers so culled gaps survive:

  thumb/axiomatic-twist/axiomatic-twist-thumb-7.jpg -> thumb-007.jpg

The most recently updated HQ trailer is transcoded to a web H.264/AAC
MP4 (1080p max, faststart) plus a still frame for the player poster.

Frontmatter:

  params.trailer                   # trailer.mp4 when a web encode exists
  params.galleries.still.count
  params.galleries.thumb.numbers   # [1, 7, 12] after culling

Do not publish (`make cdn` / git push) until generated thumbs have been culled.

Usage:

  python3 scripts/import-2026-media.py
  python3 scripts/import-2026-media.py --dry-run
  python3 scripts/import-2026-media.py --only-team axiomatic-twist
  python3 scripts/import-2026-media.py --skip-thumbs
  python3 scripts/import-2026-media.py --skip-trailers

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
POSTERS = NAS / "placeholder-posters"
THUMB = NAS / "thumb"
CONTENT = SITE / "content" / "films"
CDN = SITE / "cdn" / "films"
TEAMS_CSV = NAS / "teams.csv"

SKIP_TEAMS = {"dampt"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}
KIND_RE = re.compile(
  r"-(poster|still|bts|group-picture)-(\d+)(?:-\d+)?(\.[^.]+)$",
  re.I,
)
THUMB_RE = re.compile(r"-thumb-(\d+)\.jpg$", re.I)
TRAILER_RE = re.compile(r"-trailer-v(\d+)(?:-(\d+))?(\.[^.]+)$", re.I)
MAX_TRAILER_SECONDS = 180
TRAILER_NAME = "trailer.mp4"
TRAILER_POSTER_NAME = "trailer-poster.jpg"


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


SAME_PICTURE_EDGE = 16
# Mean absolute difference of a 16x16 thumbnail. A fresh sips JPEG of the
# same picture stays under ~6; a different poster is tens of levels apart.
SAME_PICTURE_MAX_MAD = 12.0


def thumbnail_pixels(path: Path, edge: int = SAME_PICTURE_EDGE) -> bytes | None:
  result = subprocess.run(
    [
      "vips", "thumbnail", str(path), ".ppm",
      str(edge), "--height", str(edge), "--size", "force",
    ],
    capture_output=True,
  )
  if result.returncode != 0 or not result.stdout.startswith(b"P6"):
    return None
  parts = result.stdout.split(b"\n", 3)
  if len(parts) < 4 or not parts[3]:
    return None
  return parts[3]


def same_picture(src: Path, dest: Path) -> bool:
  """True when dest is already a conversion of src, not just the same aspect."""
  src_px = thumbnail_pixels(src)
  dest_px = thumbnail_pixels(dest)
  if not src_px or not dest_px or len(src_px) != len(dest_px):
    return False
  total = sum(abs(a - b) for a, b in zip(src_px, dest_px))
  return (total / len(src_px)) <= SAME_PICTURE_MAX_MAD


def needs_poster_convert(src: Path, dest: Path) -> bool:
  """HQ posters replace placeholders even when the HQ mtime is older.

  A newer source file always wins. An older HQ file still replaces dest
  when the published picture is different — a placeholder with the same
  aspect ratio scales to the same pixel size, so size alone cannot decide.
  Skip when dest is already this picture, even if the fitted size differs
  by a few pixels from sips -Z 1920.
  """
  if not dest.exists():
    return True
  if needs_update(src, dest):
    return True
  return not same_picture(src, dest)


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
  """Return placeholder-posters/<team>.ext, the fallback poster (version 0)."""
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
  """Place placeholder posters in download as <team>-poster-0 so HQ v1+ wins."""
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


def collect_trailer(team: str, src_dir: Path) -> Path | None:
  if not src_dir.is_dir():
    return None
  items: list[Path] = []
  for path in src_dir.iterdir():
    if not path.is_file() or path.name.startswith("._"):
      continue
    if path.suffix.lower() not in VIDEO_EXTS:
      continue
    if not path.name.lower().startswith(f"{team}-trailer-"):
      continue
    if not TRAILER_RE.search(path.name):
      continue
    items.append(path)
  if not items:
    return None
  items.sort(key=lambda path: (path.stat().st_mtime, path.name))
  return items[-1]


def probe_duration(src: Path) -> float | None:
  result = subprocess.run(
    [
      "ffprobe", "-v", "error", "-show_entries", "format=duration",
      "-of", "default=noprint_wrappers=1:nokey=1", str(src),
    ],
    capture_output=True,
    text=True,
  )
  if result.returncode != 0:
    return None
  try:
    return float(result.stdout.strip())
  except ValueError:
    return None


def encode_trailer(src: Path, dest: Path, dry_run: bool) -> bool:
  dest.parent.mkdir(parents=True, exist_ok=True)
  if dry_run:
    return True
  tmp = dest.with_suffix(dest.suffix + ".tmp.mp4")
  tmp.unlink(missing_ok=True)
  vf = (
    "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease,"
    "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p"
  )
  cmd = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-i", str(src),
    "-map", "0:v:0", "-map", "0:a:0?",
    "-vf", vf,
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
    "-profile:v", "high", "-level", "4.1",
    "-c:a", "aac", "-b:a", "160k", "-ac", "2",
    "-movflags", "+faststart",
    str(tmp),
  ]
  result = subprocess.run(cmd, capture_output=True, text=True)
  if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
    err = (result.stderr or result.stdout or "").strip()
    print(f"  encode failed {src.name}: {err}")
    tmp.unlink(missing_ok=True)
    return False
  tmp.replace(dest)
  return True


def extract_trailer_poster(src: Path, dest: Path, dry_run: bool) -> bool:
  dest.parent.mkdir(parents=True, exist_ok=True)
  if dry_run:
    return True
  tmp = dest.with_suffix(dest.suffix + ".tmp.jpg")
  tmp.unlink(missing_ok=True)
  cmd = [
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-ss", "1", "-i", str(src), "-frames:v", "1", "-q:v", "3",
    str(tmp),
  ]
  result = subprocess.run(cmd, capture_output=True, text=True)
  if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
    cmd[cmd.index("-ss") + 1] = "0"
    result = subprocess.run(cmd, capture_output=True, text=True)
  if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
    err = (result.stderr or result.stdout or "").strip()
    print(f"  trailer poster failed {src.name}: {err}")
    tmp.unlink(missing_ok=True)
    return False
  tmp.replace(dest)
  return True


def set_trailer(index: Path, filename: str | None, dry_run: bool) -> None:
  text = index.read_text(encoding="utf-8")
  parts = text.split("---", 2)
  if len(parts) < 3:
    return
  fm = parts[1]
  if filename:
    line = f"  trailer: {filename}\n"
    if re.search(r"^  trailer:", fm, re.M):
      fm = re.sub(r"^  trailer:.*\n", line, fm, count=1, flags=re.M)
    elif re.search(r"^  galleries:", fm, re.M):
      fm = re.sub(r"(^  galleries:)", line + r"\1", fm, count=1, flags=re.M)
    else:
      fm = fm.rstrip() + "\n" + line
  else:
    fm = re.sub(r"^  trailer:.*\n", "", fm, count=1, flags=re.M)
  if not dry_run:
    index.write_text("---" + fm + "---" + parts[2], encoding="utf-8")


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
  if fm == parts[1]:
    return
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
  skip_trailers: bool,
  dry_run: bool,
) -> dict[str, list[str]]:
  src_dir = DOWNLOAD / team
  cdn_dir = CDN / film_dir.name
  index = film_dir / "index.md"
  stats: dict[str, list[str]] = {
    "cdn": [], "poster": [], "thumbs": [], "trailers": [], "removed": [],
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
    stale = (
      needs_poster_convert(poster_src, dest)
      if _n >= 1 else needs_update(poster_src, dest)
    )
    if stale:
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
      stale = (
        needs_poster_convert(src, dest)
        if kind == "poster" else needs_update(src, dest)
      )
      if stale:
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

  if not skip_trailers:
    stats["trailers"].extend(sync_trailer(team, src_dir, cdn_dir, index, dry_run))

  return stats


def sync_trailer(
  team: str,
  src_dir: Path,
  cdn_dir: Path,
  index: Path,
  dry_run: bool,
) -> list[str]:
  written: list[str] = []
  src = collect_trailer(team, src_dir)
  dest = cdn_dir / TRAILER_NAME
  poster = cdn_dir / TRAILER_POSTER_NAME
  if src is None:
    duration = None
  else:
    duration = probe_duration(src)
    if duration is not None and duration > MAX_TRAILER_SECONDS:
      print(
        f"  skip trailer {src.name}: {duration:.1f}s "
        f"(max {MAX_TRAILER_SECONDS}s)"
      )
      src = None
  if src is None:
    set_trailer(index, None, dry_run)
    for leftover in (dest, poster):
      if leftover.exists():
        written.append(f"removed {cdn_dir.name}/{leftover.name}")
        if not dry_run:
          leftover.unlink(missing_ok=True)
    return written

  cdn_dir.mkdir(parents=True, exist_ok=True)
  encoded = dest.exists() and not needs_update(src, dest)
  if not encoded:
    print(f"  encoding trailer {team} <- {src.name}")
    if encode_trailer(src, dest, dry_run):
      encoded = True
      written.append(f"{cdn_dir.name}/{TRAILER_NAME} <- {src.name}")
  if encoded:
    if dry_run or needs_update(dest if dest.exists() else src, poster) or not poster.exists():
      poster_src = dest if dest.exists() else src
      if extract_trailer_poster(poster_src, poster, dry_run):
        written.append(f"{cdn_dir.name}/{TRAILER_POSTER_NAME}")
    set_trailer(index, TRAILER_NAME, dry_run)
  else:
    set_trailer(index, TRAILER_NAME if dest.exists() else None, dry_run)
  return written


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
  parser.add_argument(
    "--skip-trailers",
    action="store_true",
    help="Do not encode or publish trailers",
  )
  args = parser.parse_args()
  only = {slug.strip() for slug in args.only_team if slug.strip()}

  film_dirs = sorted(
    path for path in CONTENT.iterdir()
    if path.is_dir() and path.name.startswith("2026-")
  )
  stats = {
    "cdn": [], "poster": [], "thumbs": [], "trailers": [],
    "removed": [], "skip": [],
  }
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
    result = import_team(
      team, film_dir, args.skip_thumbs, args.skip_trailers, args.dry_run,
    )
    imported += 1
    for key in ("cdn", "poster", "thumbs", "trailers", "removed"):
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
  print(f"trailers written: {len(stats['trailers'])}")
  for line in stats["trailers"]:
    print(f"  {line}")
  if stats["skip"]:
    print("no film page for:", ", ".join(stats["skip"]))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
