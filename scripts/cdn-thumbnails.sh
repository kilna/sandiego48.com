#!/bin/bash

set -euo pipefail

# Check if yq is installed
if ! command -v yq &> /dev/null; then
  echo "Error: yq is not installed. Please install mikefarah/yq first."
  echo "  brew install yq"
  echo "  or visit: https://github.com/mikefarah/yq#install"
  exit 1
fi

# Check if vips is installed
if ! command -v vips &> /dev/null; then
  echo "Error: vips is not installed. Please install libvips first."
  echo "  brew install libvips"
  exit 1
fi

# Check if parallel is installed
if ! command -v parallel &> /dev/null; then
  echo "Error: GNU parallel is not installed. Please install it first."
  echo "  brew install parallel"
  exit 1
fi

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HUGO_CONFIG="$PROJECT_ROOT/hugo.yaml"
CDN_DIR="$PROJECT_ROOT/cdn"

# Parse command line arguments
FORCE=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --force)
      FORCE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--force]"
      echo "  --force    Clean up all thumbs directories and regenerate all thumbnails"
      exit 1
      ;;
  esac
done

# Function to log messages
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to clean up all thumbs directories
cleanup_thumbs_directories() {
  log "Cleaning up all thumbs directories..."
  
  local cleaned_count=0
  local total_size=0
  
  # Find all thumbs directories in the CDN
  while IFS= read -r -d '' thumbs_dir; do
    if [ -d "$thumbs_dir" ]; then
      local dir_size=$(du -sk "$thumbs_dir" 2>/dev/null | cut -f1 || echo "0")
      local file_count=$(find "$thumbs_dir" -type f | wc -l)
      
      log "  Removing: $thumbs_dir ($file_count files, $(($dir_size / 1024))KB)"
      
      rm -rf "$thumbs_dir"
      cleaned_count=$((cleaned_count + 1))
      total_size=$((total_size + dir_size))
    fi
  done < <(find "$CDN_DIR" -name "thumbs" -type d -print0)
  
  if [ $cleaned_count -gt 0 ]; then
    log "Cleaned up $cleaned_count thumbs directories (freed $(($total_size / 1024))KB)"
  else
    log "No thumbs directories found to clean up"
  fi
}

# Function to generate thumbnail with quality control
generate_thumbnail_with_quality() {
  local input_file="$1"
  local output_file="$2"
  local size="$3"
  local quality="$4"
  
  local temp_file="${output_file}.tmp"
  local extension="${output_file##*.}"
  
  # Generate thumbnail first (use PNG as intermediate format)
  # Resize to fit within size constraint while preserving aspect ratio
  local temp_png="${temp_file%.*}.png"
  if ! vipsthumbnail "$input_file" -s "${size}" -o "$temp_png"; then
    return 1
  fi
  
  # Apply quality based on format
  case "$extension" in
    webp)
      if ! vips webpsave "$temp_png" "$output_file" -Q "$quality"; then
        rm -f "$temp_png"
        return 1
      fi
      ;;
    jpg|jpeg)
      if ! vips jpegsave "$temp_png" "$output_file" -Q "$quality"; then
        rm -f "$temp_png"
        return 1
      fi
      ;;
    png)
      # PNG doesn't use quality, use compression level (0-9, where 9 is highest compression)
      local compression=$((9 - (quality * 9 / 100)))
      if ! vips pngsave "$temp_png" "$output_file" --compression "$compression"; then
        rm -f "$temp_png"
        return 1
      fi
      ;;
    *)
      # For other formats, just copy the temp file
      if ! cp "$temp_png" "$output_file"; then
        rm -f "$temp_png"
        return 1
      fi
      ;;
  esac
  
  # Clean up temp file
  rm -f "$temp_png"
  return 0
}

