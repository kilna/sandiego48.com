#!/usr/bin/env python3
"""
Migration script to rename film directories from old 'dir' field to new 'slug' field
and create Hugo aliases for the old URLs.
"""

import csv
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def load_teams_data(csv_path: str) -> List[Dict]:
    """Load teams data from CSV file."""
    teams = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            teams.append(row)
    return teams

def get_old_dir_names() -> Dict[str, str]:
    """Get old directory names from git history."""
    import subprocess
    
    # Get the previous commit where 'dir' field existed
    try:
        result = subprocess.run(
            ['git', 'show', 'HEAD~1:data/teams.csv'],
            capture_output=True, text=True, check=True
        )
        
        old_data = result.stdout
        old_teams = []
        
        # Parse the old CSV data
        lines = old_data.strip().split('\n')
        if lines:
            reader = csv.DictReader(lines)
            for row in reader:
                if 'dir' in row and row['dir']:
                    old_teams.append(row)
        
        # Create mapping of team_code to old dir
        old_dir_map = {}
        for team in old_teams:
            if 'team_code' in team and 'dir' in team:
                old_dir_map[team['team_code']] = team['dir']
        
        return old_dir_map
        
    except subprocess.CalledProcessError:
        print("Warning: Could not get git history, proceeding without old dir names")
        return {}

def create_hugo_alias(old_path: str, new_path: str, films_dir: str):
    """Create a Hugo alias by modifying the front matter of the new directory's index.md file."""
    # Remove leading slash and films/ prefix for the new path
    new_slug = new_path.replace('/films/', '')
    
    # Find the index.md file in the new directory
    new_dir_path = Path(films_dir) / f"2025-{new_slug}"
    index_file = new_dir_path / "index.md"
    
    if not index_file.exists():
        print(f"Warning: No index.md found in {new_dir_path}")
        return False
    
    # Read the current front matter
    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if aliases already exist
    if 'aliases:' in content:
        # Add to existing aliases
        old_alias = old_path.replace('/films/', '')
        if old_alias not in content:
            # Find the aliases section and add the new alias
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == 'aliases:':
                    # Add the new alias
                    lines.insert(i + 1, f'  - "{old_alias}"')
                    break
            content = '\n'.join(lines)
    else:
        # Create new aliases section
        old_alias = old_path.replace('/films/', '')
        # Find the end of front matter (after ---)
        parts = content.split('---', 2)
        if len(parts) >= 3:
            front_matter = parts[1]
            if front_matter.strip():
                # Add aliases to existing front matter
                front_matter += f'\naliases:\n  - "{old_alias}"'
            else:
                # Create new front matter with aliases
                front_matter = f'aliases:\n  - "{old_alias}"'
            content = f'---{front_matter}---{parts[2]}'
    
    # Write the updated content back
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Added Hugo alias: {old_path} -> {new_path}")
    return True

def migrate_directories(teams: List[Dict], old_dir_map: Dict[str, str], films_dir: str):
    """Migrate directories and create Hugo aliases."""
    films_path = Path(films_dir)
    
    # Track what we've processed
    processed = set()
    aliases_created = 0
    directories_renamed = 0
    
    for team in teams:
        team_code = team.get('team_code', '')
        slug = team.get('slug', '')
        
        if not slug or not team_code:
            continue
        
        # Check if we have an old directory name for this team
        old_dir = old_dir_map.get(team_code)
        
        if old_dir:
            # Create the expected old directory path
            old_dir_path = films_path / f"2025-{old_dir}"
            new_dir_path = films_path / f"2025-{slug}"
            
            # Check if old directory exists and new one doesn't
            if old_dir_path.exists() and not new_dir_path.exists():
                try:
                    # Rename the directory
                    shutil.move(str(old_dir_path), str(new_dir_path))
                    print(f"Renamed: {old_dir_path.name} -> {new_dir_path.name}")
                    directories_renamed += 1
                    
                    # Create Hugo alias for the old URL
                    old_url = f"/films/{old_dir}"
                    new_url = f"/films/{slug}"
                    if create_hugo_alias(old_url, new_url, films_dir):
                        aliases_created += 1
                    
                except Exception as e:
                    print(f"Error renaming {old_dir_path}: {e}")
            elif old_dir_path.exists() and new_dir_path.exists():
                print(f"Warning: Both old and new directories exist for {team_code}")
                print(f"  Old: {old_dir_path}")
                print(f"  New: {new_dir_path}")
                
                # Even if both exist, we should create an alias
                old_url = f"/films/{old_dir}"
                new_url = f"/films/{slug}"
                if create_hugo_alias(old_url, new_url, films_dir):
                    aliases_created += 1
                    
            elif not old_dir_path.exists() and new_dir_path.exists():
                print(f"Directory already renamed: {team_code}")
                
                # Create alias for the old URL
                old_url = f"/films/{old_dir}"
                new_url = f"/films/{slug}"
                if create_hugo_alias(old_url, new_url, films_dir):
                    aliases_created += 1
            else:
                print(f"No directory found for {team_code}")
        
        processed.add(team_code)
    
    print(f"\nMigration Summary:")
    print(f"Directories renamed: {directories_renamed}")
    print(f"Hugo aliases created: {aliases_created}")
    print(f"Teams processed: {len(processed)}")

def main():
    """Main migration function."""
    if len(sys.argv) != 2:
        print("Usage: python migrate-directories.py <films_directory>")
        print("Example: python migrate-directories.py content/films")
        sys.exit(1)
    
    films_dir = sys.argv[1]
    
    if not os.path.exists(films_dir):
        print(f"Error: Directory {films_dir} does not exist")
        sys.exit(1)
    
    print("Starting directory migration...")
    print(f"Films directory: {films_dir}")
    
    # Load current teams data
    teams = load_teams_data('data/teams.csv')
    print(f"Loaded {len(teams)} teams from CSV")
    
    # Get old directory names from git
    old_dir_map = get_old_dir_names()
    print(f"Found {len(old_dir_map)} old directory names from git")
    
    # Perform migration
    migrate_directories(teams, old_dir_map, films_dir)
    
    print("\nMigration completed!")

if __name__ == "__main__":
    main()
