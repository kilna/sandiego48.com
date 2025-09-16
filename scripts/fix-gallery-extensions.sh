#!/bin/bash

# Fix Gallery Extensions Script
# Converts all gallery images to the correct extension expected by Hugo configuration
# All galleries expect .jpg extension

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CDN_ROOT="./cdn"
BACKUP_DIR="./backup-images-$(date +%Y%m%d-%H%M%S)"
DRY_RUN=${1:-false}

# Gallery types and their expected extensions (all expect jpg)
GALLERY_TYPES="bts still poster group photo gallery"

# Supported input extensions to convert from
INPUT_EXTENSIONS="png jpeg PNG JPEG"

log() {
  echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
  echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
  echo -e "${RED}❌${NC} $1"
}

# Function to convert image using ImageMagick
convert_image() {
  local input_file="$1"
  local output_file="$2"
  local dry_run="$3"
  
  if [ "$dry_run" = "true" ]; then
    log "Would convert: $input_file -> $output_file"
    return 0
  fi
  
  # Check if ImageMagick is available
  if ! command -v convert &> /dev/null; then
    log_error "ImageMagick 'convert' command not found. Please install ImageMagick."
    return 1
  fi
  
  # Convert the image
  if convert "$input_file" -quality 90 "$output_file"; then
    log_success "Converted: $input_file -> $output_file"
    return 0
  else
    log_error "Failed to convert: $input_file"
    return 1
  fi
}

# Function to process a single directory
process_directory() {
  local dir_path="$1"
  local content_type="$2"
  local dry_run="$3"
  local converted_count=0
  local error_count=0
  
  if [ ! -d "$dir_path" ]; then
    return 0
  fi
  
  log "Processing directory: $dir_path"
  
  # Process each gallery type
  for gallery_type in $GALLERY_TYPES; do
    local expected_ext="jpg"
    
    # Find files with wrong extensions for this gallery type
    for input_ext in $INPUT_EXTENSIONS; do
      # Find files matching pattern: gallery_type-XXX.input_ext
      find "$dir_path" -maxdepth 1 -name "${gallery_type}-*.${input_ext}" -type f | while read -r input_file; do
        local basename_no_ext=$(basename "$input_file" ".${input_ext}")
        local output_file="${dir_path}/${basename_no_ext}.${expected_ext}"
        
        # Skip if output file already exists
        if [ -f "$output_file" ]; then
          log_warning "Output file already exists, skipping: $output_file"
          continue
        fi
        
        # Create backup if not dry run
        if [ "$dry_run" = "false" ]; then
          mkdir -p "$BACKUP_DIR/$(dirname "$input_file")"
          cp "$input_file" "$BACKUP_DIR/$input_file"
        fi
        
        # Convert the image
        if convert_image "$input_file" "$output_file" "$dry_run"; then
          ((converted_count++))
          
          # Remove original file if conversion successful and not dry run
          if [ "$dry_run" = "false" ]; then
            rm "$input_file"
            log "Removed original: $input_file"
          fi
        else
          ((error_count++))
        fi
      done
    done
  done
  
  if [ $converted_count -gt 0 ]; then
    log_success "Converted $converted_count files in $dir_path"
  fi
  
  if [ $error_count -gt 0 ]; then
    log_error "Failed to convert $error_count files in $dir_path"
  fi
}

# Main execution
main() {
  log "Starting gallery extension fix..."
  
  if [ "$DRY_RUN" = "true" ]; then
    log_warning "DRY RUN MODE - No files will be modified"
  else
    log "Creating backup directory: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
  fi
  
  # Process films
  log "Processing films..."
  for film_dir in "$CDN_ROOT/films"/*/; do
    if [ -d "$film_dir" ]; then
      process_directory "$film_dir" "films" "$DRY_RUN"
    fi
  done
  
  # Process events
  log "Processing events..."
  for event_dir in "$CDN_ROOT/events"/*/; do
    if [ -d "$event_dir" ]; then
      process_directory "$event_dir" "events" "$DRY_RUN"
    fi
  done
  
  # Process people
  log "Processing people..."
  for person_dir in "$CDN_ROOT/people"/*/; do
    if [ -d "$person_dir" ]; then
      process_directory "$person_dir" "people" "$DRY_RUN"
    fi
  done
  
  log_success "Gallery extension fix completed!"
  
  if [ "$DRY_RUN" = "false" ]; then
    log "Backup created at: $BACKUP_DIR"
    log "You can restore files from backup if needed"
  fi
}

# Show usage
show_usage() {
  echo "Usage: $0 [dry-run]"
  echo ""
  echo "Arguments:"
  echo "  dry-run    Run in dry-run mode (show what would be done without making changes)"
  echo ""
  echo "Examples:"
  echo "  $0          # Convert all files"
  echo "  $0 dry-run  # Show what would be converted without making changes"
  echo ""
  echo "This script will:"
  echo "  1. Find all gallery images with wrong extensions (png, jpeg, etc.)"
  echo "  2. Convert them to .jpg (the expected extension)"
  echo "  3. Create backups of original files"
  echo "  4. Remove original files after successful conversion"
}

# Check arguments
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  show_usage
  exit 0
fi

# Run main function
main
