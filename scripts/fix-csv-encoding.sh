#!/bin/bash
set -e

CSV_FILE="/Users/kilna/Library/CloudStorage/GoogleDrive-sandiego@48hourfilm.com/My Drive/Events/Open Auditions/2025-contacts/Audition_Sign-In.csv"
BACKUP_FILE="${CSV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

echo "Fixing CSV encoding issues..."

# Create backup
cp "$CSV_FILE" "$BACKUP_FILE"
echo "✓ Created backup: $BACKUP_FILE"

# Fix encoding issues
echo "Fixing character encoding..."

# Replace +AEA- with @ (email addresses)
sed -i '' 's/+AEA-/@/g' "$CSV_FILE"

# Replace +AC0- with - (hyphens in names and phone numbers)
sed -i '' 's/+AC0-/-/g' "$CSV_FILE"

# Replace +IBk- with ' (apostrophes)
sed -i '' "s/+IBk-/'/g" "$CSV_FILE"

# Replace +ACI- with " (quotes)
sed -i '' 's/+ACI-/"/g' "$CSV_FILE"

# Replace +ACM- with nothing (remove from header)
sed -i '' 's/+ACM-//g' "$CSV_FILE"

# Replace +ACIAIg- with " (quotes in monologues)
sed -i '' 's/+ACIAIg-/"/g' "$CSV_FILE"

# Fix extra space in header
sed -i '' 's/Audition ,/Audition,/g' "$CSV_FILE"

echo "✓ Fixed encoding issues:"
echo "  - +AEA- → @ (email addresses)"
echo "  - +AC0- → - (hyphens)"
echo "  - +IBk- → ' (apostrophes)"
echo "  - +ACI- → \" (quotes)"
echo "  - +ACM- → removed (header)"
echo "  - +ACIAIg- → \" (quotes in monologues)"
echo "  - Fixed extra space in header"

# Show a few lines to verify the fix
echo ""
echo "Sample of fixed CSV (first 5 lines):"
head -5 "$CSV_FILE"

echo ""
echo "Done! CSV encoding issues fixed."
echo "Backup saved to: $BACKUP_FILE" 