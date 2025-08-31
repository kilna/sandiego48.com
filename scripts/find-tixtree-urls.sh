#!/bin/bash

# Script to help find actual Tixtree URLs for San Diego 48 Hour Film Project events
# Run this script to test potential URLs and find the correct ones

echo "=== San Diego 48 Hour Film Project - Tixtree URL Finder ==="
echo ""

# Known working URL pattern
KNOWN_URL="https://www.tixtree.com/e/best-of-san-diego-48-hour-film-project-screening-and-awards-gala-f8b4d04c2b71"

echo "✅ Known working URL:"
echo "   $KNOWN_URL"
echo ""

# Test potential URLs for premiere screenings
echo "🔍 Testing potential URLs for premiere screenings..."
echo ""

# Group A
echo "Testing Group A URLs..."
GROUP_A_URLS=(
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-a"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-a-2025"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-group-a"
)

for url in "${GROUP_A_URLS[@]}"; do
  echo "   Testing: $url"
  if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
    echo "   ✅ WORKING: $url"
  else
    echo "   ❌ Not found: $url"
  fi
done
echo ""

# Group B
echo "Testing Group B URLs..."
GROUP_B_URLS=(
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-b"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-b-2025"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-group-b"
)

for url in "${GROUP_B_URLS[@]}"; do
  echo "   Testing: $url"
  if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
    echo "   ✅ WORKING: $url"
  else
    echo "   ❌ Not found: $url"
  fi
done
echo ""

# Group C
echo "Testing Group C URLs..."
GROUP_C_URLS=(
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-c"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-c-2025"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-group-c"
)

for url in "${GROUP_C_URLS[@]}"; do
  echo "   Testing: $url"
  if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
    echo "   ✅ WORKING: $url"
  else
    echo "   ❌ Not found: $url"
  fi
done
echo ""

# Group D
echo "Testing Group D URLs..."
GROUP_D_URLS=(
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-d"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-premiere-screenings-group-d-2025"
  "https://www.tixtree.com/e/san-diego-48-hour-film-project-group-d"
)

for url in "${GROUP_D_URLS[@]}"; do
  echo "   Testing: $url"
  if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200"; then
    echo "   ✅ WORKING: $url"
  else
    echo "   ❌ Not found: $url"
  fi
done
echo ""

echo "=== Instructions ==="
echo "1. Run this script to test potential URLs"
echo "2. For any URLs that return 200 status, manually verify them in a browser"
echo "3. Update the content files with the correct URLs"
echo "4. If no URLs work, you may need to create the events on Tixtree first"
echo ""
echo "Alternative approach:"
echo "1. Go to https://www.tixtree.com/o/san-diego-48-hour-film-project"
echo "2. Look for the individual event listings"
echo "3. Copy the actual URLs from the browser"
echo ""
