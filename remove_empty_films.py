#!/usr/bin/env python3
import os
import re

def remove_empty_films_from_file(file_path):
    """Remove lines containing 'films: {}' from a markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove lines that contain exactly '      films: {}' (with proper indentation)
        lines = content.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Check if line matches the pattern (with proper indentation)
            if re.match(r'^\s*films:\s*\{\}\s*$', line):
                print(f"Removing line from {file_path}: {line.strip()}")
                continue
            filtered_lines.append(line)
        
        # Only write if changes were made
        new_content = '\n'.join(filtered_lines)
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Process all film markdown files."""
    films_dir = "content/films"
    updated_files = 0
    
    for root, dirs, files in os.walk(films_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                if remove_empty_films_from_file(file_path):
                    updated_files += 1
    
    print(f"\nProcessed {updated_files} files")

if __name__ == "__main__":
    main()