# Function to generate thumbnails for a directory
generate_thumbnails() {
  local dir_path="$1"
  local image_type="$2"
  local prefix="$3"
  local extension="$4"
  local thumb_size="$5"
  
  log "Processing directory: $dir_path"
  
  # Find all images matching the prefix and extension
  local images=()
  while IFS= read -r -d '' file; do
    images+=("$file")
  done < <(find "$dir_path" -maxdepth 1 -name "${prefix}*.${extension}" -type f -print0)
  
  if [ ${#images[@]} -eq 0 ]; then
    log "No images found matching pattern: ${prefix}*.${extension}"
    return 0
  fi
  
  log "Found ${#images[@]} images to process"
  
  # Create a list of all thumbnail generation commands
  local thumbnail_commands=()
  
  # Build list of commands to execute in parallel
  local commands=()
  local skipped_count=0
  local generated_count=0
  
  # Process each image to build command list
  for image in "${images[@]}"; do
    local basename=$(basename "$image" ".${extension}")
    local dirname=$(dirname "$image")
    
    log "Processing: $(basename "$image")"
    
    # Generate thumbnail with single size
    local size="$thumb_size"
    local suffix="-${size}"
    local thumb_ext="webp"
    local quality="95"
    
    local thumbs_dir="${dirname}/thumbs"
    local output_file="${thumbs_dir}/${basename}${suffix}.${thumb_ext}"
    
    # Create thumbs directory if it doesn't exist
    mkdir -p "$thumbs_dir"
    
    # Skip if thumbnail already exists and is newer than source (unless --force is used)
    if [ "$FORCE" = false ] && [ -f "$output_file" ] && [ "$output_file" -nt "$image" ]; then
      log "  Skipping ${basename}${suffix}.${thumb_ext} (already up to date)"
      continue
    fi
    
    log "  Generating ${basename}${suffix}.${thumb_ext} (${size}x${size})"
    
    # Add command to list for parallel execution
    local cmd="generate_thumbnail_with_quality \"$image\" \"$output_file\" \"$size\" \"$quality\""
    commands+=("$cmd")
  done
  
  # Export the function so parallel can use it
  export -f generate_thumbnail_with_quality
  
  # Execute commands in parallel if any exist
  if [ ${#commands[@]} -gt 0 ]; then
    log "Executing ${#commands[@]} thumbnail generation commands in parallel"
    printf '%s\n' "${commands[@]}" | parallel -j+0 --line-buffer --tag
    log "Parallel thumbnail generation completed"
  else
    log "No thumbnails to generate (all up to date)"
  fi
}

# Main execution
main() {
  log "Starting CDN thumbnail generation"
  log "Project root: $PROJECT_ROOT"
  log "CDN directory: $CDN_DIR"
  if [ "$FORCE" = true ]; then
    log "Force mode: Will clean up all thumbs directories and regenerate all thumbnails"
  else
    log "Normal mode: Will skip existing up-to-date thumbnails"
  fi
  
  if [ ! -f "$HUGO_CONFIG" ]; then
    log "Error: Hugo config file not found: $HUGO_CONFIG"
    exit 1
  fi
  
  if [ ! -d "$CDN_DIR" ]; then
    log "Error: CDN directory not found: $CDN_DIR"
    exit 1
  fi
  
  # Clean up thumbs directories if force mode is enabled
  if [ "$FORCE" = true ]; then
    cleanup_thumbs_directories
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
  for hugo_type in $(echo "$cdn_galleries_config" | yq eval 'keys | .[]' -); do
    log "Processing Hugo type: $hugo_type"
    
    # Get all gallery IDs for this Hugo type
    local gallery_ids=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type} | keys | .[]" -)
    
    # Process each gallery configuration for this Hugo type
    for gallery_id in $gallery_ids; do
      local name=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type}.${gallery_id}.name" -)
      local prefix=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type}.${gallery_id}.prefix // \"${gallery_id}-\"" -)
      local extension=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type}.${gallery_id}.extension" -)
      local thumb_size=$(echo "$cdn_galleries_config" | yq eval ".${hugo_type}.${gallery_id}.thumb_size" -)
      
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
      
      # Find all directories under cdn/$cdn_dir_name
      local type_dir="$CDN_DIR/$cdn_dir_name"
      if [ ! -d "$type_dir" ]; then
        log "  Directory not found: $type_dir"
        continue
      fi
      
      # Process each subdirectory
      while IFS= read -r -d '' subdir; do
        generate_thumbnails "$subdir" "$cdn_dir_name" "$prefix" "$extension" "$thumb_size"
      done < <(find "$type_dir" -type d -mindepth 1 -print0)
    done
  done
  
  log "CDN thumbnail generation completed"
}

# Run main function
main "$@"


