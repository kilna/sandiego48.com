#!/usr/bin/env bash

cat .tool-plugins | while IFS= read -r spec; do

  # Skip empty lines and comments (lines starting with # or containing only whitespace)
  spec=$(echo "$spec" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')  # trim whitespace
  [[ -z "$spec" || "$spec" =~ ^# ]] && continue
  
  # Remove inline comments (everything after # that's not at the start of line)
  spec=$(echo "$spec" | sed 's/[[:space:]]*#.*$//')
  [[ -z "$spec" ]] && continue
  
  tool=$(echo "$spec" | cut -d' ' -f1)
  
  # Add plugin if it doesn't exist (plugin name is same as tool name)
  if ! asdf plugin list | grep -q "^$tool$"; then
    echo "Adding asdf plugin: $tool"
    asdf plugin add $spec || {
      echo "Warning: Failed to add plugin $tool, continuing..."
      continue
    }
  fi

done
