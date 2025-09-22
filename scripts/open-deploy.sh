#!/usr/bin/env bash

# Get deployment URL and open it after git push
# Usage: ./scripts/open-deploy.sh

set -euo pipefail

# Get the current git commit hash
COMMIT_HASH=$(git rev-parse HEAD)
echo "Looking for deployment with commit: ${COMMIT_HASH:0:7}"

# Get project name from wrangler.toml (first occurrence only) or use default
if [ -f "$(dirname "$0")/../wrangler.toml" ]; then
  PROJECT_NAME=$(grep '^name = ' "$(dirname "$0")/../wrangler.toml" | head -1 | sed 's/name = "\(.*\)"/\1/')
else
  # Default project name based on domain
  PROJECT_NAME="sandiego48-com"
fi
echo "Debug: Using project name: $PROJECT_NAME"

echo -n "Getting deployment URLs."
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  # Look for deployment with matching commit hash
  URL=$(
    wrangler pages deployment list --project-name="$PROJECT_NAME" 2>/dev/null \
      | grep "$COMMIT_HASH" \
      | grep -o 'https://[a-f0-9]\{8\}\.[^[:space:]]*\.pages\.dev' \
      | head -1 \
      || echo ""
  )

  # Also get the build URL
  BUILD_URL=$(
    wrangler pages deployment list --project-name="$PROJECT_NAME" 2>/dev/null \
      | grep "$COMMIT_HASH" \
      | grep -o 'https://dash\.cloudflare\.com/[a-f0-9]\{32\}/pages/view/[^[:space:]]*' \
      | head -1 \
      || echo ""
  )

  # If we can't find the specific commit, try the most recent deployment
  if [ -z "$URL" ] && [ $ELAPSED -gt 10 ]; then
    echo
    echo "Could not find deployment for commit $COMMIT_HASH, trying most recent..."
    URL=$(
      wrangler pages deployment list --project-name="$PROJECT_NAME" 2>/dev/null \
        | grep -o 'https://[a-f0-9]\{8\}\.[^[:space:]]*\.pages\.dev' \
        | head -1 \
        || echo ""
    )
    # Also get the build URL for the most recent deployment
    BUILD_URL=$(
      wrangler pages deployment list --project-name="$PROJECT_NAME" 2>/dev/null \
        | grep -o 'https://dash\.cloudflare\.com/[a-f0-9]\{32\}/pages/view/[^[:space:]]*' \
        | head -1 \
        || echo ""
    )
  fi

  # If we have both URLs, we can proceed
  [ -n "$URL" ] && [ -n "$BUILD_URL" ] && break
  echo -n "."
  sleep 1
  ELAPSED=$((ELAPSED + 1))
done

# Always open the build page first
if [ -n "$BUILD_URL" ]; then
  echo
  echo "Opening build page to monitor deployment..."
  open "$BUILD_URL"
else
  echo "Error: Build URL not found within $TIMEOUT seconds" >&2
  exit 1
fi

# If we still don't have a deployment URL, exit
if [ -z "$URL" ]; then
  echo "Error: Deployment URL not found within $TIMEOUT seconds" >&2
  exit 1
fi

echo
echo -n "Waiting for deployment to complete."
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  # Get the status for our specific deployment
  STATUS=$(
    wrangler pages deployment list --project-name="$PROJECT_NAME" 2>/dev/null \
      | grep "$COMMIT_HASH" \
      | awk -F'│' '{print $6}' \
      | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' \
      | head -1 \
      || echo ""
  )
  
  # Check for success states (timestamps like "just now", "X minutes ago", "X hours ago")
  if echo "$STATUS" | grep -qiE " ago$"; then
    echo
    echo "Deployment completed! Opening site..."
    exec open "$URL"
  fi
  
  # Everything else (Active, Building, Deploying, waiting states, etc.) - keep waiting
  echo -n "."
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

echo
echo "Deployment timed out after $TIMEOUT seconds, but opening site anyway..."
exec open "$URL"
