#!/bin/bash
# Safely remove film images that are confirmed to be in CDN
# This script only removes images that have corresponding files in the CDN

set -euo pipefail

echo "🎬 Safely removing film images that are confirmed in CDN..."

# Function to check if image exists in CDN
check_cdn_exists() {
    local content_file="$1"
    local film_dir=$(dirname "$content_file")
    local film_slug=$(basename "$film_dir")
    local filename=$(basename "$content_file")
    local name_without_ext="${filename%.*}"
    local ext="${filename##*.}"
    
    # Convert to lowercase for comparison
    local cdn_dir="cdn/films/$film_slug"
    
    # Check if CDN directory exists
    if [[ ! -d "$cdn_dir" ]]; then
        return 1
    fi
    
    # Check for various possible CDN filenames
    # Look for poster files
    if [[ "$filename" =~ ^poster-.*\.(jpg|png|jpeg)$ ]]; then
        # This is a poster file, check if it exists in CDN
        if [[ -f "$cdn_dir/$filename" ]]; then
            return 0
        fi
    fi
    
    # Look for team-name files that might be posters
    if [[ "$filename" =~ ^$film_slug\.(jpg|png|jpeg)$ ]]; then
        # Check if there are any poster files in CDN for this film
        if ls "$cdn_dir"/poster-*.jpg 1> /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # For other files, check if they exist in CDN with same name
    if [[ -f "$cdn_dir/$filename" ]]; then
        return 0
    fi
    
    return 1
}

# Create lists
safe_to_remove=()
keep_files=()

echo "🔍 Checking which images are safe to remove..."

# Find all image files in content/films
while IFS= read -r -d '' file; do
    if check_cdn_exists "$file"; then
        safe_to_remove+=("$file")
        echo "✅ Safe to remove: $file"
    else
        keep_files+=("$file")
        echo "⚠️  Keep: $file (not found in CDN)"
    fi
done < <(find content/films -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" -print0)

echo ""
echo "📊 Summary:"
echo "   Safe to remove: ${#safe_to_remove[@]} files"
echo "   Keep: ${#keep_files[@]} files"

if [[ ${#safe_to_remove[@]} -eq 0 ]]; then
    echo "❌ No files are safe to remove"
    exit 0
fi

echo ""
echo "🗑️  Files to be removed:"
printf '%s\n' "${safe_to_remove[@]}"

echo ""
read -p "Remove these ${#safe_to_remove[@]} files from git? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "🗑️  Removing files from git..."

# Remove files from git index
for file in "${safe_to_remove[@]}"; do
    echo "Removing: $file"
    git rm --cached "$file" 2>/dev/null || true
done

echo "✅ Files removed from git index"
echo ""
echo "📝 Next steps:"
echo "1. Review the changes: git status"
echo "2. Commit the removal: git commit -m 'Remove film images now served from CDN'"
echo "3. Push the changes: git push"
echo ""
echo "💡 To completely remove from history later, use:"
echo "   ./scripts/rewrite-git-history.sh"
