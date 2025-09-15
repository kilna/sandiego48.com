#!/bin/bash

set -euo pipefail

# Check if yq is installed
if ! command -v yq &> /dev/null; then
  echo "Error: yq is not installed. Please install mikefarah/yq first."
  echo "  brew install yq"
  echo "  or visit: https://github.com/mikefarah/yq#install"
  exit 1
fi

# No command line arguments needed

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

# Function to count images in a directory
count_images() {
  local dir_path="$1"
  local prefix="$2"
  local extension="$3"
  
  if [ ! -d "$dir_path" ]; then
    echo "0"
    return
  fi
  
  find "$dir_path" -maxdepth 1 -name "${prefix}*.${extension}" -type f | wc -l
}

# Function to validate contiguous image numbering
validate_contiguous_images() {
  local dir_path="$1"
  local prefix="$2"
  local extension="$3"
  
  if [ ! -d "$dir_path" ]; then
    return 0
  fi
  
  # Get all matching files and extract numbers
  local files
  files=$(find "$dir_path" -maxdepth 1 -name "${prefix}*.${extension}" -type f | sort -V)
  
  if [ -z "$files" ]; then
    return 0  # No files found, nothing to validate
  fi
  
  # Extract numbers from filenames
  local numbers=()
  while IFS= read -r file; do
    local basename=$(basename "$file" ".${extension}")
    # Remove prefix and extract number
    local number="${basename#$prefix}"
    # Check if it's a valid number
    if [[ "$number" =~ ^[0-9]+$ ]]; then
      numbers+=("$number")
    else
      log "  Warning: Non-numeric filename found: $file"
    fi
  done <<< "$files"
  
  if [ ${#numbers[@]} -eq 0 ]; then
    return 0  # No valid numbers found
  fi
  
  # Sort numbers numerically
  IFS=$'\n' numbers=($(sort -n <<<"${numbers[*]}"))
  unset IFS
  
  # Check if numbering starts at 1 (handle zero-padded numbers)
  local first_num=$((10#${numbers[0]}))  # Force base-10 interpretation
  if [ "$first_num" -ne 1 ]; then
    log "  Error: Image numbering must start at 1, but found: ${numbers[0]}"
    return 1
  fi
  
  # Check for gaps
  local prev_num=1
  local gaps=()
  
  for num in "${numbers[@]}"; do
    local current_num=$((10#${num}))  # Force base-10 interpretation
    if [ "$current_num" -ne "$prev_num" ]; then
      gaps+=("$prev_num")
    fi
    prev_num=$((current_num + 1))
  done
  
  # Report gaps if found
  if [ ${#gaps[@]} -gt 0 ]; then
    log "  Error: Non-contiguous image filenames found in $dir_path"
    log "  Missing numbers: ${gaps[*]}"
    log "  Found numbers: ${numbers[*]}"
    return 1
  fi
  
  return 0
}

# Function to update a markdown file with CDN image count
update_markdown_file() {
  local file_path="$1"
  local gallery_id="$2"
  local count="$3"
  
  if [ ! -f "$file_path" ]; then
    log "Content file not found: $file_path"
    return 1
  fi
  
  # Check if file has frontmatter
  if ! head -1 "$file_path" | grep -q "^---$"; then
    log "File does not have frontmatter: $file_path"
    return 1
  fi
  
  # Don't update if count is 0 (no images)
  if [ "$count" -eq 0 ]; then
    log "  Skipping $(basename "$file_path") (no images found)"
    return 0
  fi
  
  # Create backup of original file
  local backup_file="${file_path}.bak"
  cp "$file_path" "$backup_file"
  
  # Extract frontmatter and content using a more robust method
  local temp_file=$(mktemp)
  local content_file=$(mktemp)
  
  # Find the end of frontmatter (second ---)
  local frontmatter_end_line
  frontmatter_end_line=$(awk '/^---$/ { if (++count == 2) { print NR; exit } }' "$file_path")
  
  if [ -z "$frontmatter_end_line" ]; then
    log "  Error: Could not find end of frontmatter in $file_path"
    rm -f "$temp_file" "$content_file" "$backup_file"
    return 1
  fi
  
  # Extract frontmatter (lines 2 to frontmatter_end_line-1)
  sed -n "2,$((frontmatter_end_line-1))p" "$file_path" > "$temp_file"
  
  # Extract content (lines after frontmatter_end_line)
  sed -n "$((frontmatter_end_line+1)),\$p" "$file_path" > "$content_file"
  
          # Determine Hugo type from file path
          local hugo_type
          hugo_type=$(echo "$file_path" | sed 's|.*/content/\([^/]*\)/.*|\1|')
          
          # Check if we need to update
          local current_count
          current_count=$(yq eval ".params.cdn.galleries.${gallery_id}.count // 0" "$temp_file" 2>/dev/null || echo "0")

          if [ "$current_count" = "$count" ]; then
            log "  Skipping $(basename "$file_path") (count unchanged: $count)"
            rm -f "$temp_file" "$content_file" "$backup_file"
            return 0
          fi

          # Update the frontmatter using yq
          # Ensure params exists
          yq eval '.params = (.params // {})' -i "$temp_file"
          # Ensure cdn exists under params
          yq eval '.params.cdn = (.params.cdn // {})' -i "$temp_file"
          # Ensure galleries exists under cdn
          yq eval '.params.cdn.galleries = (.params.cdn.galleries // {})' -i "$temp_file"
          # Set the count using gallery ID as key directly under galleries
          yq eval ".params.cdn.galleries.${gallery_id}.count = $count" -i "$temp_file"
  
  # Reconstruct the file with proper formatting
  {
    echo "---"
    cat "$temp_file"
    echo "---"
    cat "$content_file"
  } > "$file_path"
  
  log "  Updated $(basename "$file_path"): $hugo_type.$gallery_id = $count"
  
  # Cleanup
  rm -f "$temp_file" "$content_file" "$backup_file"
  return 0
}

# Main execution
main() {
  log "Starting CDN image count update"
  log "Project root: $PROJECT_ROOT"
  log "CDN directory: $CDN_DIR"
  log "Content directory: $CONTENT_DIR"
  
  
  if [ ! -f "$HUGO_CONFIG" ]; then
    log "Error: Hugo config file not found: $HUGO_CONFIG"
    exit 1
  fi
  
  if [ ! -d "$CDN_DIR" ]; then
    log "Error: CDN directory not found: $CDN_DIR"
    exit 1
  fi
  
  if [ ! -d "$CONTENT_DIR" ]; then
    log "Error: Content directory not found: $CONTENT_DIR"
    exit 1
  fi
  
  # Read cdn.galleries configuration from hugo.yaml
  local cdn_galleries_config
  if ! cdn_galleries_config=$(yq eval '.params.cdn.galleries' "$HUGO_CONFIG" -o json); then
    log "Error: Failed to read cdn.galleries configuration from $HUGO_CONFIG"
    exit 1
  fi

  if [ "$cdn_galleries_config" = "null" ]; then
    log "No cdn.galleries configuration found in $HUGO_CONFIG"
    exit 0
  fi
  
  # Process each Hugo type (e.g., films, events)
  local updated_files=0
  for hugo_type in $(echo "$cdn_galleries_config" | yq eval 'keys | .[]' -); do
    log "Processing Hugo type: $hugo_type"
    
    # Get all gallery IDs for this Hugo type
    local gallery_ids=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type} | keys | .[]" -)
    
    # Process each gallery configuration for this Hugo type
    for gallery_id in $gallery_ids; do
      local name=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type}.${gallery_id}.name" -)
      local prefix=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type}.${gallery_id}.prefix // \"${gallery_id}-\"" -)
      local extension=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type}.${gallery_id}.extension" -)
      
      log "  Gallery: $name"
      log "  Prefix: $prefix"
      log "  Extension: $extension"
      
      # Map gallery name to CDN directory name
      local cdn_dir_name
      case "$name" in
        "Posters") cdn_dir_name="posters" ;;
        "Film Stills") cdn_dir_name="film-stills" ;;
        "Behind the Scenes") cdn_dir_name="bts" ;;
        "Group Photos") cdn_dir_name="group-photos" ;;
        "Event Photos") cdn_dir_name="events" ;;
        *) cdn_dir_name=$(echo "$name" | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g') ;;
      esac
      
      # Find CDN directories for this gallery
      local cdn_type_dir="$CDN_DIR/$cdn_dir_name"
      if [ ! -d "$cdn_type_dir" ]; then
        log "  CDN directory not found: $cdn_type_dir"
        continue
      fi
      
      # Find content directories for this Hugo type
      local content_type_dir="$CONTENT_DIR/$hugo_type"
      if [ ! -d "$content_type_dir" ]; then
        log "  Content directory not found: $content_type_dir"
        continue
      fi
      
      # Process each subdirectory
      while IFS= read -r -d '' cdn_subdir; do
        local slug=$(basename "$cdn_subdir")
        log "  Processing slug: $slug"
        
        # Count images in CDN directory
        local count
        count=$(count_images "$cdn_subdir" "$prefix" "$extension")
        log "    Found $count images matching ${prefix}*.${extension}"
        
        # Validate contiguous numbering if images exist
        if [ "$count" -gt 0 ]; then
          if ! validate_contiguous_images "$cdn_subdir" "$prefix" "$extension"; then
            log "    Skipping $slug due to non-contiguous image numbering"
            continue
          fi
        fi
        
        # Find corresponding content file
        local content_subdir="$content_type_dir/$slug"
        local content_file="$content_subdir/index.md"
        
        if [ ! -f "$content_file" ]; then
          log "    Content file not found: $content_file"
          continue
        fi
        
        # Update the content file with the gallery ID as the key
        if update_markdown_file "$content_file" "$gallery_id" "$count"; then
          ((updated_files++))
        fi
      done < <(find "$cdn_type_dir" -type d -mindepth 1 -not -name "thumbs" -print0)
    done
  done
  
  log "CDN image count update completed. $updated_files files updated."
}

# Run main function
main "$@"
