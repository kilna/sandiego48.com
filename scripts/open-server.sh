#!/usr/bin/env bash

set -euo pipefail

opened=false
while IFS= read -r line; do
  echo "$line"
  if echo "$line" | grep -q "Web Server is available at" && ! $opened; then
    opened=true
    URL=$(echo "$line" | sed -n 's/.*Web Server is available at \(http[^ ]*\).*/\1/p')
    echo "Opening $URL"
    open "$URL"
  fi
done
