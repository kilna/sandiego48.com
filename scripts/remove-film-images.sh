#!/bin/bash
# Remove film images from git that are now served from CDN
# This is a simpler approach that removes all film images

set -euo pipefail

echo "🎬 Removing film images from git (now served from CDN)..."

# Check current repository size
echo "📊 Current repository size:"
du -sh .git

echo ""
echo "🔍 Found image files in content/films:"
find content/films -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" | wc -l

echo ""
echo "📸 CDN has $(find cdn/films -name "*.jpg" | wc -l) images available"
echo ""

# Show some examples of what will be removed
echo "📋 Examples of files to be removed:"
find content/films -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" | head -5

echo ""
echo "⚠️  This will remove all film images from git history."
echo "   Images will still be available via CDN at cdn.sandiego48.com"
echo "   This will significantly reduce repository size and speed up checkouts."
echo ""

read -p "Continue with removal? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "🗑️  Removing film images from git..."

# Remove all image files from git index
find content/films -name "*.jpg" -o -name "*.png" -o -name "*.jpeg" | while read -r file; do
    if [[ -f "$file" ]]; then
        echo "Removing: $file"
        git rm --cached "$file" 2>/dev/null || true
    fi
done

echo "✅ Film images removed from git index"
echo ""
echo "📊 Repository size after removal:"
du -sh .git

echo ""
echo "📝 Next steps:"
echo "1. Review changes: git status"
echo "2. Commit removal: git commit -m 'Remove film images now served from CDN'"
echo "3. Push changes: git push"
echo ""
echo "💡 To completely remove from history (optional):"
echo "   ./scripts/rewrite-git-history.sh"
echo "   (This will change commit hashes and require force push)"
