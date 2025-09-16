#!/bin/bash
# Remove film images that are NOT referenced in index.md files
# This ensures we keep the main poster images that are referenced

set -euo pipefail

echo "🎬 Removing unreferenced film images from git..."

# Create lists
safe_to_remove=()
keep_files=()

echo "🔍 Checking which images are safe to remove..."

# Find all image files in content/films
for file in $(find content/films -name "*.jpg" -o -name "*.png" -o -name "*.jpeg"); do
    film_dir=$(dirname "$file")
    image_name=$(basename "$file")
    index_file="$film_dir/index.md"
    
    if [[ ! -f "$index_file" ]]; then
        echo "⚠️  Keep: $file (no index.md found)"
        keep_files+=("$file")
        continue
    fi
    
    # Check if the image is referenced in the index.md file
    if grep -q "image:.*$image_name" "$index_file"; then
        keep_files+=("$file")
        echo "⚠️  Keep: $file (referenced in index.md)"
    else
        safe_to_remove+=("$file")
        echo "✅ Safe to remove: $file (not referenced)"
    fi
done

echo ""
echo "📊 Summary:"
echo "   Safe to remove: ${#safe_to_remove[@]} files"
echo "   Keep (referenced): ${#keep_files[@]} files"

if [[ ${#safe_to_remove[@]} -eq 0 ]]; then
    echo "❌ No unreferenced files found to remove"
    exit 0
fi

echo ""
echo "🗑️  Files to be removed (unreferenced):"
printf '%s\n' "${safe_to_remove[@]}"

echo ""
echo "📋 Files to be kept (referenced in index.md):"
printf '%s\n' "${keep_files[@]}"

echo ""
read -p "Remove these ${#safe_to_remove[@]} unreferenced files from git? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "🗑️  Removing unreferenced files from git..."

# Remove files from git index
for file in "${safe_to_remove[@]}"; do
    echo "Removing: $file"
    git rm --cached "$file" 2>/dev/null || true
done

echo "✅ Unreferenced files removed from git index"
echo ""
echo "📝 Next steps:"
echo "1. Review the changes: git status"
echo "2. Commit the removal: git commit -m 'Remove unreferenced film images'"
echo "3. Push the changes: git push"
