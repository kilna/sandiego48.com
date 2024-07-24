#!/usr/bin/env bash

shopt -s globstar

files=()
for file in **/*.md **/*.html; do
  if [[ "$file" != public/* ]]; then
    files=("${files[@]}" "$file")
  fi
done

set -x

for file in "${files[@]}"; do
  git mv "$file" "$file.mv"
done

git commit -m 'Rename files to kick hugo'

for file in "${files[@]}"; do
  git mv "$file.mv" "$file"
done

git commit -m 'Rename files back'

