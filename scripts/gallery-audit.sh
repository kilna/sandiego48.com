#!/bin/bash

set -euo pipefail

# Script to audit galleries and check if image counts match actual files
# Also checks for file extension mismatches

# Check if yq is installed
if ! command -v yq &> /dev/null; then
  echo "Error: yq is not installed. Please install mikefarah/yq first."
  echo "  brew install yq"
  echo "  or visit: https://github.com/mikefarah/yq#install"
  exit 1
fi

PROJECT_ROOT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"
CDN_ROOT="$PROJECT_ROOT/cdn"
CONTENT_ROOT="$PROJECT_ROOT/content"
HUGO_CONFIG="$PROJECT_ROOT/hugo.yaml"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Auditing galleries for image count and extension mismatches..."

total_mismatches=0
total_extension_errors=0
total_files_checked=0

# Iterate over Hugo content types (events, films, people)
for hugo_type in "events" "films" "people"; do
  # Get all gallery IDs for the current Hugo type
  gallery_ids=$(yq eval ".params.galleries.${hugo_type} | keys | .[]" "$HUGO_CONFIG" 2>/dev/null || true)
  
  if [ -z "$gallery_ids" ]; then
    continue
  fi
  
  # Use content-mirrored CDN directory structure
  cdn_type_dir="$hugo_type"
  
  # Find all content files for the current Hugo type
  find "$CONTENT_ROOT/$hugo_type" -type f -name "index.md" | while read -r md_file; do
    slug=$(basename "$(dirname "$md_file")")
    log "Checking: $slug"
    total_files_checked=$((total_files_checked + 1))
    
    for gallery_id in $gallery_ids; do
      # Get gallery configuration
      expected_extension=$(yq eval ".params.galleries.${hugo_type}.${gallery_id}.extension // \"jpg\"" "$HUGO_CONFIG" | tr -d '\n\r' | xargs)
      prefix=$(yq eval ".params.galleries.${hugo_type}.${gallery_id}.prefix // \"${gallery_id}-\"" "$HUGO_CONFIG" | tr -d '\n\r' | xargs)
      
      # Get the frontmatter count for this gallery type
      frontmatter_count=$(yq eval ".params.galleries.${gallery_id}.count" "$md_file" 2>/dev/null || echo "0")
      frontmatter_count=$(echo "$frontmatter_count" | tr -d '\n\r' | xargs)
      # Handle null values and malformed data
      if [ "$frontmatter_count" = "null" ] || [ -z "$frontmatter_count" ] || [[ "$frontmatter_count" =~ null ]]; then
        frontmatter_count=0
      fi
      
      # Skip if no images expected
      if [ "$frontmatter_count" -eq 0 ]; then
        continue
      fi
      
      # Construct the actual CDN directory path for this specific gallery
      actual_cdn_path="$CDN_ROOT/$cdn_type_dir/$slug"
      
      if [ ! -d "$actual_cdn_path" ]; then
        echo "❌ MISSING DIRECTORY: $actual_cdn_path"
        total_mismatches=$((total_mismatches + 1))
        continue
      fi
      
      # Count actual files with expected extension
      expected_files=0
      if [ -d "$actual_cdn_path" ]; then
        expected_files=$(find "$actual_cdn_path" -maxdepth 1 -name "${prefix}*.${expected_extension}" -type f | wc -l | tr -d ' ')
      fi
      
      # Count files with wrong extensions
      wrong_extension_files=0
      wrong_extension_list=""
      if [ -d "$actual_cdn_path" ]; then
        # Find files with the right prefix but wrong extension
        all_matching_files=$(find "$actual_cdn_path" -maxdepth 1 -name "${prefix}*.*" -type f | grep -v "\.${expected_extension}$" || true)
        if [ -n "$all_matching_files" ]; then
          wrong_extension_files=$(echo "$all_matching_files" | wc -l | tr -d ' ')
          wrong_extension_list=$(echo "$all_matching_files" | xargs -I {} basename {} | tr '\n' ' ')
        fi
      fi
      
      # Check for count mismatch
      total_actual_files=$((expected_files + wrong_extension_files))
      if [ "$frontmatter_count" -ne "$total_actual_files" ]; then
        echo "❌ COUNT MISMATCH in $slug:"
        echo "   Gallery: $gallery_id"
        echo "   Frontmatter count: $frontmatter_count"
        echo "   Actual files: $total_actual_files (${expected_files} correct + ${wrong_extension_files} wrong ext)"
        total_mismatches=$((total_mismatches + 1))
      fi
      
      # Check for extension mismatches
      if [ "$wrong_extension_files" -gt 0 ]; then
        echo "❌ EXTENSION MISMATCH in $slug:"
        echo "   Gallery: $gallery_id"
        echo "   Expected extension: .$expected_extension"
        echo "   Wrong extension files: $wrong_extension_list"
        total_extension_errors=$((total_extension_errors + 1))
      fi
      
      # Success message if everything is correct
      if [ "$frontmatter_count" -eq "$expected_files" ] && [ "$wrong_extension_files" -eq 0 ]; then
        echo "  ✅ $gallery_id: $expected_files files (matches, correct extension)"
            fi
          done
      done
done

log "Audit Summary:"
log "Total content files checked: $total_files_checked"
log "Count mismatches found: $total_mismatches"
log "Extension mismatches found: $total_extension_errors"

if [ "$total_mismatches" -eq 0 ] && [ "$total_extension_errors" -eq 0 ]; then
  log "🎉 All gallery counts and extensions match!"
  exit 0
else
  log "⚠️  Found issues:"
  [ "$total_mismatches" -gt 0 ] && log "  - $total_mismatches count mismatches"
  [ "$total_extension_errors" -gt 0 ] && log "  - $total_extension_errors extension mismatches"
  log ""
  log "💡 To fix extension mismatches, run: ./scripts/convert-gallery-images.sh"
  log "💡 To fix count mismatches, run: ./scripts/gallery-update-counts.sh"
  exit 1
fi