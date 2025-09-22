#!/usr/bin/env bash

set -eo pipefail

while IFS= read -r spec; do
  # Skip empty lines and comments (lines starting with # or containing only whitespace)
  spec=$(echo "$spec" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')  # trim whitespace
  [[ -z "$spec" || "$spec" =~ ^# ]] && continue
  
  # Remove inline comments (everything after # that's not at the start of line)
  spec=$(echo "$spec" | sed 's/[[:space:]]*#.*$//')
  [[ -z "$spec" ]] && continue
  
  tool=$(echo "$spec" | cut -d' ' -f1)
  version=$(echo "$spec" | cut -d' ' -f2)
  plugin_url=$(echo "$spec" | cut -d' ' -f3)
  
  # Add plugin if it doesn't exist (plugin name is same as tool name)
  if ! asdf plugin list | grep -q "^$tool$"; then
    echo "Adding asdf plugin: $tool"
    asdf plugin add $tool || {
      echo "Warning: Failed to add plugin $tool, continuing..."
      continue
    }
  fi
  
  # Install version if not already installed (check via asdf list)
  if ! asdf list $tool 2>/dev/null | grep -q "^[[:space:]]*$version[[:space:]]*$"; then
    echo "Installing $tool version $version"
    asdf install $tool $version || {
      echo "Warning: Failed to install $tool $version, continuing..."
      continue
    }
  else
    echo "$tool version $version is already installed"
  fi
  
  # Set the version for the current project and reshim
  echo "Setting $tool version $version for current project"
  asdf local $tool $version || {
    echo "Warning: Failed to set version for $tool, continuing..."
    continue
  }
  echo "Reshimming asdf $tool..."
  asdf reshim $tool
done < .tool-plugins
