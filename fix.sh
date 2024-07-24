#!/usr/bin/env bash

shopt -s globstar

rm -rf public/*

files=()
for file in content/**/*.md content/**/*.html; do
  files=("${files[@]}" "$file")
done

for file in "${files[@]}"; do
  if [[ " $@ " == *' -x '* ]]; then
    # Remove trailing newlines
    sed -i ':a;/^\n*$/{$d;N;};/\n$/ba' "$file"
  else
    # Add trailing newline
    (echo; echo) >>"$file"
  fi
done

hugo --forceSyncStatic --cleanDestinationDir
