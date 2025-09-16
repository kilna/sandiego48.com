#!/bin/bash
# Completely rewrite git history to remove migrated film images
# WARNING: This will change all commit hashes and require force push

set -euo pipefail

echo "🚨 WARNING: This will rewrite git history and change all commit hashes!"
echo "   This should only be done if:"
echo "   - You have coordinated with all contributors"
echo "   - You have a backup of the repository"
echo "   - You understand this will require force push"
echo ""

read -p "Are you absolutely sure you want to continue? (type 'yes' to confirm): " -r
if [[ $REPLY != "yes" ]]; then
    echo "❌ Cancelled"
    exit 1
fi

echo "🗑️  Rewriting git history to remove film images..."

# Create a backup branch first
echo "📦 Creating backup branch..."
git branch backup-before-image-removal

# Use git filter-branch to remove all image files from history
echo "🔄 Rewriting history (this may take a while)..."
git filter-branch --index-filter '
    git rm --cached --ignore-unmatch content/films/*/*.jpg content/films/*/*.png content/films/*/*.jpeg
' --prune-empty --tag-name-filter cat -- --all

echo "✅ Git history rewritten!"
echo ""
echo "📊 Repository size before cleanup:"
du -sh .git

# Clean up refs
echo "🧹 Cleaning up refs..."
git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "📊 Repository size after cleanup:"
du -sh .git

echo ""
echo "✅ History rewrite complete!"
echo ""
echo "📝 Next steps:"
echo "1. Test the repository: git log --oneline | head -10"
echo "2. If everything looks good, force push: git push --force-with-lease --all"
echo "3. Force push tags: git push --force-with-lease --tags"
echo ""
echo "⚠️  IMPORTANT:"
echo "   - All contributors will need to re-clone the repository"
echo "   - The backup-before-image-removal branch contains the old history"
echo "   - You can delete it later if everything works correctly"
