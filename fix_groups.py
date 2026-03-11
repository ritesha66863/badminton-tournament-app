#!/usr/bin/env python3
"""
Extend tournament data to 6 groups to fix KeyError issues
"""

import json

def extend_to_six_groups():
    """Extend tournament data to include all 6 groups"""
    
    # Load current data
    with open('tournament_data.json', 'r') as f:
        data = json.load(f)

    # Extend to 6 groups if needed
    group_letters = ['A', 'B', 'C', 'D', 'E', 'F']
    group_names_map = {
        'A': 'Warriors', 'B': 'Champions', 'C': 'Legends', 
        'D': 'Heroes', 'E': 'Titans', 'F': 'Gladiators'
    }

    # Update group_names
    for letter in group_letters:
        group_key = f'Group {letter}'
        if group_key not in data['group_names']:
            data['group_names'][group_key] = group_names_map[letter]

    # Update groups
    for letter in group_letters:
        group_key = f'Group {letter}'
        if group_key not in data['groups']:
            data['groups'][group_key] = []

    # Save updated data
    with open('tournament_data.json', 'w') as f:
        json.dump(data, f, indent=2)

    print('✅ Extended tournament data to 6 groups')
    print('Updated groups:', list(data['group_names'].keys()))
    return True

if __name__ == "__main__":
    extend_to_six_groups()