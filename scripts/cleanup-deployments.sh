#!/usr/bin/env bash

# Clean up Cloudflare Pages deployments
# Usage: ./scripts/cleanup-deployments.sh

set -euo pipefail

PROJECT_NAME="${1:-$CLOUDFLARE_PAGES_PROJECT}"
ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID}"
API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"

if [ -z "$PROJECT_NAME" ] || [ -z "$ACCOUNT_ID" ]; then
  echo "Error: CLOUDFLARE_PAGES_PROJECT and CLOUDFLARE_ACCOUNT_ID must be set"
  echo "Usage: $0 [project-name]"
  exit 1
fi

if [ -z "$API_TOKEN" ]; then
  echo "You need a Cloudflare API token with Pages permissions."
  exit 1
fi

BASE_URL="https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/pages/projects/$PROJECT_NAME/deployments"

ALL_DEPLOYMENTS=""
page=1
per_page=25

while true; do
  response=$(curl -s -X GET "$BASE_URL?page=$page&per_page=$per_page" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json")
  
  # Check if successful
  success=$(echo "$response" | jq -r '.success')
  if [ "$success" != "true" ]; then
    echo "❌ Failed to fetch deployments: $response"
    exit 1
  fi
  
  # Get deployments from this page
  page_deployments=$(echo "$response" | jq -c '.result[]')
  
  if [ -z "$page_deployments" ]; then
    break
  fi
  
  count=$(echo "$page_deployments" | wc -l | tr -d ' ')
  total=$(echo "$ALL_DEPLOYMENTS$page_deployments" | wc -l | tr -d ' ')
  echo "   Fetched page $page: $count deployments (total: $total)"
  
  ALL_DEPLOYMENTS="$ALL_DEPLOYMENTS$page_deployments"$'\n'
  page=$((page + 1))
done

PRODUCTION_DEPLOYMENTS=$(echo "$ALL_DEPLOYMENTS" | grep -v '^$' | jq -s 'map(select(.environment == "production")) | .[10:]')
PREVIEW_DEPLOYMENTS=$(echo "$ALL_DEPLOYMENTS" | grep -v '^$' | jq -s 'map(select(.environment == "preview"))')

PROD_COUNT=$(echo "$PRODUCTION_DEPLOYMENTS" | jq 'length')
PREVIEW_COUNT=$(echo "$PREVIEW_DEPLOYMENTS" | jq 'length')
TOTAL_TO_DELETE=$((PROD_COUNT + PREVIEW_COUNT))

if [ "$TOTAL_TO_DELETE" -eq 0 ]; then
  echo "✅ No deployments to clean up!"
  exit 0
fi

# Auto-confirm with --yes flag, otherwise ask
if [ "${2:-}" = "--yes" ] || [ "${2:-}" = "-y" ]; then
  echo "✅ Auto-confirmed with --yes flag"
else
  read -p "Delete $TOTAL_TO_DELETE deployments? Type 'yes' to confirm: " confirm
  
  if [ "$confirm" != "yes" ]; then
    echo "❌ Cleanup cancelled"
    exit 0
  fi
fi

deleted=0
failed=0
count=0

# Delete old production deployments
if [ "$PROD_COUNT" -gt 0 ]; then
  echo "$PRODUCTION_DEPLOYMENTS" | jq -r '.[] | .id' | while read -r deployment_id; do
    if [ -n "$deployment_id" ]; then
      count=$((count + 1))
      printf "[%d/%d] Deleting old production %s... " "$count" "$TOTAL_TO_DELETE" "${deployment_id:0:8}"
      
      delete_response=$(curl -s -X DELETE "$BASE_URL/$deployment_id" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json")
      
      delete_success=$(echo "$delete_response" | jq -r '.success')
      
      if [ "$delete_success" = "true" ]; then
        echo "✅"
        deleted=$((deleted + 1))
      else
        echo "❌"
        failed=$((failed + 1))
      fi
      
      # Rate limiting
      if [ $((count % 10)) -eq 0 ]; then
        echo "   💤 Brief pause..."
        sleep 1
      fi
    fi
  done
fi

# Delete all preview deployments
if [ "$PREVIEW_COUNT" -gt 0 ]; then
  echo "$PREVIEW_DEPLOYMENTS" | jq -r '.[] | .id' | while read -r deployment_id; do
    if [ -n "$deployment_id" ]; then
      count=$((count + 1))
      printf "[%d/%d] Deleting preview %s... " "$count" "$TOTAL_TO_DELETE" "${deployment_id:0:8}"
      
      delete_response=$(curl -s -X DELETE "$BASE_URL/$deployment_id" \
        -H "Authorization: Bearer $API_TOKEN" \
        -H "Content-Type: application/json")
      
      delete_success=$(echo "$delete_response" | jq -r '.success')
      
      if [ "$delete_success" = "true" ]; then
        echo "✅"
        deleted=$((deleted + 1))
      else
        echo "❌"
        failed=$((failed + 1))
      fi
      
      # Rate limiting
      if [ $((count % 10)) -eq 0 ]; then
        echo "   💤 Brief pause..."
        sleep 1
      fi
    fi
  done
fi
