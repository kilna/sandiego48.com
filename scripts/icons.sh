#!/bin/bash

set -euo pipefail

# Check if yq is installed
if ! command -v yq &> /dev/null; then
  echo "Error: yq is not installed. Please install mikefarah/yq first."
  echo "  brew install yq"
  echo "  or visit: https://github.com/mikefarah/yq#install"
  exit 1
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
  echo "Error: curl is not installed."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
YAML_FILE="$SCRIPT_DIR/../icons.yaml"

if [[ ! -f "$YAML_FILE" ]]; then
  echo "Error: icons.yaml not found at $YAML_FILE"
  exit 1
fi

echo "Parsing icons.yaml and downloading SVGs..."

# Parse YAML and iterate through each key-value pair
yq eval '. as $root | keys | .[] | . as $key | {"name": $key, "iconify": $root[$key]}' "$YAML_FILE" | \
while read -r line; do
  if [[ "$line" == "name:"* ]]; then
    icon_name="${line#name: }"
  elif [[ "$line" == "iconify:"* ]]; then
    iconify_id="${line#iconify: }"
    
    # Split iconify ID (e.g., "mdi:twitter" -> collection="mdi", icon="twitter")
    if [[ "$iconify_id" =~ ^([^:]+):(.+)$ ]]; then
      collection="${BASH_REMATCH[1]}"
      icon="${BASH_REMATCH[2]}"
      
      url="https://api.iconify.design/${collection}/${icon}.svg"
      output_file="$SCRIPT_DIR/../assets/icons/${icon_name}.svg"
      
      echo "Downloading $iconify_id as ${icon_name}.svg..."
      
      if curl -s -f "$url" -o "$output_file"; then
        echo "  ✓ Successfully downloaded ${icon_name}.svg"
      else
        echo "  ✗ Failed to download $iconify_id"
        rm -f "$output_file"  # Clean up partial file
      fi
    else
      echo "  ✗ Invalid iconify ID format: $iconify_id (expected format: collection:icon)"
    fi
  fi
done

echo "Done!" 