#!/usr/bin/env python3
"""
Fix script to restore all 6 group names
"""
import json
import os

def fix_group_names():
    """Restore missing group names in tournament_data.json"""
    
    print("🔧 Fixing Group Names Setup")
    print("=" * 30)
    
    os.chdir('/Users/ritesha/Downloads/badminton-tournament-app-main')
    
    with open('tournament_data.json', 'r') as f:
        data = json.load(f)
    
    # Check current state
    existing_groups = list(data.get('groups', {}).keys())
    current_group_names = data.get('group_names', {})
    
    print(f"📋 Existing groups in data: {existing_groups}")
    print(f"📋 Current group_names: {current_group_names}")
    
    # Define all 6 groups and their default names
    default_names = ['Warriors', 'Champions', 'Legends', 'Heroes', 'Titans', 'Gladiators']
    all_group_keys = [f'Group {chr(65+i)}' for i in range(6)]
    
    # Restore all 6 group names
    fixed_group_names = {}
    for i, group_key in enumerate(all_group_keys):
        if group_key in current_group_names:
            # Keep existing custom name
            fixed_group_names[group_key] = current_group_names[group_key]
            print(f"✅ Keeping {group_key}: '{current_group_names[group_key]}'")
        else:
            # Add missing with default name
            fixed_group_names[group_key] = default_names[i]
            print(f"🔄 Adding {group_key}: '{default_names[i]}'")
    
    # Update the data
    data['group_names'] = fixed_group_names
    
    # Make sure groups section also has all 6 groups
    current_groups = data.get('groups', {})
    for group_key in all_group_keys:
        if group_key not in current_groups:
            current_groups[group_key] = []
            print(f"🆕 Added empty {group_key} to groups")
    
    data['groups'] = current_groups
    
    # Save back to file
    with open('tournament_data.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✅ SUCCESS: All 6 group names restored!")
    print(f"📋 Final group_names: {fixed_group_names}")
    
    return True

if __name__ == "__main__":
    success = fix_group_names()
    exit(0 if success else 1)