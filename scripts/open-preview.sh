#!/usr/bin/env bash

# Wait for Cloudflare Pages deployment to be ready, then open in browser
# Usage: wrangler pages deploy ... | ./scripts/open-preview.sh

set -euo pipefail

while IFS= read -r line; do
  echo "$line"
  if echo "$line" | grep -q "https://"; then
    URL=$(echo "$line" | grep -o 'https://[^[:space:]]*' | head -1)
    if [ -n "$URL" ]; then
      echo "Preview deployed to: $URL"
      echo -n "Waiting for deployment to be ready."
      while true; do
        if curl -s "$URL" | grep -q "Nothing is here yet"; then
          echo -n "."
          sleep 1
        else
          echo
          echo "Deployment ready! Opening in browser..."
          open "$URL"
          break
        fi
      done
    fi
  fi
done
