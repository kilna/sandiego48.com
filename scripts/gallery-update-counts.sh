#!/bin/bash

set -euo pipefail

# Check if yq is installed
if ! command -v yq &> /dev/null; then
  echo "Error: yq is not installed. Please install mikefarah/yq first."
  echo "  brew install yq"
  echo "  or visit: https://github.com/mikefarah/yq#install"
  exit 1
fi

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HUGO_CONFIG="$PROJECT_ROOT/hugo.yaml"
CDN_DIR="$PROJECT_ROOT/cdn"
CONTENT_DIR="$PROJECT_ROOT/content"

# Function to log messages
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to count images in a film directory
count_images_in_film_dir() {
  local film_dir="$1"
  local prefix="$2"
  local extension="$3"
  
  if [ ! -d "$film_dir" ]; then
    echo "0"
    return
  fi
  
  find "$film_dir" -maxdepth 1 -name "${prefix}*.${extension}" -o -name "${prefix}*.jpg" -o -name "${prefix}*.png" -o -name "${prefix}*.jpeg" | wc -l | tr -d ' '
}

# Function to update markdown file with new count
update_markdown_file() {
  local md_file="$1"
  local gallery_id="$2"
  local count="$3"
  
  if [ ! -f "$md_file" ]; then
    log "    File not found: $md_file"
    return 1
  fi
  
  # Use yq to update the count
  yq eval -i ".params.galleries.${gallery_id}.count = $count" "$md_file"
  log "    Updated $md_file: $gallery_id = $count"
}

log "Starting gallery image count update (content-mirrored structure)"
log "Project root: $PROJECT_ROOT"
log "CDN directory: $CDN_DIR"
log "Content directory: $CONTENT_DIR"

# Read gallery configurations from hugo.yaml
galleries_config=$(yq eval '.params.galleries' "$HUGO_CONFIG")

if [ "$galleries_config" = "null" ] || [ -z "$galleries_config" ]; then
  log "Error: No galleries configuration found in $HUGO_CONFIG"
  exit 1
fi

# Process each Hugo type (events, films, people)
for hugo_type in events films people; do
  log "Processing Hugo type: $hugo_type"
  
  # Get galleries for this type
  type_galleries=$(echo "$galleries_config" | yq eval ".$hugo_type")
  
  if [ "$type_galleries" = "null" ] || [ -z "$type_galleries" ]; then
    log "  No galleries configured for $hugo_type"
    continue
  fi
  
  # Process each gallery in this type
  echo "$type_galleries" | yq eval 'keys | .[]' | while read -r gallery_id; do
    gallery_config=$(echo "$type_galleries" | yq eval ".$gallery_id")
    
    if [ "$gallery_config" = "null" ]; then
      continue
    fi
    
    name=$(echo "$gallery_config" | yq eval '.name // ""')
    prefix=$(echo "$gallery_config" | yq eval '.prefix // ""')
    extension=$(echo "$gallery_config" | yq eval '.extension // "jpg"')
    
    # Default prefix if not specified
    if [ -z "$prefix" ]; then
      prefix="${gallery_id}-"
    fi
    
    log "  Gallery: $name"
    log "  Prefix: $prefix"
    log "  Extension: $extension"
    
    # Process each content directory for this type
    content_type_dir="$CONTENT_DIR/$hugo_type"
    
    if [ ! -d "$content_type_dir" ]; then
      log "  Content directory not found: $content_type_dir"
      continue
    fi
    
    # Find all subdirectories (content items)
    find "$content_type_dir" -mindepth 1 -maxdepth 1 -type d | while read -r content_dir; do
      slug=$(basename "$content_dir")
      md_file="$content_dir/index.md"
      
      if [ ! -f "$md_file" ]; then
        continue
      fi
      
      # Use content-mirrored CDN directory structure
      cdn_subdir="$CDN_DIR/$hugo_type/$slug"
      
      # Count images in the CDN directory
      image_count=$(count_images_in_film_dir "$cdn_subdir" "$prefix" "$extension")
      
      if [ "$image_count" -gt 0 ]; then
        log "    Found $image_count images in $slug"
        update_markdown_file "$md_file" "$gallery_id" "$image_count"
      fi
    done
  done
done

log "Gallery image count update completed."
