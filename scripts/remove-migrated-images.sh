#!/bin/bash
# Remove migrated film images from git history to speed up checkouts
# This script removes images that are now served from CDN

set -euo pipefail

echo "🎬 Removing migrated film images from git history..."

# Create a list of image files to remove
echo "📋 Creating list of images to remove..."

# Find all image files in content/films
find content/films -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" > /tmp/images_to_remove.txt

echo "Found $(wc -l < /tmp/images_to_remove.txt) image files to remove"

# Show some examples
echo "📸 Examples of files to be removed:"
head -5 /tmp/images_to_remove.txt

echo ""
echo "⚠️  This will remove these images from git history permanently."
echo "   The images will still be available via CDN."
echo "   Make sure you have a backup if needed."
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "🗑️  Removing images from git history..."

# Remove each file from git history
while IFS= read -r file; do
    if [[ -f "$file" ]]; then
        echo "Removing: $file"
        git rm --cached "$file" 2>/dev/null || true
    fi
done < /tmp/images_to_remove.txt

# Clean up temp file
rm -f /tmp/images_to_remove.txt

echo "✅ Images removed from git index"
echo ""
echo "📝 Next steps:"
echo "1. Commit the removal: git commit -m 'Remove migrated film images from git history'"
echo "2. Optionally rewrite history: git filter-branch --index-filter 'git rm --cached --ignore-unmatch content/films/*/*.{jpg,png,jpeg}' HEAD"
echo ""
echo "⚠️  Note: Rewriting history will change commit hashes and require force push"
echo "   Only do this if you're sure and have coordinated with other contributors"
