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
    if [[ -n "$plugin_url" ]]; then
      # Try with the URL first
      asdf plugin add $tool $plugin_url || {
        echo "Failed to add plugin $tool from $plugin_url, trying without URL..."
        # Fallback: try without URL (uses default repository)
        asdf plugin add $tool || {
          echo "Warning: Failed to add plugin $tool, trying alternative installation..."
          # For yq specifically, try installing via other means
          if [[ "$tool" == "yq" ]]; then
            echo "Attempting to install yq via alternative method..."
            # Try to install yq directly if asdf fails
            if command -v curl >/dev/null 2>&1; then
              echo "Installing yq via direct download..."
              curl -L "https://github.com/mikefarah/yq/releases/download/v${version}/yq_linux_amd64" -o /tmp/yq
              chmod +x /tmp/yq
              mkdir -p ~/.local/bin
              mv /tmp/yq ~/.local/bin/yq
              export PATH="$HOME/.local/bin:$PATH"
              echo "yq installed to ~/.local/bin/yq"
            else
              echo "Warning: curl not available, cannot install yq"
              continue
            fi
          else
            echo "Warning: Failed to add plugin $tool, continuing..."
            continue
          fi
        }
      }
    else
      asdf plugin add $tool || {
        echo "Warning: Failed to add plugin $tool, continuing..."
        continue
      }
    fi
  fi
  
  # Install version if not already installed (check via asdf list)
  if ! asdf list $tool 2>/dev/null | grep -q "^[[:space:]]*$version[[:space:]]*$"; then
    echo "Installing $tool version $version"
    asdf install $tool $version || {
      echo "Warning: Failed to install $tool $version via asdf"
      # If yq was installed via alternative method, skip asdf installation
      if [[ "$tool" == "yq" && -f "$HOME/.local/bin/yq" ]]; then
        echo "yq already installed via alternative method, skipping asdf installation"
      else
        echo "Warning: Failed to install $tool $version, continuing..."
        continue
      fi
    }
  else
    echo "$tool version $version is already installed"
  fi
  
  # Set the version for the current project and reshim (only if installed via asdf)
  if [[ "$tool" != "yq" || -f "$HOME/.asdf/installs/yq/$version/bin/yq" ]]; then
    echo "Setting $tool version $version for current project"
    asdf local $tool $version || {
      echo "Warning: Failed to set version for $tool, continuing..."
      continue
    }
    echo "Reshimming asdf $tool..."
    asdf reshim $tool
  else
    echo "yq installed via alternative method, skipping asdf local/reshim"
  fi
done < .tool-plugins
