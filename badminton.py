import streamlit as st
import pandas as pd
import json
import random
import io
from collections import defaultdict
import hashlib
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page Configuration
st.set_page_config(page_title="Badminton Tournament Pro", layout="wide")

# User Management System
def hash_password(password):
    """Hash password using SHA-256 with salt"""
    salt = "badminton_tournament_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a stored password against provided password"""
    return stored_password == hash_password(provided_password)

def initialize_users():
    """Initialize default users if not exists"""
    if 'users' not in st.session_state:
        st.session_state.users = {}
    
    # Always ensure the default superuser exists (in case it was deleted)
    if 'ritesha' not in st.session_state.users:
        # Get superuser password from Streamlit secrets or environment variable
        try:
            # Try Streamlit secrets first (for Streamlit Cloud)
            superuser_password = st.secrets.get("SUPERUSER_PASSWORD")
        except (FileNotFoundError, KeyError):
            # Fallback to environment variable (for local development)
            superuser_password = os.getenv('SUPERUSER_PASSWORD')
        
        if not superuser_password:
            st.error("⚠️ SUPERUSER_PASSWORD not configured! Please set it in Streamlit secrets or .env file.")
            st.stop()
            
        st.session_state.users['ritesha'] = {
            'password_hash': hash_password(superuser_password),
            'role': 'superuser',
            'created_by': 'system',
            'created_at': datetime.now().isoformat()
        }

def get_user_role(username):
    """Get user role, return None if user doesn't exist"""
    if username in st.session_state.users:
        return st.session_state.users[username]['role']
    return None

def is_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def get_current_user():
    """Get current logged in user"""
    return st.session_state.get('current_user', None)

def get_current_user_role():
    """Get current user's role"""
    user = get_current_user()
    return get_user_role(user) if user else None

def can_access_page(page_name):
    """Check if current user can access a specific page"""
    # Public pages - accessible to everyone
    public_pages = ['Team Details', 'Standings & Qualifiers']
    
    if page_name in public_pages:
        return True
    
    # Protected pages require authentication
    if not is_authenticated():
        return False
    
    user_role = get_current_user_role()
    
    # Superuser can access everything
    if user_role == 'superuser':
        return True
    
    # Admin can access clash recording
    if user_role == 'admin' and page_name == 'Record a Clash':
        return True
    
    # Other protected pages require superuser
    return False

def logout():
    """Logout current user"""
    st.session_state.authenticated = False
    st.session_state.current_user = None
    st.rerun()

def login_page():
    """Display login page"""
    st.title('🏸 Tournament Management - Login')
    
    with st.form('login_form'):
        st.markdown('### 🔐 Please Login to Continue')
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        login_button = st.form_submit_button('Login')
        
        if login_button:
            if username in st.session_state.users:
                if verify_password(st.session_state.users[username]['password_hash'], password):
                    st.session_state.authenticated = True
                    st.session_state.current_user = username
                    st.success(f'Welcome back, {username}!')
                    st.rerun()
                else:
                    st.error('Invalid password')
            else:
                st.error('User not found')
    
    st.markdown('---')
    st.info('👁️ **Public Access Available:** You can view Team Details and Standings & Qualifiers without logging in.')
    
    # Public access button
    if st.button('🌐 Continue as Guest (Limited Access)'):
        st.session_state.public_access = True
        st.rerun()

# Data persistence functions
def save_tournament_data():
    """Save tournament data to JSON files"""
    try:
        # Save player database
        if 'player_database' in st.session_state:
            st.session_state.player_database.to_json('tournament_players.json', orient='records')
        
        # Ensure standings is a proper dataframe before saving
        standings_to_save = {}
        if 'standings' in st.session_state and not st.session_state.standings.empty:
            try:
                standings_to_save = st.session_state.standings.to_dict('index')
            except Exception as e:
                st.warning(f"Warning: Could not save standings properly: {str(e)}")
        
        # Save other data including users (excluding matches - they have their own file now)
        tournament_data = {
            'group_names': st.session_state.get('group_names', {}),
            'subgroup_names': st.session_state.get('subgroup_names', {}),
            'groups': st.session_state.get('groups', {}),
            'detailed_groups': st.session_state.get('detailed_groups', {}),
            'standings': standings_to_save,
            'tournament_data': st.session_state.get('tournament_data', {}),  # Keep for backward compatibility
            'users': st.session_state.get('users', {}),
            'clash_edit_history': st.session_state.get('clash_edit_history', [])
        }
        
        with open('tournament_data.json', 'w') as f:
            json.dump(tournament_data, f, indent=2)
            
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

def load_tournament_data():
    """Load tournament data from JSON files"""
    try:
        # Load player database
        try:
            st.session_state.player_database = pd.read_json('tournament_players.json', orient='records')
        except:
            # Initialize with sample data if file doesn't exist
            st.session_state.player_database = pd.DataFrame({
                'name': [f'Player {i+1}' for i in range(60)],
                'gender': ['M' if i % 3 != 0 else 'F' for i in range(60)],
                'email': [f'player{i+1}@example.com' for i in range(60)],
                'skill_level': [random.randint(1, 10) for _ in range(60)],
                'group': [f"Group {chr(65+(i//10))}" for i in range(60)],
                'assigned': [True] * 60
            })
        
        # Load other data
        try:
            with open('tournament_data.json', 'r') as f:
                tournament_data = json.load(f)
                
                # Default group setup for consistency
                default_groups = [f"Group {chr(65+i)}" for i in range(6)]
                default_names = ["Warriors", "Champions", "Legends", "Heroes", "Titans", "Gladiators"]
                
                st.session_state.group_names = tournament_data.get('group_names', {group: name for group, name in zip(default_groups, default_names)})
                st.session_state.subgroup_names = tournament_data.get('subgroup_names', {'subgroup1': '1 (Lower)', 'subgroup2': '2 (Higher)'})
                st.session_state.groups = tournament_data.get('groups', {group: [] for group in default_groups})
                st.session_state.detailed_groups = tournament_data.get('detailed_groups', {})
                st.session_state.tournament_data = tournament_data.get('tournament_data', {})
                # Load individual matches from separate file
                load_matches()
                st.session_state.clash_edit_history = tournament_data.get('clash_edit_history', [])
                
                # Load users first before other initialization
                saved_users = tournament_data.get('users', {})
                if saved_users:
                    st.session_state.users = saved_users
                else:
                    st.session_state.users = {}
                
                # Restore standings
                standings_data = tournament_data.get('standings', {})
                if standings_data:
                    try:
                        # Try to load from indexed format first (new format)
                        st.session_state.standings = pd.DataFrame.from_dict(standings_data, orient='index')
                    except:
                        # Fallback to old format if needed
                        st.session_state.standings = pd.DataFrame.from_dict(standings_data)
                        if 'Group' in st.session_state.standings.columns:
                            st.session_state.standings = st.session_state.standings.set_index('Group')
                else:
                    # Calculate fresh standings from tournament data if available
                    if st.session_state.tournament_data or st.session_state.get('individual_matches', []):
                        # Try new individual matches first
                        if st.session_state.get('individual_matches', []):
                            calculated_standings = calculate_standings_from_matches()
                        else:
                            # Fallback to old clash-based calculation for backward compatibility
                            calculated_standings = calculate_standings()
                        
                        if not calculated_standings.empty:
                            st.session_state.standings = calculated_standings.set_index('Team')
                        else:
                            # Initialize default standings
                            st.session_state.standings = pd.DataFrame({
                                "Group": [f"Group {chr(65+i)}" for i in range(6)],
                                "Clash Wins": [0]*6,
                                "Total Points": [0]*6
                            }).set_index("Group")
                    else:
                        # Initialize default standings
                        st.session_state.standings = pd.DataFrame({
                            "Group": [f"Group {chr(65+i)}" for i in range(6)],
                            "Clash Wins": [0]*6,
                            "Total Points": [0]*6
                        }).set_index("Group")
                
                # Always recalculate standings from available data to ensure accuracy
                if st.session_state.get('individual_matches', []):
                    calculated_standings = calculate_standings_from_matches()
                    if not calculated_standings.empty:
                        st.session_state.standings = calculated_standings.set_index('Team')
                elif st.session_state.tournament_data:
                    calculated_standings = calculate_standings()
                    if not calculated_standings.empty:
                        st.session_state.standings = calculated_standings.set_index('Team')
        except:
            # Initialize defaults if file doesn't exist
            default_groups = [f"Group {chr(65+i)}" for i in range(6)]
            default_names = ["Warriors", "Champions", "Legends", "Heroes", "Titans", "Gladiators"]
            
            st.session_state.group_names = {group: name for group, name in zip(default_groups, default_names)}
            st.session_state.subgroup_names = {'subgroup1': '1 (Lower)', 'subgroup2': '2 (Higher)'}
            st.session_state.groups = {group: [] for group in default_groups}
            st.session_state.users = {}  # Initialize empty users dict
            st.session_state.clash_edit_history = []  # Initialize empty history
            st.session_state.tournament_data = {}  # Initialize empty tournament data (backward compatibility)
            # Initialize individual matches from file or create empty
            load_matches()
            st.session_state.detailed_groups = {}  # Initialize empty detailed groups
            st.session_state.standings = pd.DataFrame({
                "Team": default_groups,
                "Clash Wins": [0]*6,
                "Total Points": [0]*6
            }).set_index("Team")
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")

# Auto-save functionality
def save_matches():
    """Save individual matches to separate JSON file"""
    try:
        matches = st.session_state.get('individual_matches', [])
        with open('matches.json', 'w') as f:
            json.dump(matches, f, indent=2)
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def load_matches():
    """Load individual matches from JSON file"""
    try:
        with open('matches.json', 'r') as f:
            matches = json.load(f)
            st.session_state.individual_matches = matches
    except FileNotFoundError:
        st.session_state.individual_matches = []
    except Exception as e:
        st.error(f"Error loading matches: {str(e)}")
        st.session_state.individual_matches = []

def add_match(match_record):
    """Add a new match and save to file"""
    if 'individual_matches' not in st.session_state:
        load_matches()
    st.session_state.individual_matches.append(match_record)
    save_matches()

def update_match(match_index, updated_data):
    """Update an existing match and save to file"""
    if 'individual_matches' not in st.session_state:
        load_matches()
    if 0 <= match_index < len(st.session_state.individual_matches):
        st.session_state.individual_matches[match_index].update(updated_data)
        save_matches()
        return True
    return False

def delete_match(match_index):
    """Delete a match and save to file"""
    if 'individual_matches' not in st.session_state:
        load_matches()
    if 0 <= match_index < len(st.session_state.individual_matches):
        st.session_state.individual_matches.pop(match_index)
        save_matches()
        return True
    return False

def get_all_matches():
    """Get all matches, loading from file if necessary"""
    if 'individual_matches' not in st.session_state:
        load_matches()
    return st.session_state.individual_matches

def clear_all_matches():
    """Clear all matches and save to file"""
    st.session_state.individual_matches = []
    save_matches()

def auto_save():
    """Save individual matches to separate JSON file"""
    try:
        matches = st.session_state.get('individual_matches', [])
        with open('matches.json', 'w') as f:
            json.dump(matches, f, indent=2)
    except Exception as e:
        st.error(f"Error saving matches: {str(e)}")

def load_matches():
    """Load individual matches from JSON file"""
    try:
        with open('matches.json', 'r') as f:
            matches = json.load(f)
            st.session_state.individual_matches = matches
    except FileNotFoundError:
        st.session_state.individual_matches = []
    except Exception as e:
        st.error(f"Error loading matches: {str(e)}")
        st.session_state.individual_matches = []

def auto_save():
    """Auto-save tournament data and matches"""
    save_tournament_data()
    save_matches()

def generate_round_robin_schedule(groups, dates, start_time, end_time, num_courts, match_duration, break_duration):
    """
    Generate proper round-robin schedule where all groups play simultaneously in each round
    """
    from datetime import datetime, timedelta
    
    # Ensure we have at least 2 groups
    if len(groups) < 2:
        return []
    
    # Generate proper round-robin pairings
    def generate_round_robin_pairings(teams):
        """Generate round-robin pairings where each team plays every other team exactly once"""
        n = len(teams)
        if n % 2 == 1:
            teams = teams + ['BYE']  # Add dummy team for odd numbers
            n += 1
        
        rounds = []
        
        # Generate n-1 rounds for n teams
        for round_num in range(n - 1):
            round_pairings = []
            
            # Generate pairings for this round
            for i in range(n // 2):
                team1_idx = i
                team2_idx = n - 1 - i
                
                team1 = teams[team1_idx]
                team2 = teams[team2_idx]
                
                # Skip if either team is BYE
                if team1 != 'BYE' and team2 != 'BYE':
                    round_pairings.append((team1, team2))
            
            rounds.append(round_pairings)
            
            # Rotate teams for next round (keep first fixed, rotate rest)
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]
        
        return rounds
    
    # Generate round-robin rounds
    tournament_rounds = generate_round_robin_pairings(groups.copy())
    
    # Calculate timing
    start_dt = datetime.strptime(start_time.strftime('%H:%M'), '%H:%M')
    end_dt = datetime.strptime(end_time.strftime('%H:%M'), '%H:%M')
    daily_minutes = int((end_dt - start_dt).total_seconds() / 60)
    
    slot_duration = match_duration + break_duration
    
    schedule = []
    current_date_idx = 0
    current_time_slot = 0
    
    for round_idx, round_pairings in enumerate(tournament_rounds):
        # Calculate start time for this round
        round_start_minutes = current_time_slot * slot_duration
        round_start_dt = start_dt + timedelta(minutes=round_start_minutes)
        
        # Check if we need to move to next day
        if round_start_minutes + slot_duration > daily_minutes:
            current_date_idx = (current_date_idx + 1) % len(dates)
            current_time_slot = 0
            round_start_minutes = 0
            round_start_dt = start_dt
        
        # Schedule all matches in this round
        court_assignments = {}  # Track which courts are used at which times
        
        for clash_idx, (group1, group2) in enumerate(round_pairings):
            # Schedule 5 matches for this clash
            for match_num in range(1, 6):
                # Find available court for this time slot
                time_slot_key = f"{current_date_idx}_{current_time_slot}"
                
                if time_slot_key not in court_assignments:
                    court_assignments[time_slot_key] = []
                
                # Find next available court
                court_num = len(court_assignments[time_slot_key]) + 1
                
                if court_num <= num_courts:
                    # Court is available at this time
                    match_start_time = round_start_dt
                    match_end_time = match_start_time + timedelta(minutes=match_duration)
                    
                    court_assignments[time_slot_key].append(court_num)
                else:
                    # Need to use next time slot
                    current_time_slot += 1
                    
                    # Check if day overflows
                    if (current_time_slot * slot_duration) + slot_duration > daily_minutes:
                        current_date_idx = (current_date_idx + 1) % len(dates)
                        current_time_slot = 0
                    
                    match_start_time = start_dt + timedelta(minutes=current_time_slot * slot_duration)
                    match_end_time = match_start_time + timedelta(minutes=match_duration)
                    
                    court_num = 1
                    new_time_slot_key = f"{current_date_idx}_{current_time_slot}"
                    court_assignments[new_time_slot_key] = [1]
                
                # Add match to schedule
                schedule.append({
                    'date': dates[current_date_idx].strftime('%Y-%m-%d'),
                    'round_number': round_idx + 1,
                    'clash_number': clash_idx + 1,
                    'match_number': match_num,
                    'court': f'Court {court_num}',
                    'start_time': match_start_time.strftime('%H:%M'),
                    'end_time': match_end_time.strftime('%H:%M'),
                    'group1': group1,
                    'group2': group2,
                    'status': 'Scheduled'
                })
        
        # Move to next time slot for next round
        current_time_slot += 1
    
    return schedule

# Initialize State for Data Persistence
if 'initialized' not in st.session_state:
    # Load existing data first (including users)
    load_tournament_data()
    
    # Ensure subgroup names are always initialized
    if 'subgroup_names' not in st.session_state:
        st.session_state.subgroup_names = {
            'subgroup1': '1 (Lower)',
            'subgroup2': '2 (Higher)'
        }
    
    # Then initialize user system (will only add missing default users)
    initialize_users()
    
    # Ensure groups are populated from player database if they exist
    if not any(st.session_state.groups.values()) and not st.session_state.player_database.empty:
        assigned_players = st.session_state.player_database[st.session_state.player_database['assigned'] == True]
        for _, player in assigned_players.iterrows():
            if player['group'] in st.session_state.groups:
                if player['name'] not in st.session_state.groups[player['group']]:
                    st.session_state.groups[player['group']].append(player['name'])
    
    # Initialize individual matches if not exists
    if 'individual_matches' not in st.session_state:
        load_matches()  # Load matches from file
    
    # Initialize edit history if not exists
    if 'clash_edit_history' not in st.session_state:
        st.session_state.clash_edit_history = []
    
    st.session_state.initialized = True

st.title("🏸 Badminton Group Tournament Manager")

# Check authentication and show login if needed
if not is_authenticated() and not st.session_state.get('public_access', False):
    login_page()
    st.stop()

# Build navigation menu based on user permissions
available_pages = []
all_pages = ["Player Import & Auto-Balance", "Setup Groups & Players", "Team Details", 
            "Match Schedule", "Standings & Qualifiers", "Record a Clash", "Manage Players", "User Management"]

for page in all_pages:
    if can_access_page(page):
        available_pages.append(page)

# Show user info in sidebar
st.sidebar.header("Tournament Controls")
if is_authenticated():
    current_user = get_current_user()
    user_role = get_current_user_role()
    st.sidebar.success(f'👤 Logged in as: **{current_user}** ({user_role})')
    if st.sidebar.button('🚪 Logout'):
        logout()
else:
    st.sidebar.info('👁️ **Guest Access** - Limited features available')
    if st.sidebar.button('🔐 Login'):
        st.session_state.public_access = False
        st.rerun()

st.sidebar.divider()

# Save/Load functionality in sidebar
st.sidebar.subheader("💾 Data Management")
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("💾 Save Data", help="Save all tournament data"):
        save_tournament_data()
        st.sidebar.success("Data saved!")
with col2:
    if st.button("📂 Load Data", help="Load saved tournament data"):
        load_tournament_data()
        st.sidebar.success("Data loaded!")
        st.rerun()

# Export functionality
if st.sidebar.button("📤 Export Player Data", help="Download player database as CSV"):
    csv_data = st.session_state.player_database.to_csv(index=False)
    st.sidebar.download_button(
        label="⬇️ Download CSV",
        data=csv_data,
        file_name=f"tournament_players_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

st.sidebar.divider()

menu = st.sidebar.radio("Navigate", available_pages)

# Auto-balancing algorithm
def auto_balance_groups(players_df, min_females_per_group=None, max_females_per_group=None, force_rebalance=False):
    """
    Auto-balance players into 6 groups with optimized skill and gender distribution
    Uses iterative optimization to minimize skill variance between groups
    
    Args:
        players_df: DataFrame containing player data
        min_females_per_group: Minimum number of females per group (optional)
        max_females_per_group: Maximum number of females per group (optional)
        force_rebalance: If True, introduces randomization for different team compositions
    """
    import itertools
    import random
    
    # If force_rebalance is True, shuffle the player order to get different results
    if force_rebalance:
        players_df = players_df.sample(frac=1).reset_index(drop=True)
        # Add some randomness to ensure different team compositions
        random.seed(None)  # Use current time as seed
    
    # Separate male and female players
    male_players = players_df[players_df['gender'] == 'M'].copy()
    female_players = players_df[players_df['gender'] == 'F'].copy()
    
    # Sort by skill level (descending)
    male_players = male_players.sort_values('skill_level', ascending=False).reset_index(drop=True)
    female_players = female_players.sort_values('skill_level', ascending=False).reset_index(drop=True)
    
    # Initialize groups using configured custom names
    group_keys = [f"Group {chr(65+i)}" for i in range(6)]  # Default keys
    if 'group_names' in st.session_state:
        # Use the display names from configuration
        groups = {key: {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0} for key in group_keys}
    else:
        groups = {f"Group {chr(65+i)}": {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0} for i in range(6)}
        group_keys = list(groups.keys())
    
    # Step 1: Distribute females using user-defined constraints or default even distribution
    total_females = len(female_players)
    
    if min_females_per_group is not None and max_females_per_group is not None:
        # Validate constraints
        if min_females_per_group * 6 > total_females:
            raise ValueError(f"Not enough female players: need at least {min_females_per_group * 6}, have {total_females}")
        if max_females_per_group * 6 < total_females:
            raise ValueError(f"Too many female players for constraints: max capacity {max_females_per_group * 6}, have {total_females}")
        
        # Create optimized distribution within constraints
        female_distribution = [min_females_per_group] * 6
        remaining_females = total_females - (min_females_per_group * 6)
        
        # Distribute remaining females respecting max constraints
        for i in range(6):
            if remaining_females > 0 and female_distribution[i] < max_females_per_group:
                add_count = min(remaining_females, max_females_per_group - female_distribution[i])
                female_distribution[i] += add_count
                remaining_females -= add_count
    else:
        # Default: distribute females evenly
        female_count_per_group = total_females // 6
        female_remainder = total_females % 6
        
        female_distribution = []
        for i in range(6):
            group_females = female_count_per_group + (1 if i < female_remainder else 0)
            female_distribution.append(group_females)
    
    # Assign females using skill balancing
    female_idx = 0
    for round_num in range(max(female_distribution)):
        # Alternate direction each round for better balance
        group_order = list(range(6)) if round_num % 2 == 0 else list(range(5, -1, -1))
        
        for group_idx in group_order:
            if female_distribution[group_idx] > 0 and female_idx < len(female_players):
                player = female_players.iloc[female_idx]
                groups[group_keys[group_idx]]['players'].append(player)
                groups[group_keys[group_idx]]['total_skill'] += player['skill_level']
                groups[group_keys[group_idx]]['female_count'] += 1
                female_distribution[group_idx] -= 1
                female_idx += 1
    
    # Step 2: Distribute males using skill-based optimization
    remaining_spots = [10 - len(groups[key]['players']) for key in group_keys]
    
    # Use iterative assignment for better balance
    male_idx = 0
    while male_idx < len(male_players):
        # Find the group with lowest total skill that has remaining spots
        available_groups = [(i, groups[group_keys[i]]['total_skill']) for i in range(6) if remaining_spots[i] > 0]
        
        if not available_groups:
            break
            
        # Sort by total skill (ascending) to assign to weakest group
        available_groups.sort(key=lambda x: x[1])
        target_group_idx = available_groups[0][0]
        
        player = male_players.iloc[male_idx]
        groups[group_keys[target_group_idx]]['players'].append(player)
        groups[group_keys[target_group_idx]]['total_skill'] += player['skill_level']
        groups[group_keys[target_group_idx]]['male_count'] += 1
        remaining_spots[target_group_idx] -= 1
        male_idx += 1
    
    # Step 3: Simple redistribution for guaranteed 1-point difference
    def redistribute_for_perfect_balance():
        """Simple algorithm to achieve exactly 1-point max difference"""
        # Use the tested working algorithm
        max_iterations = 100
        
        # If force_rebalance is True, do more swaps to ensure redistribution
        if force_rebalance:
            max_iterations = 200  # More iterations for more mixing
            
            # Perform some random swaps first to shuffle teams
            for _ in range(10):  # Do random swaps of same-gender players
                group1_idx = random.randint(0, len(group_keys)-1)
                group2_idx = random.randint(0, len(group_keys)-1)
                
                if group1_idx == group2_idx:
                    continue
                    
                group1 = groups[group_keys[group1_idx]]
                group2 = groups[group_keys[group2_idx]]
                
                if not group1['players'] or not group2['players']:
                    continue
                    
                # Find players of same gender to swap
                for p1_idx, p1 in enumerate(group1['players']):
                    for p2_idx, p2 in enumerate(group2['players']):
                        if p1['gender'] == p2['gender']:  # Same gender
                            # Perform the swap
                            group1['players'][p1_idx] = p2
                            group2['players'][p2_idx] = p1
                            # Update totals
                            skill_diff = p1['skill_level'] - p2['skill_level']
                            group1['total_skill'] -= skill_diff
                            group2['total_skill'] += skill_diff
                            break
                    else:
                        continue
                    break
        
        for iteration in range(max_iterations):  # Use variable iterations
            # Get current group totals
            totals = [groups[key]['total_skill'] for key in group_keys]
            max_total = max(totals)
            min_total = min(totals)
            
            # If balanced within 1 point, we're done (unless force_rebalance is True)
            if max_total - min_total <= 1 and not force_rebalance:
                break
            
            # For force_rebalance, do at least 15 iterations to ensure redistribution
            if force_rebalance and iteration < 15:
                pass  # Continue balancing even if already balanced
            elif max_total - min_total <= 1:
                break
            
            # Find highest and lowest groups
            max_idx = totals.index(max_total)
            min_idx = totals.index(min_total)
            
            max_group = groups[group_keys[max_idx]]
            min_group = groups[group_keys[min_idx]]
            
            # Find best player swap
            best_swap = None
            best_improvement = 0
            
            for i, max_player in enumerate(max_group['players']):
                for j, min_player in enumerate(min_group['players']):
                    # Only swap same gender
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    # Calculate skill difference
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    
                    # Only swap if it reduces the gap
                    if skill_diff <= 0:
                        continue
                    
                    # Calculate new totals after swap
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    # If this improves balance, consider it
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = (i, j, max_player, min_player, skill_diff)
            
            # Make the best swap
            if best_swap:
                i, j, max_player, min_player, skill_diff = best_swap
                # Swap players
                max_group['players'][i] = min_player
                min_group['players'][j] = max_player
                # Update totals
                max_group['total_skill'] -= skill_diff
                min_group['total_skill'] += skill_diff
            else:
                break  # No beneficial swap found
    
    # Execute the redistribution
    redistribute_for_perfect_balance()
    
    # Convert to the expected format
    result_groups = {}
    for group_name, group_data in groups.items():
        result_groups[group_name] = group_data['players']
    
    return result_groups


def auto_balance_subgroups(players_df, subgroup1_min, subgroup1_max, subgroup2_min, subgroup2_max, subgroup1_count, subgroup2_count, num_groups=6, min_females_per_group=None, max_females_per_group=None, force_rebalance=False):
    """
    Auto-balance players into specified number of groups with 2 skill-based subgroups each
    Ensures skill point balance at group level, subgroup 1 level, and subgroup 2 level
    
    Args:
        min_females_per_group: Minimum number of females per group (optional)
        max_females_per_group: Maximum number of females per group (optional)
        force_rebalance: If True, introduces randomization for different team compositions
    """
    import itertools
    import random
    
    # If force_rebalance is True, shuffle the player order to get different results
    if force_rebalance:
        players_df = players_df.sample(frac=1).reset_index(drop=True)
        # Add some randomness to ensure different team compositions
        random.seed(None)  # Use current time as seed
    
    # Filter players based on skill level ranges
    subgroup1_players = players_df[
        (players_df['skill_level'] >= subgroup1_min) & 
        (players_df['skill_level'] <= subgroup1_max)
    ].copy()
    
    subgroup2_players = players_df[
        (players_df['skill_level'] >= subgroup2_min) & 
        (players_df['skill_level'] <= subgroup2_max)
    ].copy()
    
    # Check if we have enough players
    needed_sg1 = subgroup1_count * num_groups
    needed_sg2 = subgroup2_count * num_groups
    
    if len(subgroup1_players) < needed_sg1:
        raise ValueError(f"Not enough players for Subgroup 1. Need {needed_sg1}, have {len(subgroup1_players)}")
    if len(subgroup2_players) < needed_sg2:
        raise ValueError(f"Not enough players for Subgroup 2. Need {needed_sg2}, have {len(subgroup2_players)}")
    
    # Validate gender constraints if specified
    if min_females_per_group is not None and max_females_per_group is not None:
        total_females_sg1 = len(subgroup1_players[subgroup1_players['gender'] == 'F'])
        total_females_sg2 = len(subgroup2_players[subgroup2_players['gender'] == 'F'])
        total_females = total_females_sg1 + total_females_sg2
        
        if min_females_per_group * num_groups > total_females:
            raise ValueError(f"Not enough female players: need at least {min_females_per_group * num_groups}, have {total_females}")
        if max_females_per_group * num_groups < total_females:
            raise ValueError(f"Too many female players for constraints: max capacity {max_females_per_group * num_groups}, have {total_females}")
    
    # Select players for each subgroup (take all available if we have more than needed)
    if len(subgroup1_players) > needed_sg1:
        subgroup1_selected = subgroup1_players.nlargest(needed_sg1, 'skill_level').reset_index(drop=True)
    else:
        subgroup1_selected = subgroup1_players.reset_index(drop=True)
        
    if len(subgroup2_players) > needed_sg2:
        subgroup2_selected = subgroup2_players.nlargest(needed_sg2, 'skill_level').reset_index(drop=True)
    else:
        subgroup2_selected = subgroup2_players.reset_index(drop=True)
    
    # Initialize groups dynamically using default keys
    groups = {}
    for i in range(num_groups):
        group_name = f"Group {chr(65+i)}"  # Use default keys internally
        groups[group_name] = {
            'subgroup1': {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0},
            'subgroup2': {'players': [], 'total_skill': 0, 'male_count': 0, 'female_count': 0}
        }
    
    group_keys = list(groups.keys())
    
    def balance_players_by_skill(players_list, subgroup_type, target_count_per_group, force_rebalance=False):
        """Balance players across all groups to minimize skill variance while respecting gender constraints"""
        if len(players_list) == 0:
            return
        
        # Separate by gender first if constraints are specified
        if min_females_per_group is not None and max_females_per_group is not None:
            male_players = players_list[players_list['gender'] == 'M'].sort_values('skill_level', ascending=False).reset_index(drop=True)
            female_players = players_list[players_list['gender'] == 'F'].sort_values('skill_level', ascending=False).reset_index(drop=True)
            
            # Distribute females first to meet constraints
            distribute_with_gender_constraints(female_players, male_players, subgroup_type, target_count_per_group)
        else:
            # Original skill-only distribution
            distribute_by_skill_only(players_list, subgroup_type, target_count_per_group)
    
    def distribute_with_gender_constraints(female_players, male_players, subgroup_type, target_count_per_group):
        """Distribute players respecting gender constraints"""
        total_females = len(female_players)
        
        # Calculate female distribution within constraints
        female_distribution = [min_females_per_group] * num_groups
        remaining_females = total_females - (min_females_per_group * num_groups)
        
        # Distribute remaining females respecting max constraints
        for i in range(num_groups):
            if remaining_females > 0 and female_distribution[i] < max_females_per_group:
                add_count = min(remaining_females, max_females_per_group - female_distribution[i])
                female_distribution[i] += add_count
                remaining_females -= add_count
        
        # Assign females using skill balancing within constraints
        female_idx = 0
        female_records = female_players.to_dict('records')
        
        for round_num in range(max(female_distribution) if female_distribution else 0):
            group_order = list(range(num_groups)) if round_num % 2 == 0 else list(range(num_groups-1, -1, -1))
            
            for group_idx in group_order:
                if female_distribution[group_idx] > 0 and female_idx < len(female_records):
                    player = female_records[female_idx]
                    group_name = group_keys[group_idx]
                    groups[group_name][subgroup_type]['players'].append(player)
                    groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
                    groups[group_name][subgroup_type]['female_count'] += 1
                    female_distribution[group_idx] -= 1
                    female_idx += 1
        
        # Assign males to fill remaining spots
        male_records = male_players.to_dict('records')
        male_idx = 0
        
        while male_idx < len(male_records):
            # Find group with fewest players and lowest skill total
            available_groups = []
            for i in range(num_groups):
                current_count = len(groups[group_keys[i]][subgroup_type]['players'])
                if current_count < target_count_per_group:
                    skill_total = groups[group_keys[i]][subgroup_type]['total_skill']
                    available_groups.append((skill_total, current_count, i))
            
            if not available_groups:
                break
            
            # Sort by skill total (ascending) then by count (ascending)
            available_groups.sort(key=lambda x: (x[0], x[1]))
            target_group_idx = available_groups[0][2]
            
            player = male_records[male_idx]
            group_name = group_keys[target_group_idx]
            groups[group_name][subgroup_type]['players'].append(player)
            groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
            groups[group_name][subgroup_type]['male_count'] += 1
            male_idx += 1
    
    def distribute_by_skill_only(players_list, subgroup_type, target_count_per_group):
        """Original skill-only distribution method"""
    def distribute_by_skill_only(players_list, subgroup_type, target_count_per_group):
        """Original skill-only distribution method"""
        # Sort players by skill level (descending)
        sorted_players = players_list.sort_values('skill_level', ascending=False).reset_index(drop=True)
        
        # Convert to list of dictionaries for easier manipulation
        player_records = sorted_players.to_dict('records')
        
        # Initialize group assignments
        group_assignments = [[] for _ in range(num_groups)]
        
        # Distribute players using a skill-balancing algorithm
        for i, player in enumerate(player_records):
            # Find the group with the lowest current total skill for this subgroup
            group_skills = []
            for j in range(num_groups):
                current_skill = sum(p['skill_level'] for p in group_assignments[j])
                current_count = len(group_assignments[j])
                # Only consider groups that haven't reached their target count
                if current_count < target_count_per_group:
                    group_skills.append((current_skill, j))
            
            if group_skills:
                # Sort by current skill total (ascending) and assign to the group with lowest skill
                group_skills.sort(key=lambda x: x[0])
                target_group_idx = group_skills[0][1]
                group_assignments[target_group_idx].append(player)
        
        # Assign players to groups
        for group_idx, assigned_players in enumerate(group_assignments):
            group_name = group_keys[group_idx]
            for player in assigned_players:
                groups[group_name][subgroup_type]['players'].append(player)
                groups[group_name][subgroup_type]['total_skill'] += player['skill_level']
                if player['gender'] == 'M':
                    groups[group_name][subgroup_type]['male_count'] += 1
                else:
                    groups[group_name][subgroup_type]['female_count'] += 1
        
        # Optimize by swapping players to reduce variance
        optimize_skill_balance(subgroup_type, target_count_per_group, force_rebalance)
    
    def optimize_skill_balance(subgroup_type, target_count_per_group, force_rebalance=False):
        """Simple redistribution for subgroups using the proven algorithm"""
        
        max_iterations = 100
        
        # If force_rebalance is True, do more mixing with proper skill validation
        if force_rebalance:
            max_iterations = 200  # More iterations for better mixing
            
            # Determine skill range for this subgroup to validate swaps
            if subgroup_type == 'subgroup1':
                valid_min_skill, valid_max_skill = subgroup1_min, subgroup1_max
            else:  # subgroup2
                valid_min_skill, valid_max_skill = subgroup2_min, subgroup2_max
            
            # Perform some random swaps first within this subgroup to shuffle teams
            for _ in range(8):  # Reduced random swaps of same-gender players
                group1_idx = random.randint(0, len(group_keys)-1)
                group2_idx = random.randint(0, len(group_keys)-1)
                
                if group1_idx == group2_idx:
                    continue
                    
                group1 = groups[group_keys[group1_idx]][subgroup_type]
                group2 = groups[group_keys[group2_idx]][subgroup_type]
                
                if not group1['players'] or not group2['players']:
                    continue
                    
                # Find players of same gender AND valid skill range to swap
                swap_made = False
                for p1_idx, p1 in enumerate(group1['players']):
                    if swap_made:
                        break
                    
                    # Validate p1 belongs to correct skill range
                    if not (valid_min_skill <= p1['skill_level'] <= valid_max_skill):
                        continue
                        
                    for p2_idx, p2 in enumerate(group2['players']):
                        # Validate p2 belongs to correct skill range AND same gender
                        if (p1['gender'] == p2['gender'] and 
                            valid_min_skill <= p2['skill_level'] <= valid_max_skill):
                            
                            # Perform the swap
                            group1['players'][p1_idx] = p2
                            group2['players'][p2_idx] = p1
                            # Update totals
                            skill_diff = p1['skill_level'] - p2['skill_level']
                            group1['total_skill'] -= skill_diff
                            group2['total_skill'] += skill_diff
                            swap_made = True
                            break
        
        for iteration in range(max_iterations):  # Use variable iterations
            # Get current group totals for this subgroup
            current_skills = [groups[group_key][subgroup_type]['total_skill'] for group_key in group_keys]
            
            if not any(current_skills):
                break
                
            max_skill = max(current_skills)
            min_skill = min(current_skills)
            
            # Success: difference <= 1 (unless force_rebalance is True)
            if max_skill - min_skill <= 1 and not force_rebalance:
                break
            
            # For force_rebalance, do at least 10 iterations to ensure redistribution
            if force_rebalance and iteration < 10:
                pass  # Continue balancing even if already balanced
            elif max_skill - min_skill <= 1:
                break
            
            # Find max and min groups
            max_group_idx = current_skills.index(max_skill)
            min_group_idx = current_skills.index(min_skill)
            
            max_group = groups[group_keys[max_group_idx]][subgroup_type]
            min_group = groups[group_keys[min_group_idx]][subgroup_type]
            
            # Skip if either is empty
            if not max_group['players'] or not min_group['players']:
                break
            
            # Find best player swap using the simple proven algorithm
            best_swap = None
            best_improvement = 0
            
            for i, max_player in enumerate(max_group['players']):
                for j, min_player in enumerate(min_group['players']):
                    # Only swap same gender
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    # Calculate skill difference
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    
                    # Only swap if it reduces the gap
                    if skill_diff <= 0:
                        continue
                    
                    # Calculate new totals after swap
                    new_max_skill = max_skill - skill_diff
                    new_min_skill = min_skill + skill_diff
                    new_diff = abs(new_max_skill - new_min_skill)
                    
                    # If this improves balance, consider it
                    improvement = (max_skill - min_skill) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = (i, j, max_player, min_player, skill_diff)
            
            # Make the best swap
            if best_swap:
                i, j, max_player, min_player, skill_diff = best_swap
                # Swap players
                max_group['players'][i] = min_player
                min_group['players'][j] = max_player
                # Update totals
                max_group['total_skill'] -= skill_diff
                min_group['total_skill'] += skill_diff
            else:
                break  # No beneficial swap found
    
    # Balance subgroup 1 players
    balance_players_by_skill(subgroup1_selected, 'subgroup1', subgroup1_count, force_rebalance)
    
    # Balance subgroup 2 players  
    balance_players_by_skill(subgroup2_selected, 'subgroup2', subgroup2_count, force_rebalance)
    
    # Final step: Balance overall combined totals across all groups
    def balance_overall_groups():
        """Balance the combined totals of subgroup1 + subgroup2 across all groups"""
        max_iterations = 100
        
        # If force_rebalance is True, do more iterations but NO cross-subgroup swaps
        if force_rebalance:
            max_iterations = 200  # More iterations for better mixing
            
            # Only perform swaps WITHIN each subgroup type separately to maintain skill constraints
            # This ensures players never move between subgroups
            
            # Random swaps within subgroup1 only
            for _ in range(8):  # Reduced random swaps within subgroup1 only
                group1_idx = random.randint(0, len(group_keys)-1)
                group2_idx = random.randint(0, len(group_keys)-1)
                
                if group1_idx == group2_idx:
                    continue
                    
                group1_sg1 = groups[group_keys[group1_idx]]['subgroup1']
                group2_sg1 = groups[group_keys[group2_idx]]['subgroup1']
                
                if not group1_sg1['players'] or not group2_sg1['players']:
                    continue
                    
                # Swap within subgroup1 only (same skill range)
                for p1_idx, p1 in enumerate(group1_sg1['players']):
                    for p2_idx, p2 in enumerate(group2_sg1['players']):
                        if (p1['gender'] == p2['gender'] and 
                            subgroup1_min <= p1['skill_level'] <= subgroup1_max and
                            subgroup1_min <= p2['skill_level'] <= subgroup1_max):
                            
                            # Perform swap within subgroup1
                            group1_sg1['players'][p1_idx] = p2
                            group2_sg1['players'][p2_idx] = p1
                            # Update totals
                            skill_diff = p1['skill_level'] - p2['skill_level']
                            group1_sg1['total_skill'] -= skill_diff
                            group2_sg1['total_skill'] += skill_diff
                            break
                    else:
                        continue
                    break
                        
            # Random swaps within subgroup2 only  
            for _ in range(8):  # Reduced random swaps within subgroup2 only
                group1_idx = random.randint(0, len(group_keys)-1)
                group2_idx = random.randint(0, len(group_keys)-1)
                
                if group1_idx == group2_idx:
                    continue
                    
                group1_sg2 = groups[group_keys[group1_idx]]['subgroup2']
                group2_sg2 = groups[group_keys[group2_idx]]['subgroup2']
                
                if not group1_sg2['players'] or not group2_sg2['players']:
                    continue
                    
                # Swap within subgroup2 only (same skill range)
                for p1_idx, p1 in enumerate(group1_sg2['players']):
                    for p2_idx, p2 in enumerate(group2_sg2['players']):
                        if (p1['gender'] == p2['gender'] and 
                            subgroup2_min <= p1['skill_level'] <= subgroup2_max and
                            subgroup2_min <= p2['skill_level'] <= subgroup2_max):
                            
                            # Perform swap within subgroup2
                            group1_sg2['players'][p1_idx] = p2
                            group2_sg2['players'][p2_idx] = p1
                            # Update totals
                            skill_diff = p1['skill_level'] - p2['skill_level']
                            group1_sg2['total_skill'] -= skill_diff
                            group2_sg2['total_skill'] += skill_diff
                            break
                    else:
                        continue
                    break
                        
        for iteration in range(max_iterations):
            # Calculate combined totals
            combined_totals = []
            for key in group_keys:
                sg1_total = groups[key]['subgroup1']['total_skill']
                sg2_total = groups[key]['subgroup2']['total_skill']
                combined_totals.append(sg1_total + sg2_total)
            
            max_total = max(combined_totals)
            min_total = min(combined_totals)
            
            # If balanced within 1 point, we're done (unless force_rebalance is True)
            if max_total - min_total <= 1 and not force_rebalance:
                break
            
            # For force_rebalance, do at least 15 iterations to ensure redistribution
            if force_rebalance and iteration < 15:
                pass  # Continue balancing even if already balanced
            elif max_total - min_total <= 1:
                break
            
            # Find highest and lowest groups
            max_idx = combined_totals.index(max_total)
            min_idx = combined_totals.index(min_total)
            
            # Try swapping between subgroups of these groups
            best_swap = None
            best_improvement = 0
            
            # Try swaps within subgroup1 with skill validation
            max_sg1 = groups[group_keys[max_idx]]['subgroup1']
            min_sg1 = groups[group_keys[min_idx]]['subgroup1']
            
            for i, max_player in enumerate(max_sg1['players']):
                for j, min_player in enumerate(min_sg1['players']):
                    if max_player['gender'] != min_player['gender']:
                        continue
                    
                    # Validate both players belong to subgroup1 skill range
                    if not (subgroup1_min <= max_player['skill_level'] <= subgroup1_max):
                        continue
                    if not (subgroup1_min <= min_player['skill_level'] <= subgroup1_max):
                        continue
                    
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    if skill_diff <= 0:
                        continue
                    
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = ('subgroup1', i, j, max_player, min_player, skill_diff)
            
            # Try swaps within subgroup2 with skill validation
            max_sg2 = groups[group_keys[max_idx]]['subgroup2']
            min_sg2 = groups[group_keys[min_idx]]['subgroup2']
            
            for i, max_player in enumerate(max_sg2['players']):
                for j, min_player in enumerate(min_sg2['players']):
                    if max_player['gender'] != min_player['gender']:
                        continue
                        
                    # Validate both players belong to subgroup2 skill range
                    if not (subgroup2_min <= max_player['skill_level'] <= subgroup2_max):
                        continue
                    if not (subgroup2_min <= min_player['skill_level'] <= subgroup2_max):
                        continue
                    
                    skill_diff = max_player['skill_level'] - min_player['skill_level']
                    if skill_diff <= 0:
                        continue
                    
                    new_max_total = max_total - skill_diff
                    new_min_total = min_total + skill_diff
                    new_diff = abs(new_max_total - new_min_total)
                    
                    improvement = (max_total - min_total) - new_diff
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_swap = ('subgroup2', i, j, max_player, min_player, skill_diff)
            
            # Execute the best swap
            if best_swap:
                subgroup_type, i, j, max_player, min_player, skill_diff = best_swap
                
                max_subgroup = groups[group_keys[max_idx]][subgroup_type]
                min_subgroup = groups[group_keys[min_idx]][subgroup_type]
                
                # Swap players
                max_subgroup['players'][i] = min_player
                min_subgroup['players'][j] = max_player
                # Update totals
                max_subgroup['total_skill'] -= skill_diff
                min_subgroup['total_skill'] += skill_diff
            else:
                break  # No beneficial swap found
    
    # Apply final overall balancing
    balance_overall_groups()
    
    # VALIDATION: Ensure no players are in wrong subgroups
    for group_name in group_keys:
        # Validate subgroup1 players
        for player in groups[group_name]['subgroup1']['players']:
            if not (subgroup1_min <= player['skill_level'] <= subgroup1_max):
                raise ValueError(f"VALIDATION ERROR: Player {player['name']} (skill {player['skill_level']}) is in subgroup1 but should be in skill range {subgroup1_min}-{subgroup1_max}")
        
        # Validate subgroup2 players  
        for player in groups[group_name]['subgroup2']['players']:
            if not (subgroup2_min <= player['skill_level'] <= subgroup2_max):
                raise ValueError(f"VALIDATION ERROR: Player {player['name']} (skill {player['skill_level']}) is in subgroup2 but should be in skill range {subgroup2_min}-{subgroup2_max}")
    
    # Convert to the expected format - combine subgroups into main groups
    result_groups = {}
    for group_name in group_keys:
        all_players = []
        all_players.extend(groups[group_name]['subgroup1']['players'])
        all_players.extend(groups[group_name]['subgroup2']['players'])
        result_groups[group_name] = all_players
    
    return result_groups, groups  # Return both formats for detailed analysis


def calculate_group_stats(group_players):
    """Calculate statistics for a group"""
    if not group_players:
        return {"avg_skill": 0, "male_count": 0, "female_count": 0, "total_skill": 0}
    
    avg_skill = sum(p['skill_level'] for p in group_players) / len(group_players)
    male_count = sum(1 for p in group_players if p['gender'] == 'M')
    female_count = sum(1 for p in group_players if p['gender'] == 'F')
    total_skill = sum(p['skill_level'] for p in group_players)
    
    return {
        "avg_skill": round(avg_skill, 2),
        "male_count": male_count,
        "female_count": female_count,
        "total_skill": total_skill
    }

def calculate_standings_from_matches():
    """Calculate standings from individual match records"""
    if 'individual_matches' not in st.session_state:
        load_matches()  # Load matches from file
    
    standings_data = []
    
    # Calculate standings for each group
    for group_name in st.session_state.groups.keys():
        wins = 0
        losses = 0
        total_points = 0
        matches_played = 0
        
        # Count from individual matches
        for match in st.session_state.individual_matches:
            if match['team1'] == group_name:
                matches_played += 1
                if match['winner'] == group_name:
                    wins += 1
                    total_points += match['match_points']
                else:
                    losses += 1
            elif match['team2'] == group_name:
                matches_played += 1
                if match['winner'] == group_name:
                    wins += 1
                    total_points += match['match_points']
                else:
                    losses += 1
        
        standings_data.append({
            'Team': st.session_state.group_names.get(group_name, group_name),
            'Matches Played': matches_played,
            'Wins': wins,
            'Losses': losses,
            'Points': total_points,
            'Win Rate': f"{(wins/matches_played*100):.1f}%" if matches_played > 0 else "0.0%"
        })
    
    # Create DataFrame and sort by wins, then points
    df = pd.DataFrame(standings_data)
    if not df.empty:
        df = df.sort_values(['Wins', 'Points'], ascending=[False, False]).reset_index(drop=True)
        
        # Add rank column
        df.insert(0, 'Rank', range(1, len(df) + 1))
    
    return df

def manage_recorded_matches():
    """Display and manage all recorded matches"""
    if 'individual_matches' not in st.session_state:
        load_matches()  # Load matches from file
    
    if not st.session_state.individual_matches:
        st.info("📋 No matches recorded yet. Record your first match to get started!")
        return
    
    st.subheader(f"📋 Recorded Matches ({len(st.session_state.individual_matches)})")
    
    # Display matches in a table format
    for i, match in enumerate(st.session_state.individual_matches):
        with st.expander(f"Match #{i+1}: {match['team1_display']} vs {match['team2_display']} - {match['recorded_at'][:19]}", expanded=False):
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown("**Match Details:**")
                st.write(f"🏆 **Winner:** {st.session_state.group_names.get(match['winner'], match['winner'])}")
                st.write(f"🏅 **Score:** {match['score_display']} ({match['match_points']} points)")
                st.write(f"📏 **Recorded by:** {match['recorded_by']}")
                
            with col2:
                st.markdown("**Teams & Players:**")
                st.write(f"**{match['team1_display']}:** {', '.join(match['team1_players'])}")
                st.write(f"**{match['team2_display']}:** {', '.join(match['team2_players'])}")
                
                # Set by set breakdown
                st.markdown("**Set Scores:**")
                for set_num, (s1, s2) in enumerate(match['set_scores'].values(), 1):
                    if match['set_scores'][f'set{set_num}'] is not None:
                        st.write(f"Set {set_num}: {s1}-{s2}")
            
            with col3:
                if get_current_user_role() == 'superuser':
                    st.markdown("**Actions:**")
                    if st.button("✏️ Edit", key=f"edit_match_{i}"):
                        st.session_state.edit_match_index = i
                        st.rerun()
                    
                    if st.button("🗑️ Delete", key=f"delete_match_{i}"):
                        # Confirm deletion
                        if st.button(f"⚠️ Confirm Delete Match #{i+1}", key=f"confirm_delete_{i}", type="secondary"):
                            # Remove match using CRUD function
                            if delete_match(i):
                                # Recalculate standings
                                updated_standings = calculate_standings_from_matches()
                                if not updated_standings.empty:
                                    st.session_state.standings = updated_standings.set_index('Team')
                                
                                st.success(f"✅ Match #{i+1} deleted successfully!")
                                st.rerun()
                else:
                    st.info("🔒 Superuser\nrequired for edits")

def edit_selected_match():
    """Edit the selected match"""
    if 'edit_match_index' not in st.session_state:
        return
    
    match_index = st.session_state.edit_match_index
    match = st.session_state.individual_matches[match_index]
    
    st.subheader(f"✏️ Edit Match #{match_index+1}")
    
    # Display current match info
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Current Match:** {match['team1_display']} vs {match['team2_display']}")
    with col2:
        st.info(f"**Current Winner:** {st.session_state.group_names.get(match['winner'], match['winner'])} {match['score_display']}")
    
    # Edit form
    st.markdown("### 📝 Update Match Details")
    
    # Current players (read-only display)
    st.markdown("**Current Players:**")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"{match['team1_display']}: {', '.join(match['team1_players'])}")
    with col2:
        st.write(f"{match['team2_display']}: {', '.join(match['team2_players'])}")
    
    st.divider()
    
    # Edit scores
    st.markdown("**📊 Update Match Scores**")
    col1, col2, col3 = st.columns(3)
    
    # Get current scores
    current_set1 = match['set_scores']['set1']
    current_set2 = match['set_scores']['set2']
    current_set3 = match['set_scores'].get('set3', (0, 0))
    
    # Set 1
    with col1:
        st.markdown("**Set 1**")
        new_set1_g1 = st.number_input(f"{match['team1_display']}", min_value=0, max_value=30, 
                                     value=current_set1[0], key="edit_set1_g1")
        new_set1_g2 = st.number_input(f"{match['team2_display']}", min_value=0, max_value=30, 
                                     value=current_set1[1], key="edit_set1_g2")
    
    # Set 2
    with col2:
        st.markdown("**Set 2**")
        new_set2_g1 = st.number_input(f"{match['team1_display']}", min_value=0, max_value=30, 
                                     value=current_set2[0], key="edit_set2_g1")
        new_set2_g2 = st.number_input(f"{match['team2_display']}", min_value=0, max_value=30, 
                                     value=current_set2[1], key="edit_set2_g2")
    
    # Set 3
    with col3:
        st.markdown("**Set 3**")
        if current_set3 and (current_set3[0] > 0 or current_set3[1] > 0):
            new_set3_g1 = st.number_input(f"{match['team1_display']}", min_value=0, max_value=30, 
                                         value=current_set3[0], key="edit_set3_g1")
            new_set3_g2 = st.number_input(f"{match['team2_display']}", min_value=0, max_value=30, 
                                         value=current_set3[1], key="edit_set3_g2")
        else:
            new_set3_g1 = st.number_input(f"{match['team1_display']}", min_value=0, max_value=30, 
                                         value=0, key="edit_set3_g1")
            new_set3_g2 = st.number_input(f"{match['team2_display']}", min_value=0, max_value=30, 
                                         value=0, key="edit_set3_g2")
    
    # Calculate new winner and points
    new_sets_won_g1 = (new_set1_g1 > new_set1_g2) + (new_set2_g1 > new_set2_g2) + (new_set3_g1 > new_set3_g2)
    new_sets_won_g2 = (new_set1_g2 > new_set1_g1) + (new_set2_g2 > new_set2_g1) + (new_set3_g2 > new_set3_g1)
    
    new_winner = None
    new_points = 0
    if new_sets_won_g1 > new_sets_won_g2:
        new_winner = match['team1']
        new_points = 2 if new_sets_won_g1 == 2 and new_sets_won_g2 == 0 else 1
    elif new_sets_won_g2 > new_sets_won_g1:
        new_winner = match['team2']
        new_points = 2 if new_sets_won_g2 == 2 and new_sets_won_g1 == 0 else 1
    
    # Show new result preview
    st.divider()
    if new_winner:
        winner_display = match['team1_display'] if new_winner == match['team1'] else match['team2_display']
        st.success(f"🏆 **New Result:** {winner_display} wins ({new_sets_won_g1 if new_winner == match['team1'] else new_sets_won_g2}-{new_sets_won_g2 if new_winner == match['team1'] else new_sets_won_g1}) - {new_points} points")
    else:
        st.warning("⚠️ Please complete the score entry")
    
    # Edit reason
    edit_reason = st.text_input("Reason for editing:", placeholder="e.g., Score correction, missed set")
    
    # Update buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Save Changes", type="primary", disabled=new_winner is None):
            # Update the match using CRUD function
            updated_data = {
                'set_scores': {
                    'set1': (new_set1_g1, new_set1_g2),
                    'set2': (new_set2_g1, new_set2_g2), 
                    'set3': (new_set3_g1, new_set3_g2) if (new_set3_g1 > 0 or new_set3_g2 > 0) else None
                },
                'winner': new_winner,
                'sets_won_team1': new_sets_won_g1,
                'sets_won_team2': new_sets_won_g2,
                'match_points': new_points,
                'score_display': f"({new_sets_won_g1}-{new_sets_won_g2})",
                'last_edited_by': get_current_user(),
                'last_edited_at': datetime.now().isoformat(),
                'edit_reason': edit_reason
            }
            
            if update_match(match_index, updated_data):
                # Recalculate standings
                updated_standings = calculate_standings_from_matches()
                if not updated_standings.empty:
                    st.session_state.standings = updated_standings.set_index('Team')
                
                st.success("✅ Match updated successfully!")
                del st.session_state.edit_match_index  # Clear edit mode
                st.rerun()
    
    with col2:
        if st.button("❌ Cancel"):
            del st.session_state.edit_match_index
            st.rerun()
    
def calculate_standings():
    """Legacy function for backward compatibility with old clash-based data"""
    if 'tournament_data' not in st.session_state:
        st.session_state.tournament_data = {}
    
    standings_data = []
    
    # Calculate standings for each group from old tournament_data format
    for group_name in st.session_state.groups.keys():
        clash_wins = 0
        clash_losses = 0
        total_points = 0
        total_matches_won = 0
        total_matches_lost = 0
        
        # Count from tournament data
        for clash_key, matches in st.session_state.tournament_data.items():
            if group_name in clash_key and '_vs_' in clash_key:
                # Properly parse clash key (e.g., "Group A_vs_Group B")
                parts = clash_key.split('_vs_')
                if len(parts) == 2:
                    team1, team2 = parts[0], parts[1]
                    if team1 == group_name:
                        opponent = team2
                    elif team2 == group_name:
                        opponent = team1
                    else:
                        continue
                else:
                    continue
                
                # Count matches won/lost and points for this clash
                clash_matches_won = 0
                clash_matches_lost = 0
                clash_points = 0
                
                for match_result in matches:
                    winner = match_result.get('winner')
                    if winner == group_name:
                        clash_matches_won += 1
                        clash_points += match_result.get('match_points', 1)
                    elif winner == opponent:
                        clash_matches_lost += 1
                
                total_matches_won += clash_matches_won
                total_matches_lost += clash_matches_lost
                total_points += clash_points
                
                # Determine clash winner (best of 5 matches)
                if clash_matches_won > clash_matches_lost:
                    clash_wins += 1
                elif clash_matches_lost > clash_matches_won:
                    clash_losses += 1
        
        standings_data.append({
            'Team': st.session_state.group_names.get(group_name, group_name),
            'Clash Wins': clash_wins,
            'Clash Losses': clash_losses, 
            'Match Wins': total_matches_won,
            'Match Losses': total_matches_lost,
            'Points': total_points,
            'Clashes Played': clash_wins + clash_losses
        })
    
    # Create DataFrame and sort by clash wins, then points, then match wins
    df = pd.DataFrame(standings_data)
    if not df.empty:
        df = df.sort_values(['Clash Wins', 'Points', 'Match Wins'], ascending=[False, False, False]).reset_index(drop=True)
        
        # Add rank column
        df.insert(0, 'Rank', range(1, len(df) + 1))
    
    return df

def record_new_clash():
    """Function to handle match recording - now simplified to individual matches"""
    # Check if we're in edit mode for a specific match
    if 'edit_match_index' in st.session_state:
        edit_selected_match()
        return
    
    # Otherwise show the record single match interface
    record_single_match()

def edit_clash_results():
    """Function to handle editing/managing individual match results"""
    manage_recorded_matches()

def view_clash_results():
    """Function for viewing match results (read-only)"""
    if 'individual_matches' not in st.session_state:
        load_matches()  # Load matches from file
    
    if not st.session_state.individual_matches:
        st.info("📋 No matches recorded yet.")
        return
    
    st.subheader(f"📊 Match Results Summary ({len(st.session_state.individual_matches)} matches)")
    
    # Group matches by teams for better organization
    team_matches = {}
    for match in st.session_state.individual_matches:
        key = f"{match['team1_display']} vs {match['team2_display']}"
        if key not in team_matches:
            team_matches[key] = []
        team_matches[key].append(match)
    
    # Display grouped matches
    for team_pair, matches in team_matches.items():
        with st.expander(f"🎯 {team_pair} ({len(matches)} matches)"):
            team1_wins = 0
            team2_wins = 0
            team1_points = 0
            team2_points = 0
            
            for i, match in enumerate(matches):
                winner_name = st.session_state.group_names.get(match['winner'], match['winner'])
                st.write(f"**Match {i+1}:** {winner_name} wins {match['score_display']} - {match['match_points']} points")
                st.write(f"  📊 Players: {', '.join(match['team1_players'])} vs {', '.join(match['team2_players'])}")
                st.write(f"  📅 Recorded: {match['recorded_at'][:19]}")
                
                # Count wins and points
                if match['winner'] == match['team1']:
                    team1_wins += 1
                    team1_points += match['match_points']
                else:
                    team2_wins += 1
                    team2_points += match['match_points']
                
                st.markdown("---")
            
            # Summary for this team pair
            col1, col2 = st.columns(2)
            with col1:
                st.metric(match['team1_display'], f"{team1_wins} wins, {team1_points} points")
            with col2:
                st.metric(match['team2_display'], f"{team2_wins} wins, {team2_points} points")

def show_edit_history():
    """Function to display clash edit history"""
    if not st.session_state.clash_edit_history:
        st.info("📝 No edit history available.")
        return
    
    st.markdown("**All Clash Edits:**")
    
    # Sort by timestamp (newest first)
    sorted_history = sorted(st.session_state.clash_edit_history, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    for i, edit in enumerate(sorted_history):
        with st.expander(f"🔄 Edit #{i+1}: {edit.get('clash_key', 'Unknown')} - {edit.get('timestamp', 'Unknown time')}"):
            st.write(f"**Editor:** {edit.get('editor', 'Unknown')}")
            st.write(f"**Action:** {edit.get('action', 'Unknown')}")
            st.write(f"**Match:** {edit.get('match_number', 'Unknown')}")
            
            if edit.get('original_data'):
                st.markdown("**Original Data:**")
                st.json(edit.get('original_data'))
            
            if edit.get('new_data'):
                st.markdown("**New Data:**")
                st.json(edit.get('new_data'))
            
            if edit.get('reason'):
                st.write(f"**Reason:** {edit.get('reason')}")

def log_clash_edit(clash_key, match_number, action, original_data, new_data, reason=""):
    """Log clash edit to history"""
    edit_entry = {
        'timestamp': datetime.now().isoformat(),
        'editor': get_current_user(),
        'clash_key': clash_key,
        'match_number': match_number,
        'action': action,
        'original_data': original_data,
        'new_data': new_data,
        'reason': reason
    }
    
    st.session_state.clash_edit_history.append(edit_entry)
    auto_save()  # Save immediately after logging

def record_single_match():
    """Simple UI to record a single match"""
    st.subheader("📝 Record a Single Match")
    st.info("💡 Record one doubles match at a time for accurate tracking")
    
    # Step 1: Select Groups
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Select Team 1:**")
        group_options = [st.session_state.group_names.get(key, key) for key in st.session_state.groups.keys() if st.session_state.groups[key]]
        group_keys = [key for key in st.session_state.groups.keys() if st.session_state.groups[key]]
        
        if not group_options:
            st.error("No groups with players found. Please set up teams first.")
            return
            
        g1_display = st.selectbox("Team 1", group_options, key="match_g1")
        g1 = group_keys[group_options.index(g1_display)]
        
    with col2:
        st.markdown("**Select Team 2:**")
        g2_display = st.selectbox("Team 2", group_options, key="match_g2")
        g2 = group_keys[group_options.index(g2_display)]

    if g1 == g2:
        st.error("Please select two different teams.")
        return
    
    # Step 2: Select Subgroups (if applicable)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{g1_display} Subgroup:**")
        subgroup_options = list(st.session_state.subgroup_names.values()) + ["All Players"]
        subgroup_keys = list(st.session_state.subgroup_names.keys()) + ["all"]
        g1_sub = st.selectbox(f"{g1_display} players from", subgroup_options, key="g1_subgroup")
        g1_sub_key = subgroup_keys[subgroup_options.index(g1_sub)]
        
    with col2:
        st.markdown(f"**{g2_display} Subgroup:**")
        g2_sub = st.selectbox(f"{g2_display} players from", subgroup_options, key="g2_subgroup")
        g2_sub_key = subgroup_keys[subgroup_options.index(g2_sub)]
    
    # Get filtered players
    def get_subgroup_players(group_name, subgroup_key):
        if subgroup_key == "all":
            return st.session_state.groups.get(group_name, [])
        
        if not hasattr(st.session_state, 'detailed_groups') or not st.session_state.detailed_groups:
            return st.session_state.groups.get(group_name, [])
        
        group_subgroups = st.session_state.detailed_groups.get(group_name, {})
        subgroup_data = group_subgroups.get(subgroup_key, {})
        players = subgroup_data.get('players', st.session_state.groups.get(group_name, []))
        
        # Extract player names from objects if they are stored as dictionaries
        if players and isinstance(players[0], dict):
            return [player['name'] for player in players if 'name' in player]
        else:
            return players
    
    g1_players = get_subgroup_players(g1, g1_sub_key)
    g2_players = get_subgroup_players(g2, g2_sub_key)
    
    if len(g1_players) < 2:
        st.error(f"{g1_display} needs at least 2 players in selected subgroup.")
        return
    if len(g2_players) < 2:
        st.error(f"{g2_display} needs at least 2 players in selected subgroup.")
        return
    
    st.divider()
    
    # Step 3: Select Players
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**{g1_display} Pair:**")
        g1_p1 = st.selectbox(f"{g1_display} Player 1", g1_players, key="g1_p1")
        remaining_g1 = [p for p in g1_players if p != g1_p1]
        g1_p2 = st.selectbox(f"{g1_display} Player 2", remaining_g1, key="g1_p2")
        
    with col2:
        st.markdown(f"**{g2_display} Pair:**")
        g2_p1 = st.selectbox(f"{g2_display} Player 1", g2_players, key="g2_p1")
        remaining_g2 = [p for p in g2_players if p != g2_p1]
        g2_p2 = st.selectbox(f"{g2_display} Player 2", remaining_g2, key="g2_p2")
    
    st.divider()
    
    # Step 4: Enter Match Scores
    st.markdown("**📊 Match Score Entry**")
    col1, col2, col3 = st.columns(3)
    
    # Set 1
    with col1:
        st.markdown("**Set 1**")
        set1_g1 = st.number_input(f"{g1_display}", min_value=0, max_value=30, value=0, key="set1_g1")
        set1_g2 = st.number_input(f"{g2_display}", min_value=0, max_value=30, value=0, key="set1_g2")
    
    # Set 2
    with col2:
        st.markdown("**Set 2**")
        set2_g1 = st.number_input(f"{g1_display}", min_value=0, max_value=30, value=0, key="set2_g1")
        set2_g2 = st.number_input(f"{g2_display}", min_value=0, max_value=30, value=0, key="set2_g2")
    
    # Set 3 (if needed)
    set_1_winner = g1 if set1_g1 > set1_g2 else g2 if set1_g2 > set1_g1 else None
    set_2_winner = g1 if set2_g1 > set2_g2 else g2 if set2_g2 > set2_g1 else None
    
    match_decided = (set_1_winner == set_2_winner and set_1_winner is not None)
    
    with col3:
        st.markdown("**Set 3** (if needed)")
        if match_decided:
            st.info("Match decided in 2 sets")
            set3_g1 = 0
            set3_g2 = 0
        else:
            set3_g1 = st.number_input(f"{g1_display}", min_value=0, max_value=30, value=0, key="set3_g1")
            set3_g2 = st.number_input(f"{g2_display}", min_value=0, max_value=30, value=0, key="set3_g2")
    
    # Calculate winner and points
    sets_won_g1 = (set1_g1 > set1_g2) + (set2_g1 > set2_g2) + (set3_g1 > set3_g2)
    sets_won_g2 = (set1_g2 > set1_g1) + (set2_g2 > set2_g1) + (set3_g2 > set3_g1)
    
    winner = None
    points = 0
    if sets_won_g1 > sets_won_g2:
        winner = g1
        points = 2 if sets_won_g1 == 2 and sets_won_g2 == 0 else 1
    elif sets_won_g2 > sets_won_g1:
        winner = g2
        points = 2 if sets_won_g2 == 2 and sets_won_g1 == 0 else 1
    
    # Match summary
    st.divider()
    if winner:
        winner_display = g1_display if winner == g1 else g2_display
        st.success(f"🏆 **Winner:** {winner_display} ({sets_won_g1 if winner == g1 else sets_won_g2}-{sets_won_g2 if winner == g1 else sets_won_g1}) - {points} points")
    else:
        st.warning("⚠️ Please complete the score entry to determine winner")
    
    # Submit button
    submit_enabled = winner is not None and (set1_g1 > 0 or set1_g2 > 0)
    
    if st.button("✅ Record Match", type="primary", disabled=not submit_enabled):
        # Create match record
        match_record = {
            'match_id': f"{g1}_{g2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'team1': g1,
            'team2': g2, 
            'team1_display': g1_display,
            'team2_display': g2_display,
            'team1_players': [g1_p1, g1_p2],
            'team2_players': [g2_p1, g2_p2],
            'team1_subgroup': g1_sub,
            'team2_subgroup': g2_sub,
            'set_scores': {
                'set1': (set1_g1, set1_g2),
                'set2': (set2_g1, set2_g2),
                'set3': (set3_g1, set3_g2) if not match_decided else None
            },
            'winner': winner,
            'sets_won_team1': sets_won_g1,
            'sets_won_team2': sets_won_g2,
            'match_points': points,
            'recorded_by': get_current_user(),
            'recorded_at': datetime.now().isoformat(),
            'score_display': f"({sets_won_g1}-{sets_won_g2})"
        }
        
        # Store in session state for individual matches
        # Add match using the new CRUD function
        add_match(match_record)
        
        # Update standings
        updated_standings = calculate_standings_from_matches()
        if not updated_standings.empty:
            st.session_state.standings = updated_standings.set_index('Team')
        
        # Save data
        auto_save()
        
        st.success("🎉 Match recorded successfully!")
        st.success("📊 Standings updated!")
        st.balloons()
        st.rerun()


# --- MAIN MENU STRUCTURE ---
if menu == "Player Import & Auto-Balance":
    st.header("📊 Player Import & Team Auto-Balancing")
    st.markdown("Import players with detailed information and automatically create balanced groups.")
    
    # Import Methods
    st.subheader("📥 Import Players")
    
    import_method = st.radio("Choose import method:", ["Manual Entry", "CSV/Excel Upload", "Bulk Text Import"])
    
    if import_method == "CSV/Excel Upload":
        st.info("Upload a CSV or Excel file with columns: name, gender (M/F), email, skill_level (1-10)")
        
        # Template download options
        template_data = {
            'name': ['John Doe', 'Jane Smith', 'Mike Johnson'],
            'gender': ['M', 'F', 'M'],
            'email': ['john@example.com', 'jane@example.com', 'mike@example.com'],
            'skill_level': [7, 8, 6]
        }
        template_df = pd.DataFrame(template_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV template
            csv_template = template_df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV Template",
                data=csv_template,
                file_name="player_template.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel template
            try:
                excel_buffer = io.BytesIO()
                template_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                excel_template = excel_buffer.getvalue()
                
                st.download_button(
                    label="📊 Download Excel Template",
                    data=excel_template,
                    file_name="player_template.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info("📊 Excel template: Install openpyxl to enable Excel template download")
        
        uploaded_file = st.file_uploader(
            "Choose file", 
            type=["csv", "xlsx", "xls"],
            help="Upload CSV or Excel file with player data"
        )
        
        if uploaded_file is not None:
            try:
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                # Read file based on extension
                if file_extension == 'csv':
                    new_players_df = pd.read_csv(uploaded_file)
                elif file_extension in ['xlsx', 'xls']:
                    try:
                        # Try with openpyxl first (for .xlsx)
                        new_players_df = pd.read_excel(uploaded_file, engine='openpyxl')
                    except ImportError:
                        try:
                            # Fallback to xlrd (for .xls)
                            new_players_df = pd.read_excel(uploaded_file, engine='xlrd')
                        except ImportError:
                            st.error("❌ Excel support not available. Please install openpyxl: `pip install openpyxl`")
                            st.stop()
                    except Exception as e:
                        # Try with different engines
                        try:
                            new_players_df = pd.read_excel(uploaded_file)
                        except Exception as e2:
                            st.error(f"❌ Error reading Excel file: {str(e2)}")
                            st.stop()
                else:
                    st.error("❌ Unsupported file format")
                    st.stop()
                
                # Validate columns
                required_cols = ['name', 'gender', 'email', 'skill_level']
                if all(col in new_players_df.columns for col in required_cols):
                    # Validate data
                    new_players_df['gender'] = new_players_df['gender'].str.upper()
                    new_players_df['skill_level'] = pd.to_numeric(new_players_df['skill_level'], errors='coerce')
                    
                    # Filter valid rows
                    valid_rows = (
                        new_players_df['gender'].isin(['M', 'F']) &
                        new_players_df['skill_level'].between(1, 10) &
                        new_players_df['name'].notna() &
                        new_players_df['email'].notna()
                    )
                    
                    valid_players = new_players_df[valid_rows].copy()
                    invalid_count = len(new_players_df) - len(valid_players)
                    
                    if len(valid_players) > 0:
                        st.success(f"✅ Found {len(valid_players)} valid players in {file_extension.upper()} file")
                        if invalid_count > 0:
                            st.warning(f"⚠️ Skipped {invalid_count} invalid rows")
                        
                        # Preview data
                        st.dataframe(valid_players, use_container_width=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            replace_existing = st.checkbox("Replace all existing players", value=True)
                        
                        if st.button("Import These Players", type="primary"):
                            # Add missing columns
                            valid_players['group'] = None
                            valid_players['assigned'] = False
                            
                            if replace_existing:
                                st.session_state.player_database = valid_players
                            else:
                                st.session_state.player_database = pd.concat([st.session_state.player_database, valid_players], ignore_index=True)
                            
                            auto_save()  # Auto-save after import
                            st.success(f"🎉 Players imported successfully from {file_extension.upper()} file!")
                            st.rerun()
                    else:
                        st.error("❌ No valid players found in the uploaded file")
                else:
                    st.error(f"❌ Missing required columns. Expected: {required_cols}")
                    st.info(f"Found columns: {list(new_players_df.columns)}")
                    
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
                st.info("💡 Tip: Make sure your file has the correct format and required columns")
    
    elif import_method == "Bulk Text Import":
        st.info("Enter players in format: Name, Gender(M/F), Email, Skill(1-10) - one per line")
        
        bulk_input = st.text_area(
            "Enter player data:",
            height=300,
            placeholder="John Doe, M, john@example.com, 7\nJane Smith, F, jane@example.com, 8\nMike Johnson, M, mike@example.com, 6"
        )
        
        if st.button("Parse and Import", type="primary") and bulk_input.strip():
            players_data = []
            lines = bulk_input.strip().split('\n')
            
            for line_num, line in enumerate(lines, 1):
                try:
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        name, gender, email, skill = parts[0], parts[1].upper(), parts[2], int(parts[3])
                        if gender in ['M', 'F'] and 1 <= skill <= 10:
                            players_data.append({
                                'name': name,
                                'gender': gender,
                                'email': email,
                                'skill_level': skill,
                                'group': None,
                                'assigned': False
                            })
                        else:
                            st.warning(f"⚠️ Line {line_num}: Invalid gender or skill level")
                    else:
                        st.warning(f"⚠️ Line {line_num}: Not enough data fields")
                except:
                    st.warning(f"⚠️ Line {line_num}: Error parsing data")
            
            if players_data:
                new_df = pd.DataFrame(players_data)
                st.session_state.player_database = new_df
                auto_save()  # Auto-save after bulk import
                st.success(f"✅ Imported {len(players_data)} players!")
                st.rerun()
    
    elif import_method == "Manual Entry":
        st.info("Add players one by one")
        
        with st.form("manual_player_entry"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                player_name = st.text_input("Player Name")
            with col2:
                player_gender = st.selectbox("Gender", ["M", "F"])
            with col3:
                player_email = st.text_input("Email")
            with col4:
                player_skill = st.number_input("Skill Level", min_value=1, max_value=10, value=5)
            
            if st.form_submit_button("Add Player"):
                if player_name.strip() and player_email.strip():
                    new_player = pd.DataFrame({
                        'name': [player_name.strip()],
                        'gender': [player_gender],
                        'email': [player_email.strip()],
                        'skill_level': [player_skill],
                        'group': [None],
                        'assigned': [False]
                    })
                    
                    st.session_state.player_database = pd.concat([st.session_state.player_database, new_player], ignore_index=True)
                    auto_save()  # Auto-save after manual entry
                    st.success(f"✅ Added {player_name}!")
                    st.rerun()
                else:
                    st.error("Please enter both name and email")
    
    st.divider()
    
    # Current Player Database
    st.subheader("👥 Current Player Database")
    
    if not st.session_state.player_database.empty:
        # Display statistics
        total_players = len(st.session_state.player_database)
        male_players = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'M'])
        female_players = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'F'])
        avg_skill = st.session_state.player_database['skill_level'].mean()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Players", total_players)
        with col2:
            st.metric("Male Players", male_players)
        with col3:
            st.metric("Female Players", female_players)
        with col4:
            st.metric("Avg Skill Level", f"{avg_skill:.1f}")
        
        # Editable dataframe
        edited_df = st.data_editor(
            st.session_state.player_database,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "skill_level": st.column_config.NumberColumn(
                    "Skill Level",
                    min_value=1,
                    max_value=10,
                    step=1,
                ),
                "gender": st.column_config.SelectboxColumn(
                    "Gender",
                    options=["M", "F"],
                ),
            },
            key="player_database_editor"
        )
        
        # Update the database
        st.session_state.player_database = edited_df
        
        st.divider()
        
        # Auto-Balance Groups
        st.subheader("⚖️ Auto-Balance Groups")
        st.info("Automatically create balanced groups based on skill level and gender distribution")
        
        if len(st.session_state.player_database) >= 60:
            # Balance strategy selection
            balance_strategy = st.selectbox(
                "Balancing Strategy:",
                ["Optimized Balance (Recommended)", "Skill-Level Subgroups", "Snake Draft", "Random"],
                help="Choose how to balance players across groups"
            )
            
            # Gender distribution constraints (for Optimized Balance strategy)
            if balance_strategy == "Optimized Balance (Recommended)":
                st.markdown("#### 👥 Gender Distribution Settings")
                
                # Get current female player count
                total_females = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'F'])
                total_males = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'M'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Female Players", total_females)
                with col2:
                    st.metric("Total Male Players", total_males)
                with col3:
                    st.metric("Total Players", total_females + total_males)
                
                # Min/Max females per group settings
                col1, col2 = st.columns(2)
                with col1:
                    min_females = st.number_input(
                        "Minimum females per group:",
                        min_value=0,
                        max_value=total_females // 6 if total_females > 0 else 0,
                        value=max(0, total_females // 6 if total_females > 0 else 0),
                        help="Minimum number of female players in each group"
                    )
                with col2:
                    max_females = st.number_input(
                        "Maximum females per group:",
                        min_value=min_females,
                        max_value=10,
                        value=min(10, (total_females + 5) // 6 if total_females > 0 else 0),
                        help="Maximum number of female players in each group"
                    )
                
                # Validation and preview
                if total_females > 0:
                    min_total_needed = min_females * 6
                    max_total_capacity = max_females * 6
                    
                    if min_total_needed > total_females:
                        st.error(f"❌ Minimum constraint too high: need {min_total_needed} females, but only have {total_females}")
                    elif max_total_capacity < total_females:
                        st.error(f"❌ Maximum constraint too low: can fit {max_total_capacity} females, but have {total_females}")
                    else:
                        # Show distribution preview
                        avg_females = total_females / 6
                        st.success(f"✅ Valid constraints. Average females per group: {avg_females:.1f}")
                        
                        if st.checkbox("Show detailed distribution preview"):
                            # Calculate expected distribution
                            base_females = [min_females] * 6
                            remaining = total_females - (min_females * 6)
                            for i in range(6):
                                if remaining > 0 and base_females[i] < max_females:
                                    add_count = min(remaining, max_females - base_females[i])
                                    base_females[i] += add_count
                                    remaining -= add_count
                            
                            preview_df = pd.DataFrame({
                                'Group': [f'Group {chr(65+i)}' for i in range(6)],
                                'Expected Females': base_females,
                                'Expected Males': [10 - f for f in base_females]
                            })
                            st.dataframe(preview_df, use_container_width=True)
            
            # Show subgroup options if selected
            if balance_strategy == "Skill-Level Subgroups":
                st.markdown("#### 🎯 Tournament Configuration")
                st.info("Configure the tournament structure, skill level ranges, and player counts")
                
                # Number of groups configuration
                num_groups = st.number_input(
                    "Number of Main Groups:", 
                    min_value=2, max_value=12, value=6, 
                    key="num_groups",
                    help="Total number of main groups to create (e.g., 6 creates Groups A-F)"
                )
                
                # Generate group labels dynamically
                group_labels = [f"Group {chr(65+i)}" for i in range(num_groups)]
                st.info(f"Will create: {', '.join(group_labels)}")
                
                # Gender distribution constraints
                st.markdown("#### 👥 Gender Distribution Settings")
                
                # Get current female player count
                total_females = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'F'])
                total_males = len(st.session_state.player_database[st.session_state.player_database['gender'] == 'M'])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Female Players", total_females)
                with col2:
                    st.metric("Total Male Players", total_males)
                with col3:
                    st.metric("Total Players", total_females + total_males)
                
                # Gender constraint toggle
                use_gender_constraints = st.checkbox(
                    "Enable gender distribution constraints",
                    help="Control the number of female players per group"
                )
                
                if use_gender_constraints:
                    col1, col2 = st.columns(2)
                    with col1:
                        min_females_sg = st.number_input(
                            "Minimum females per group:",
                            min_value=0,
                            max_value=total_females // num_groups if total_females > 0 else 0,
                            value=max(0, total_females // num_groups if total_females > 0 else 0),
                            key="min_females_sg",
                            help="Minimum number of female players in each group"
                        )
                    with col2:
                        max_females_sg = st.number_input(
                            "Maximum females per group:",
                            min_value=min_females_sg,
                            max_value=15,
                            value=min(15, (total_females + num_groups-1) // num_groups if total_females > 0 else 0),
                            key="max_females_sg",
                            help="Maximum number of female players in each group"
                        )
                    
                    # Validation for gender constraints
                    if total_females > 0:
                        min_total_needed = min_females_sg * num_groups
                        max_total_capacity = max_females_sg * num_groups
                        
                        if min_total_needed > total_females:
                            st.error(f"❌ Minimum constraint too high: need {min_total_needed} females, but only have {total_females}")
                        elif max_total_capacity < total_females:
                            st.error(f"❌ Maximum constraint too low: can fit {max_total_capacity} females, but have {total_females}")
                        else:
                            st.success(f"✅ Valid gender constraints. Average females per group: {total_females/num_groups:.1f}")
                
                # Skill level ranges
                col1, col2 = st.columns(2)
                with col1:
                    subgroup1_name = st.session_state.subgroup_names.get('subgroup1', '1 (Lower)')
                    st.markdown(f"**{subgroup1_name}**")
                    subgroup1_min = st.number_input("Min Skill Level:", min_value=1, max_value=10, value=1, key="sg1_min")
                    subgroup1_max = st.number_input("Max Skill Level:", min_value=1, max_value=10, value=5, key="sg1_max")
                    
                with col2:
                    subgroup2_name = st.session_state.subgroup_names.get('subgroup2', '2 (Higher)')
                    st.markdown(f"**{subgroup2_name}**")
                    subgroup2_min = st.number_input("Min Skill Level:", min_value=1, max_value=10, value=6, key="sg2_min")
                    subgroup2_max = st.number_input("Max Skill Level:", min_value=1, max_value=10, value=10, key="sg2_max")
                
                # Player count configuration
                st.markdown("#### 📊 Player Count Configuration")
                st.info("Specify how many players should be in each subgroup across all groups")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    subgroup1_count = st.number_input(
                        f"Players per {subgroup1_name}:", 
                        min_value=1, max_value=15, value=5, 
                        key="sg1_count",
                        help=f"Number of players in each {subgroup1_name.lower()} across {num_groups} groups"
                    )
                with col2:
                    subgroup2_count = st.number_input(
                        f"Players per {subgroup2_name}:", 
                        min_value=1, max_value=15, value=5, 
                        key="sg2_count",
                        help=f"Number of players in each {subgroup2_name.lower()} across {num_groups} groups"
                    )
                with col3:
                    total_per_group = subgroup1_count + subgroup2_count
                    st.metric("Total per Group", total_per_group)
                    st.metric("Tournament Total", total_per_group * num_groups)
                
                # Validate ranges
                if subgroup1_max >= subgroup2_min:
                    st.warning(f"⚠️ Subgroup ranges should not overlap. Adjust the ranges so {subgroup1_name} max is less than {subgroup2_name} min.")
                
                # Show preview of player distribution
                if st.button("🔍 Preview Player Distribution"):
                    available_sg1 = len(st.session_state.player_database[
                        (st.session_state.player_database['skill_level'] >= subgroup1_min) & 
                        (st.session_state.player_database['skill_level'] <= subgroup1_max)
                    ])
                    available_sg2 = len(st.session_state.player_database[
                        (st.session_state.player_database['skill_level'] >= subgroup2_min) & 
                        (st.session_state.player_database['skill_level'] <= subgroup2_max)
                    ])
                    
                    needed_sg1 = subgroup1_count * num_groups
                    needed_sg2 = subgroup2_count * num_groups
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Available SG1", available_sg1)
                        if available_sg1 < needed_sg1:
                            st.error(f"Need {needed_sg1}, short by {needed_sg1 - available_sg1}")
                        else:
                            st.success(f"Sufficient (need {needed_sg1})")
                    
                    with col2:
                        st.metric("Available SG2", available_sg2)
                        if available_sg2 < needed_sg2:
                            st.error(f"Need {needed_sg2}, short by {needed_sg2 - available_sg2}")
                        else:
                            st.success(f"Sufficient (need {needed_sg2})")
                    
                    with col3:
                        total_available = available_sg1 + available_sg2
                        total_needed = needed_sg1 + needed_sg2
                        st.metric("Total Available", total_available)
                        
                    with col4:
                        st.metric("Total Needed", total_needed)
                        if total_available >= total_needed:
                            st.success("✓ Feasible")
                        else:
                            st.error(f"❌ Short by {total_needed - total_available}")
                    
                    if total_available > total_needed:
                        excess = total_available - total_needed
                        st.info(f"📈 {excess} players will not be assigned (excess players)")
            
            # Create balanced groups button
            if st.button("🎯 Create Balanced Groups", type="primary", help="This will redistribute all players into balanced groups"):
                with st.spinner("Creating balanced groups... This may take a moment."):
                    # Clear existing groups to ensure fresh redistribution
                    st.session_state.groups = {}
                    if hasattr(st.session_state, 'detailed_groups'):
                        st.session_state.detailed_groups = {}
                    
                    # Reset player assignments in database
                    if 'group' in st.session_state.player_database.columns:
                        st.session_state.player_database['group'] = None
                    if 'assigned' in st.session_state.player_database.columns:
                        st.session_state.player_database['assigned'] = False
                    
                    if balance_strategy == "Skill-Level Subgroups":
                        # Validate subgroup ranges
                        if subgroup1_max >= subgroup2_min:
                            st.error("❌ Please fix the subgroup ranges before proceeding.")
                            st.stop()
                        
                        try:
                            # Auto-balance with subgroups and gender constraints
                            gender_constraints = {}
                            if 'use_gender_constraints' in locals() and use_gender_constraints:
                                gender_constraints = {
                                    'min_females_per_group': min_females_sg,
                                    'max_females_per_group': max_females_sg
                                }
                            
                            balanced_groups, detailed_groups = auto_balance_subgroups(
                                st.session_state.player_database, 
                                subgroup1_min, subgroup1_max, 
                                subgroup2_min, subgroup2_max,
                                subgroup1_count, subgroup2_count, num_groups,
                                force_rebalance=True,  # Force complete redistribution
                                **gender_constraints
                            )
                            
                            # Store detailed subgroup information for display
                            st.session_state.detailed_groups = detailed_groups
                            
                        except ValueError as e:
                            st.error(f"❌ {str(e)}")
                            st.info("💡 Use the 'Preview Player Distribution' button to check availability before balancing.")
                            st.stop()
                        
                    else:
                        # Use traditional auto-balance with gender constraints if specified
                        if balance_strategy == "Optimized Balance (Recommended)":
                            balanced_groups = auto_balance_groups(
                                st.session_state.player_database,
                                min_females_per_group=min_females if 'min_females' in locals() else None,
                                max_females_per_group=max_females if 'max_females' in locals() else None,
                                force_rebalance=True  # Force complete redistribution
                            )
                        else:
                            balanced_groups = auto_balance_groups(st.session_state.player_database, force_rebalance=True)
                    
                    # Update session state for both strategies
                    st.session_state.groups = {}
                    updated_players = st.session_state.player_database.copy()
                    
                    for group_name, players_list in balanced_groups.items():
                        player_names = []
                        for player in players_list:
                            player_names.append(player['name'])
                            # Update player database with group assignment
                            mask = updated_players['name'] == player['name']
                            updated_players.loc[mask, 'group'] = group_name
                            updated_players.loc[mask, 'assigned'] = True
                        
                        st.session_state.groups[group_name] = player_names
                    
                    st.session_state.player_database = updated_players
                    
                    # Update standings to include new groups
                    st.session_state.standings = pd.DataFrame({
                        "Group": [st.session_state.group_names.get(key, key) for key in st.session_state.groups.keys()],
                        "Clash Wins": [0] * len(st.session_state.groups),
                        "Total Points": [0] * len(st.session_state.groups)
                    }).set_index("Group")
                    
                    auto_save()  # Auto-save after group balancing
                    st.success("🎉 Groups have been auto-balanced!")
                    st.balloons()
                    st.rerun()
        else:
            st.warning(f"⚠️ Need at least 60 players for auto-balancing. Currently have {len(st.session_state.player_database)} players.")
        
        # Show current group balance if groups exist
        if st.session_state.groups and any(st.session_state.groups.values()):
            st.divider()
            st.subheader("📊 Current Group Balance & Player Distribution")
            
            # Collect balance data and player lists
            balance_data = []
            group_player_details = {}
            
            for group_name, player_names in st.session_state.groups.items():
                if player_names:
                    # Get player details for this group
                    group_players_df = st.session_state.player_database[
                        st.session_state.player_database['name'].isin(player_names)
                    ]
                    
                    if not group_players_df.empty:
                        # Store detailed player info for display
                        group_player_details[group_name] = group_players_df.sort_values('skill_level', ascending=False)
                        
                        stats = {
                            'Group': st.session_state.group_names.get(group_name, group_name),
                            'Players': len(group_players_df),
                            'Males': len(group_players_df[group_players_df['gender'] == 'M']),
                            'Females': len(group_players_df[group_players_df['gender'] == 'F']),
                            'Avg Skill': round(group_players_df['skill_level'].mean(), 2),
                            'Total Skill': group_players_df['skill_level'].sum(),
                            'Skill Range': f"{group_players_df['skill_level'].min()}-{group_players_df['skill_level'].max()}"
                        }
                        balance_data.append(stats)
            
            if balance_data:
                # Display balance summary table
                balance_df = pd.DataFrame(balance_data)
                st.dataframe(balance_df, use_container_width=True)
                
                # Balance quality metrics
                if len(balance_data) > 1:
                    skill_variance = balance_df['Total Skill'].var()
                    avg_variance = balance_df['Avg Skill'].var()
                    gender_balance = balance_df['Females'].std()
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Skill Variance", f"{skill_variance:.2f}", help="Lower is better (0 = perfectly balanced)")
                    with col2:
                        st.metric("Avg Skill Variance", f"{avg_variance:.3f}", help="Lower is better")
                    with col3:
                        st.metric("Gender Balance Quality", f"{gender_balance:.2f}", help="Lower is better (more even distribution)")
                    with col4:
                        skill_range = balance_df['Total Skill'].max() - balance_df['Total Skill'].min()
                        st.metric("Skill Point Range", f"{skill_range}", help="Difference between strongest and weakest group")
                
                # Show subgroup breakdown if detailed groups exist
                if hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups:
                    st.divider()
                    st.subheader("🎯 Subgroup Distribution Analysis")
                    subgroup1_name = st.session_state.subgroup_names.get('subgroup1', '1 (Lower)')
                    subgroup2_name = st.session_state.subgroup_names.get('subgroup2', '2 (Higher)')
                    st.info(f"Breakdown of players by skill-level subgroups ({subgroup1_name} & {subgroup2_name}) within each group")
                    
                    subgroup_data = []
                    for group_name, subgroups in st.session_state.detailed_groups.items():
                        # Subgroup 1 stats
                        sg1_players = subgroups['subgroup1']['players']
                        if sg1_players:
                            sg1_stats = {
                                'Group': f"{st.session_state.group_names.get(group_name, group_name)} - {st.session_state.subgroup_names.get('subgroup1', '1 (Lower)')}",
                                'Subgroup': st.session_state.subgroup_names.get('subgroup1', '1 (Lower)'),
                                'Players': len(sg1_players),
                                'Males': subgroups['subgroup1']['male_count'],
                                'Females': subgroups['subgroup1']['female_count'],
                                'Avg Skill': round(sum(p['skill_level'] for p in sg1_players) / len(sg1_players), 2),
                                'Total Skill': subgroups['subgroup1']['total_skill'],
                                'Skill Range': f"{min(p['skill_level'] for p in sg1_players)}-{max(p['skill_level'] for p in sg1_players)}"
                            }
                            subgroup_data.append(sg1_stats)
                        
                        # Subgroup 2 stats  
                        sg2_players = subgroups['subgroup2']['players']
                        if sg2_players:
                            sg2_stats = {
                                'Group': f"{st.session_state.group_names.get(group_name, group_name)} - {st.session_state.subgroup_names.get('subgroup2', '2 (Higher)')}",
                                'Subgroup': st.session_state.subgroup_names.get('subgroup2', '2 (Higher)'),
                                'Players': len(sg2_players),
                                'Males': subgroups['subgroup2']['male_count'],
                                'Females': subgroups['subgroup2']['female_count'],
                                'Avg Skill': round(sum(p['skill_level'] for p in sg2_players) / len(sg2_players), 2),
                                'Total Skill': subgroups['subgroup2']['total_skill'],
                                'Skill Range': f"{min(p['skill_level'] for p in sg2_players)}-{max(p['skill_level'] for p in sg2_players)}"
                            }
                            subgroup_data.append(sg2_stats)
                    
                    if subgroup_data:
                        subgroup_df = pd.DataFrame(subgroup_data)
                        st.dataframe(subgroup_df, use_container_width=True)
                        
                        # Subgroup balance metrics
                        subgroup1_name = st.session_state.subgroup_names.get('subgroup1', '1 (Lower)')
                        subgroup2_name = st.session_state.subgroup_names.get('subgroup2', '2 (Higher)')
                        
                        sg1_data = [row for row in subgroup_data if subgroup1_name in row['Subgroup']]
                        sg2_data = [row for row in subgroup_data if subgroup2_name in row['Subgroup']]
                        
                        if sg1_data and sg2_data:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**{subgroup1_name} Balance**")
                                sg1_df = pd.DataFrame(sg1_data)
                                sg1_variance = sg1_df['Total Skill'].var()
                                sg1_range = sg1_df['Total Skill'].max() - sg1_df['Total Skill'].min()
                                st.metric("Skill Variance", f"{sg1_variance:.2f}")
                                st.metric("Skill Range", f"{sg1_range}")
                                
                            with col2:
                                st.markdown(f"**{subgroup2_name} Balance**")
                                sg2_df = pd.DataFrame(sg2_data)
                                sg2_variance = sg2_df['Total Skill'].var()
                                sg2_range = sg2_df['Total Skill'].max() - sg2_df['Total Skill'].min()
                                st.metric("Skill Variance", f"{sg2_variance:.2f}")
                                st.metric("Skill Range", f"{sg2_range}")
                
                # Detailed Player Distribution
                st.subheader("👥 Detailed Player Distribution")
                st.info("Players in each group, sorted by skill level (highest to lowest)")
                
                # Create tabs for each group
                if group_player_details:
                    # Create tabs with group display names and skill points
                    tab_labels = []
                    for group_name in group_player_details.keys():
                        display_name = st.session_state.group_names.get(group_name, group_name)
                        # Find matching balance data by display name
                        matching_balance = balance_df[balance_df['Group'] == display_name]
                        if not matching_balance.empty:
                            total_skill = matching_balance['Total Skill'].iloc[0]
                            tab_labels.append(f"{display_name} ({total_skill} pts)")
                        else:
                            tab_labels.append(display_name)
                    
                    group_tabs = st.tabs(tab_labels)
                    
                    for tab, (group_name, players_df) in zip(group_tabs, group_player_details.items()):
                        with tab:
                            # Group statistics - use display name to find balance data
                            display_name = st.session_state.group_names.get(group_name, group_name)
                            group_stats = next((x for x in balance_data if x['Group'] == display_name), None)
                            
                            if group_stats:
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total Players", group_stats['Players'])
                                with col2:
                                    st.metric("Males/Females", f"{group_stats['Males']}/{group_stats['Females']}")
                                with col3:
                                    st.metric("Average Skill", group_stats['Avg Skill'])
                                with col4:
                                    st.metric("Total Skill Points", group_stats['Total Skill'])
                                
                                # Player list with details
                                st.markdown("**Players:**")
                                
                                # Show subgroup breakdown if available
                                if hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups and group_name in st.session_state.detailed_groups:
                                    subgroups = st.session_state.detailed_groups[group_name]
                                    
                                    # Subgroup 1
                                    if subgroups['subgroup1']['players']:
                                        subgroup1_name = st.session_state.subgroup_names.get('subgroup1', '1 (Lower)')
                                        st.markdown(f"***🔽 {subgroup1_name} ({len(subgroups['subgroup1']['players'])} players)***")
                                        for idx, player in enumerate(subgroups['subgroup1']['players'], 1):
                                            gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                            skill_stars = "⭐" * min(player['skill_level'], 5)
                                            st.write(f"  {idx}. {gender_icon} **{player['name']}** (Skill: {player['skill_level']} {skill_stars}) - {player['email']}")
                                    
                                    # Subgroup 2
                                    if subgroups['subgroup2']['players']:
                                        subgroup2_name = st.session_state.subgroup_names.get('subgroup2', '2 (Higher)')
                                        st.markdown(f"***🔼 {subgroup2_name} ({len(subgroups['subgroup2']['players'])} players)***")
                                        for idx, player in enumerate(subgroups['subgroup2']['players'], 1):
                                            gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                            skill_stars = "⭐" * min(player['skill_level'], 10)
                                            st.write(f"  {idx}. {gender_icon} **{player['name']}** (Skill: {player['skill_level']} {skill_stars}) - {player['email']}")
                                else:
                                    # Regular display without subgroups
                                    for idx, (_, player) in enumerate(players_df.iterrows(), 1):
                                        gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                        skill_stars = "⭐" * min(player['skill_level'], 10)
                                        st.write(f"{idx}. {gender_icon} **{player['name']}** (Skill: {player['skill_level']} {skill_stars}) - {player['email']}")
                            else:
                                st.warning(f"No balance data found for {display_name}")
                
                # Summary statistics
                st.divider()
                st.subheader("📈 Balance Summary")
                
                if len(balance_data) >= 6:
                    total_players = sum(stats['Players'] for stats in balance_data)
                    total_males = sum(stats['Males'] for stats in balance_data)
                    total_females = sum(stats['Females'] for stats in balance_data)
                    total_skill = sum(stats['Total Skill'] for stats in balance_data)
                    avg_group_skill = total_skill / 6
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Tournament Players", total_players, "Target: 60")
                    with col2:
                        st.metric("Gender Distribution", f"{total_males}M / {total_females}F")
                    with col3:
                        st.metric("Target Group Skill", f"{avg_group_skill:.1f}", "All groups should be close to this")
                    
                    # Balance quality assessment
                    max_skill_diff = max(stats['Total Skill'] for stats in balance_data) - min(stats['Total Skill'] for stats in balance_data)
                    
                    if max_skill_diff <= 5:
                        st.success("✅ Excellent balance! Groups are very evenly matched.")
                    elif max_skill_diff <= 10:
                        st.info("ℹ️ Good balance. Groups are reasonably matched.")
                    elif max_skill_diff <= 15:
                        st.warning("⚠️ Fair balance. Consider re-balancing for better competition.")
                    else:
                        st.error("❌ Poor balance. Re-balancing strongly recommended.")
    else:
        st.info("No players in database. Import some players to get started!")

# --- TAB 2: SETUP GROUPS & PLAYERS ---
elif menu == "Setup Groups & Players":
    st.header("🎯 Tournament Setup")
    st.markdown("Configure your tournament groups and add all participants.")
    
    # Group Names Setup
    st.subheader("🏷️ Group Names Configuration")
    st.info("Give meaningful names to your groups (e.g., 'Team Thunder', 'Eagles Squad', etc.)")
    
    col1, col2, col3 = st.columns(3)
    
    # Display group name inputs in columns
    group_items = list(st.session_state.group_names.items())
    for i, (group_key, current_name) in enumerate(group_items):
        col = [col1, col2, col3][i % 3]
        with col:
            # Extract the letter from the group key for display (e.g., "Group A" -> "A")
            group_letter = group_key.split()[-1] if ' ' in group_key else group_key
            new_name = st.text_input(f"{group_key} Name:", value=current_name, key=f"group_name_{group_key}")
            if new_name.strip() and new_name != current_name:
                # Update group name and transfer data
                old_key = group_key
                st.session_state.group_names[old_key] = new_name
                
                # Update groups dictionary with new name if it exists
                if hasattr(st.session_state, 'groups') and st.session_state.groups is not None:
                    if old_key in st.session_state.groups:
                        st.session_state.groups[new_name] = st.session_state.groups.pop(old_key)
                
                # Update standings dataframe if it exists
                if hasattr(st.session_state, 'standings') and st.session_state.standings is not None:
                    if old_key in st.session_state.standings.index:
                        st.session_state.standings = st.session_state.standings.rename(index={old_key: new_name})
                
                # Auto-save configuration changes
                auto_save()
    
    # Subgroup Names Configuration
    st.subheader("🏷️ Subgroup Names Configuration")
    st.info("Define names for subgroups used in 'Skill-Level Subgroups' balance strategy (e.g., 'Defenders', 'Attackers' or 'Juniors', 'Seniors')")
    
    # Initialize subgroup names if not exists
    if 'subgroup_names' not in st.session_state:
        st.session_state.subgroup_names = {
            'subgroup1': '1 (Lower)',
            'subgroup2': '2 (Higher)'
        }
    
    col1, col2 = st.columns(2)
    with col1:
        subgroup1_name = st.text_input(
            "Subgroup 1 Name (Lower Skills):", 
            value=st.session_state.subgroup_names['subgroup1'], 
            key="subgroup1_name",
            help="This name will be used for the lower skill subgroup across all groups"
        )
        if subgroup1_name.strip() and subgroup1_name != st.session_state.subgroup_names['subgroup1']:
            st.session_state.subgroup_names['subgroup1'] = subgroup1_name.strip()
            auto_save()  # Auto-save subgroup name changes
    
    with col2:
        subgroup2_name = st.text_input(
            "Subgroup 2 Name (Higher Skills):", 
            value=st.session_state.subgroup_names['subgroup2'], 
            key="subgroup2_name",
            help="This name will be used for the higher skill subgroup across all groups"
        )
        if subgroup2_name.strip() and subgroup2_name != st.session_state.subgroup_names['subgroup2']:
            st.session_state.subgroup_names['subgroup2'] = subgroup2_name.strip()
            auto_save()  # Auto-save subgroup name changes

    # Save confirmation section
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("💾 Save All Names Configuration", type="primary", use_container_width=True):
            auto_save()
            st.success("✅ All group and subgroup names saved successfully!")
            st.balloons()

    st.divider()
    
    # Players Setup
    st.subheader("👥 Players Configuration")
    st.info("Add 10 players to each group. You can copy-paste names or enter them manually.")
    
    # Create tabs for each group - use existing groups only
    existing_groups = [(key, name) for key, name in st.session_state.group_names.items() if key in st.session_state.groups]
    if not existing_groups:
        st.error("No groups configured. Please set up groups first.")
        st.stop()
    
    group_tabs = st.tabs([name for key, name in existing_groups])
    
    for i, tab in enumerate(group_tabs):
        group_key, group_name = existing_groups[i]
        
        with tab:
            st.markdown(f"### Players for {group_name}")
            
            # Option 1: Bulk input
            with st.expander("📋 Bulk Add Players (Recommended)"):
                bulk_text = st.text_area(
                    "Enter all 10 players (one per line or comma-separated):",
                    value="\n".join(st.session_state.groups.get(group_name, [])),
                    height=200,
                    key=f"bulk_{i}"
                )
                
                if st.button(f"Update {group_name} Players", key=f"bulk_btn_{i}"):
                    # Parse input - handle both newline and comma separation
                    if "\n" in bulk_text:
                        players = [p.strip() for p in bulk_text.split("\n") if p.strip()]
                    else:
                        players = [p.strip() for p in bulk_text.split(",") if p.strip()]
                    
                    # Ensure exactly 10 players
                    players = players[:10]  # Take first 10
                    while len(players) < 10:
                        players.append(f"Player {len(players)+1}")
                    
                    st.session_state.groups[group_name] = players
                    st.success(f"Updated {len(players)} players for {group_name}!")
                    st.rerun()
            
            # Option 2: Individual input fields
            with st.expander("✏️ Edit Individual Players"):
                current_players = st.session_state.groups.get(group_name, [f"Player {j+1}" for j in range(10)])
                updated_players = []
                
                col_a, col_b = st.columns(2)
                for j in range(10):
                    col = col_a if j < 5 else col_b
                    with col:
                        player_name = st.text_input(
                            f"Player {j+1}:",
                            value=current_players[j] if j < len(current_players) else f"Player {j+1}",
                            key=f"player_{i}_{j}"
                        )
                        updated_players.append(player_name.strip() or f"Player {j+1}")
                
                if st.button(f"Save Individual Changes for {group_name}", key=f"individual_btn_{i}"):
                    st.session_state.groups[group_name] = updated_players
                    st.success(f"Saved individual player changes for {group_name}!")
                    st.rerun()
            
            # Current players preview
            st.markdown("**Current Players:**")
            current_list = st.session_state.groups.get(group_name, [])
            if current_list:
                for idx, player in enumerate(current_list, 1):
                    st.write(f"{idx}. {player}")
            else:
                st.write("No players added yet.")
    
    # Tournament Status
    st.divider()
    st.subheader("📊 Tournament Status")
    total_players = sum(len(players) for players in st.session_state.groups.values())
    st.metric("Total Players Registered", total_players, f"Target: 60")
    
    if total_players == 60:
        st.success("✅ Tournament setup complete! All groups have 10 players each.")
        st.balloons()
    elif total_players < 60:
        st.warning(f"⚠️ Need {60-total_players} more players to complete setup.")
    else:
        st.error(f"❌ Too many players! Remove {total_players-60} players.")

# --- TAB 3: TEAM DETAILS ---
elif menu == "Team Details":
    st.header("👥 Team Details & Subgroup Breakdown")
    st.markdown("Detailed view of all teams with player distribution")
    
    # Debug info at top (can be hidden with expander)
    with st.expander("🔧 Debug Info", expanded=False):
        st.write("**Groups exist:**", bool(st.session_state.groups))
        st.write("**Groups have players:**", any(st.session_state.groups.values()) if st.session_state.groups else False)
        st.write("**Detailed groups exist:**", hasattr(st.session_state, 'detailed_groups'))
        if hasattr(st.session_state, 'detailed_groups'):
            st.write("**Detailed groups populated:**", bool(st.session_state.detailed_groups))
            if st.session_state.detailed_groups:
                st.write("**Detailed groups keys:**", list(st.session_state.detailed_groups.keys()))
    
    if not st.session_state.groups or not any(st.session_state.groups.values()):
        st.info("📝 No teams have been created yet. Please go to 'Player Import & Auto-Balance' to create teams first.")
    else:
        # Check if subgroup data exists
        has_subgroups = hasattr(st.session_state, 'detailed_groups') and st.session_state.detailed_groups
        
        if has_subgroups:
            st.success("🎯 **Skill-Level Subgroups Active** - Teams are organized by skill ranges")
            
            # More prominent subgroup info
            subgroup1_name = st.session_state.subgroup_names.get('subgroup1', '1 (Lower)')
            subgroup2_name = st.session_state.subgroup_names.get('subgroup2', '2 (Higher)')
            
            st.info(f"📋 **Your Subgroups:** {subgroup1_name} and {subgroup2_name}")
            
            # Subgroup summary
            st.subheader("📊 Subgroup Overview")
            subgroup_summary = []
            
            for group_name, subgroups in st.session_state.detailed_groups.items():
                sg1_data = subgroups['subgroup1']
                sg2_data = subgroups['subgroup2']
                
                # Use custom group name for display
                display_group_name = st.session_state.group_names.get(group_name, group_name)
                
                summary = {
                    'Group': display_group_name,
                    f'{subgroup1_name} Players': len(sg1_data['players']),
                    f'{subgroup1_name} Males': sg1_data['male_count'],
                    f'{subgroup1_name} Females': sg1_data['female_count'],
                    f'{subgroup2_name} Players': len(sg2_data['players']),
                    f'{subgroup2_name} Males': sg2_data['male_count'], 
                    f'{subgroup2_name} Females': sg2_data['female_count'],
                    'Total Players': len(sg1_data['players']) + len(sg2_data['players'])
                }
                subgroup_summary.append(summary)
            
            # Display subgroup summary table
            summary_df = pd.DataFrame(subgroup_summary)
            st.dataframe(summary_df, use_container_width=True)
            
            # Detailed team breakdown
            st.subheader("🔍 Detailed Team Breakdown by Subgroups")
            st.info(f"Click on each team tab to see players organized by {subgroup1_name} and {subgroup2_name}")
            
            # Create tabs for each group using custom names
            group_display_names = [st.session_state.group_names.get(group_name, group_name) for group_name in st.session_state.detailed_groups.keys()]
            group_tabs = st.tabs(group_display_names)
            
            for tab, (group_name, subgroups) in zip(group_tabs, st.session_state.detailed_groups.items()):
                with tab:
                    display_group_name = st.session_state.group_names.get(group_name, group_name)
                    st.markdown(f"### {display_group_name} - Complete Roster")
                    
                    # Group statistics
                    total_players = len(subgroups['subgroup1']['players']) + len(subgroups['subgroup2']['players'])
                    total_males = subgroups['subgroup1']['male_count'] + subgroups['subgroup2']['male_count']
                    total_females = subgroups['subgroup1']['female_count'] + subgroups['subgroup2']['female_count']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Players", total_players)
                    with col2:
                        st.metric("Males", total_males)
                    with col3:
                        st.metric("Females", total_females)
                    
                    # Subgroup breakdown with enhanced display
                    st.markdown("---")
                    st.markdown(f"### 🎯 Subgroup Organization")
                    col1, col2 = st.columns(2)
                    
                    # Subgroup 1
                    with col1:
                        st.markdown(f"#### 🔽 {subgroup1_name}")
                        sg1_players = subgroups['subgroup1']['players']
                        if sg1_players:
                            sg1_metrics_col1, sg1_metrics_col2 = st.columns(2)
                            with sg1_metrics_col1:
                                st.metric("Players", len(sg1_players))
                                st.metric("Males", subgroups['subgroup1']['male_count'])
                            with sg1_metrics_col2:
                                st.metric("Females", subgroups['subgroup1']['female_count'])
                            
                            st.markdown("**🏸 Players:**")
                            for i, player in enumerate(sg1_players, 1):
                                gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                st.write(f"{i}. {gender_icon} **{player['name']}**")
                        else:
                            st.info(f"No players in {subgroup1_name}")
                    
                    # Subgroup 2
                    with col2:
                        st.markdown(f"#### 🔼 {subgroup2_name}")
                        sg2_players = subgroups['subgroup2']['players']
                        if sg2_players:
                            sg2_metrics_col1, sg2_metrics_col2 = st.columns(2)
                            with sg2_metrics_col1:
                                st.metric("Players", len(sg2_players))
                                st.metric("Males", subgroups['subgroup2']['male_count'])
                            with sg2_metrics_col2:
                                st.metric("Females", subgroups['subgroup2']['female_count'])
                            
                            st.markdown("**🏸 Players:**")
                            for i, player in enumerate(sg2_players, 1):
                                gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                st.write(f"{i}. {gender_icon} **{player['name']}**")
                        else:
                            st.info(f"No players in {subgroup2_name}")
        
        else:
            st.info("🎯 **Standard Groups** - Teams created without skill-level subgroups")
            
            # Add instructions for getting subgroups
            with st.expander("💡 Want to see teams organized by skill subgroups?", expanded=False):
                st.markdown("""
                To see players organized by skill subgroups:
                1. Go to **'Player Import & Auto-Balance'** tab
                2. Select **'Skill-Level Subgroups'** balance strategy
                3. Configure your skill ranges and subgroup names
                4. Create balanced groups
                5. Return to this page to see subgroup organization
                """)
            
            # Standard group display
            st.subheader("👥 Team Roster")
            
            # Group summary
            group_summary = []
            for group_name, players in st.session_state.groups.items():
                if players:
                    # Get player details from database
                    group_players_df = st.session_state.player_database[
                        st.session_state.player_database['name'].isin(players)
                    ]
                    
                    if not group_players_df.empty:
                        summary = {
                            'Group': st.session_state.group_names.get(group_name, group_name),
                            'Total Players': len(group_players_df),
                            'Males': len(group_players_df[group_players_df['gender'] == 'M']),
                            'Females': len(group_players_df[group_players_df['gender'] == 'F'])
                        }
                        group_summary.append(summary)
            
            if group_summary:
                summary_df = pd.DataFrame(group_summary)
                st.dataframe(summary_df, use_container_width=True)
            
            # Detailed team breakdown
            st.subheader("🔍 Detailed Team Breakdown")
            
            group_tabs = st.tabs([st.session_state.group_names.get(group_name, group_name) for group_name in st.session_state.groups.keys()])
            
            for tab, (group_name, players) in zip(group_tabs, st.session_state.groups.items()):
                with tab:
                    display_group_name = st.session_state.group_names.get(group_name, group_name)
                    st.markdown(f"### {display_group_name} - Complete Roster")
                    
                    if players:
                        # Get player details
                        group_players_df = st.session_state.player_database[
                            st.session_state.player_database['name'].isin(players)
                        ]
                        
                        if not group_players_df.empty:
                            # Group statistics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Players", len(group_players_df))
                            with col2:
                                males = len(group_players_df[group_players_df['gender'] == 'M'])
                                st.metric("Males", males)
                            with col3:
                                females = len(group_players_df[group_players_df['gender'] == 'F'])
                                st.metric("Females", females)
                            
                            # Player list
                            st.markdown("#### 📋 Players")
                            
                            for i, (_, player) in enumerate(group_players_df.iterrows(), 1):
                                gender_icon = "👨" if player['gender'] == 'M' else "👩"
                                st.write(f"{i}. {gender_icon} **{player['name']}** - {player['email']}")
                        else:
                            st.warning("No player details found in database")
                    else:
                        st.info("No players assigned to this group")
        
        # Export functionality
        st.divider()
        st.subheader("📥 Export Team Details")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Export Team Summary"):
                if has_subgroups and subgroup_summary:
                    summary_csv = pd.DataFrame(subgroup_summary).to_csv(index=False)
                    st.download_button(
                        label="💾 Download Subgroup Summary CSV",
                        data=summary_csv,
                        file_name="team_subgroup_summary.csv",
                        mime="text/csv"
                    )
                elif group_summary:
                    summary_csv = pd.DataFrame(group_summary).to_csv(index=False)
                    st.download_button(
                        label="💾 Download Team Summary CSV",
                        data=summary_csv,
                        file_name="team_summary.csv",
                        mime="text/csv"
                    )
        
        with col2:
            if st.button("👥 Export Detailed Roster"):
                detailed_roster = []
                
                if has_subgroups:
                    subgroup1_name = st.session_state.subgroup_names.get('subgroup1', '1 (Lower)')
                    subgroup2_name = st.session_state.subgroup_names.get('subgroup2', '2 (Higher)')
                    
                    for group_name, subgroups in st.session_state.detailed_groups.items():
                        display_group_name = st.session_state.group_names.get(group_name, group_name)
                        for sg_type, sg_data, sg_name in [('subgroup1', subgroups['subgroup1'], subgroup1_name), ('subgroup2', subgroups['subgroup2'], subgroup2_name)]:
                            for player in sg_data['players']:
                                detailed_roster.append({
                                    'Group': display_group_name,
                                    'Subgroup': sg_name,
                                    'Player': player['name'],
                                    'Gender': player['gender'],
                                    'Email': player.get('email', '')
                                })
                else:
                    for group_name, players in st.session_state.groups.items():
                        group_players_df = st.session_state.player_database[
                            st.session_state.player_database['name'].isin(players)
                        ]
                        for _, player in group_players_df.iterrows():
                            detailed_roster.append({
                                'Group': group_name,
                                'Subgroup': 'All',
                                'Player': player['name'],
                                'Gender': player['gender'],
                                'Email': player['email']
                            })
                
                if detailed_roster:
                    roster_csv = pd.DataFrame(detailed_roster).to_csv(index=False)
                    st.download_button(
                        label="💾 Download Detailed Roster CSV",
                        data=roster_csv,
                        file_name="detailed_team_roster.csv",
                        mime="text/csv"
                    )

# --- TAB 4: MATCH SCHEDULE ---
elif menu == "Match Schedule":
    st.header("📅 Match Schedule Generator")
    st.markdown("Create optimized tournament schedule based on available courts and time slots.")
    
    # Initialize schedule state
    if 'tournament_schedule' not in st.session_state:
        st.session_state.tournament_schedule = []
    if 'schedule_config' not in st.session_state:
        st.session_state.schedule_config = {
            'courts': 4,
            'match_duration': 25,
            'break_duration': 5,
            'start_time': '09:00',
            'end_time': '18:00',
            'dates': []
        }
    
    # Check if groups are set up
    if not st.session_state.groups or not any(st.session_state.groups.values()):
        st.warning("⚠️ Please set up groups first in the 'Setup Groups & Players' tab before creating schedules.")
        st.stop()
    
    # Schedule Configuration
    st.subheader("⚙️ Tournament Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        num_courts = st.number_input(
            "Number of Courts Available:",
            min_value=1,
            max_value=20,
            value=st.session_state.schedule_config['courts'],
            help="Total badminton courts available for the tournament"
        )
        st.session_state.schedule_config['courts'] = num_courts
    
    with col2:
        match_duration = st.number_input(
            "Match Duration (minutes):",
            min_value=15,
            max_value=60,
            value=st.session_state.schedule_config['match_duration'],
            help="Duration of each doubles match including setup"
        )
        st.session_state.schedule_config['match_duration'] = match_duration
    
    with col3:
        break_duration = st.number_input(
            "Break Between Matches (minutes):",
            min_value=0,
            max_value=30,
            value=st.session_state.schedule_config['break_duration'],
            help="Rest time between consecutive matches"
        )
        st.session_state.schedule_config['break_duration'] = break_duration
    
    # Time Configuration
    col1, col2 = st.columns(2)
    
    with col1:
        start_time = st.time_input(
            "Tournament Start Time:",
            value=pd.to_datetime(st.session_state.schedule_config['start_time']).time(),
            help="Daily tournament start time"
        )
        st.session_state.schedule_config['start_time'] = start_time.strftime('%H:%M')
    
    with col2:
        end_time = st.time_input(
            "Tournament End Time:",
            value=pd.to_datetime(st.session_state.schedule_config['end_time']).time(),
            help="Daily tournament end time"
        )
        st.session_state.schedule_config['end_time'] = end_time.strftime('%H:%M')
    
    # Date Configuration
    st.subheader("📅 Tournament Dates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        tournament_start_date = st.date_input(
            "Tournament Start Date:",
            value=pd.Timestamp.now().date(),
            help="First day of the tournament"
        )
    
    with col2:
        tournament_days = st.number_input(
            "Number of Tournament Days:",
            min_value=1,
            max_value=14,
            value=3,
            help="Total days for the tournament"
        )
    
    # Generate date list
    tournament_dates = [tournament_start_date + pd.Timedelta(days=i) for i in range(tournament_days)]
    st.session_state.schedule_config['dates'] = [date.strftime('%Y-%m-%d') for date in tournament_dates]
    
    # Display tournament overview
    st.subheader("📊 Tournament Overview")
    
    # Calculate match requirements for round-based scheduling
    num_groups = len([g for g in st.session_state.groups.values() if g])
    
    if num_groups < 2:
        st.warning("⚠️ Need at least 2 groups to generate schedule.")
        st.stop()
    
    # In round-robin, each group plays every other group once
    total_rounds = num_groups - 1 if num_groups % 2 == 0 else num_groups
    matches_per_round = (num_groups // 2) if num_groups % 2 == 0 else ((num_groups - 1) // 2)
    matches_per_clash = 5  # 5 doubles matches per group clash
    total_matches = total_rounds * matches_per_round * matches_per_clash
    
    # Calculate time requirements for round-based scheduling
    total_match_time = match_duration + break_duration
    
    # Convert time objects to datetime for calculation
    from datetime import datetime, timedelta
    
    # Create datetime objects for today with the specified times
    today = pd.Timestamp.now().date()
    start_datetime = pd.to_datetime(f"{today} {start_time}")
    end_datetime = pd.to_datetime(f"{today} {end_time}")
    
    daily_duration = end_datetime - start_datetime
    daily_minutes = daily_duration.total_seconds() / 60
    
    # Calculate capacity based on available courts and simultaneous play
    courts_needed_per_round = matches_per_round * matches_per_clash  # Total matches in a round
    
    if num_courts >= courts_needed_per_round:
        # All matches in a round can be played simultaneously
        round_duration = total_match_time  # Just one match duration since all are parallel
        rounds_per_day = int(daily_minutes // round_duration)
        total_tournament_capacity = rounds_per_day * tournament_days * matches_per_round * matches_per_clash
    else:
        # Not enough courts - some matches will be sequential
        # Calculate how many parallel "batches" we can run
        batches_per_round = (courts_needed_per_round + num_courts - 1) // num_courts  # Ceiling division
        round_duration = batches_per_round * total_match_time
        rounds_per_day = int(daily_minutes // round_duration)
        total_tournament_capacity = rounds_per_day * tournament_days * matches_per_round * matches_per_clash
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Groups", num_groups)
    with col2:
        st.metric("Tournament Rounds", total_rounds)
    with col3:
        st.metric("Total Matches", total_matches)
    with col4:
        st.metric("Tournament Capacity", total_tournament_capacity)
    
    # Add detailed calculation breakdown for round-based scheduling
    with st.expander("📊 Detailed Round-Based Capacity Breakdown"):
        col1, col2, col3 = st.columns(3)
        
        # Calculate derived values for display
        rounds_per_day = int(daily_minutes // (total_match_time if num_courts >= courts_needed_per_round else 
                                               ((courts_needed_per_round + num_courts - 1) // num_courts) * total_match_time))
        batches_per_round = (courts_needed_per_round + num_courts - 1) // num_courts if num_courts < courts_needed_per_round else 1
        
        with col1:
            st.metric("Daily Hours", f"{daily_minutes/60:.1f}")
            st.metric("Match + Break Time", f"{total_match_time} min")
            st.metric("Rounds per Day", rounds_per_day)
        
        with col2:
            st.metric("Courts Available", num_courts)
            st.metric("Courts Needed per Round", courts_needed_per_round)
            st.metric("Tournament Days", tournament_days)
        
        with col3:
            st.metric("Matches per Round", matches_per_round * matches_per_clash)
            st.metric("Batches per Round", batches_per_round)
            st.metric("Court Utilization", f"{min(100, (courts_needed_per_round/num_courts)*100):.1f}%")
        
        # Capacity breakdown explanation
        if num_courts >= courts_needed_per_round:
            st.success(f"""
            ✅ **Optimal Scheduling**: All {courts_needed_per_round} matches in each round can play simultaneously!
            - Round duration: {total_match_time} minutes (all matches parallel)
            - Rounds per day: {rounds_per_day}
            - Total capacity: {rounds_per_day * tournament_days * matches_per_round * matches_per_clash} matches
            """)
        else:
            st.info(f"""
            ℹ️ **Sequential Scheduling**: {courts_needed_per_round} matches need to be split into {batches_per_round} batches.
            - Each round takes {batches_per_round * total_match_time} minutes ({batches_per_round} batches)
            - Rounds per day: {rounds_per_day}
            - Total capacity: {rounds_per_day * tournament_days * matches_per_round * matches_per_clash} matches
            """)
    
    # Capacity analysis
    if total_matches <= total_tournament_capacity:
        st.success(f"✅ Schedule feasible! {total_tournament_capacity - total_matches} extra slots available.")
    else:
        shortage = total_matches - total_tournament_capacity
        st.error(f"❌ Schedule not feasible! Need {shortage} more match slots. Consider adding courts, days, or extending hours.")
    
    st.divider()
    
    # Schedule Generation
    st.subheader("🎯 Generate Schedule")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        schedule_type = st.selectbox(
            "Schedule Type:",
            ["Round Robin (All groups play each other)", "Swiss System", "Custom Bracket"],
            help="Round Robin ensures all groups play each other once"
        )
    
    with col2:
        if st.button("🚀 Generate Schedule", type="primary", disabled=total_matches > total_tournament_capacity):
            if schedule_type == "Round Robin (All groups play each other)":
                with st.spinner("Generating optimized schedule..."):
                    schedule = generate_round_robin_schedule(
                        [st.session_state.group_names.get(key, key) for key in st.session_state.groups.keys()],
                        tournament_dates,
                        start_time,
                        end_time,
                        num_courts,
                        match_duration,
                        break_duration
                    )
                    st.session_state.tournament_schedule = schedule
                    auto_save()
                    st.success("🎉 Schedule generated successfully!")
                    st.rerun()
    
    # Display Generated Schedule
    if st.session_state.tournament_schedule:
        st.divider()
        st.subheader("📋 Generated Tournament Schedule")
        
        # Schedule overview
        schedule_df = pd.DataFrame(st.session_state.tournament_schedule)
        
        # Filter and display options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_date = st.selectbox(
                "View Date:",
                ["All Dates"] + st.session_state.schedule_config['dates'],
                help="Filter schedule by specific date"
            )
        
        with col2:
            selected_court = st.selectbox(
                "View Court:",
                ["All Courts"] + [f"Court {i+1}" for i in range(num_courts)],
                help="Filter schedule by specific court"
            )
        
        with col3:
            view_format = st.selectbox(
                "View Format:",
                ["Table View", "Timeline View", "Court Schedule"],
                help="Different ways to display the schedule"
            )
        
        # Filter schedule
        filtered_schedule = schedule_df.copy()
        
        if selected_date != "All Dates":
            filtered_schedule = filtered_schedule[filtered_schedule['date'] == selected_date]
        
        if selected_court != "All Courts":
            filtered_schedule = filtered_schedule[filtered_schedule['court'] == selected_court]
        
        # Display schedule based on selected format
        if view_format == "Table View":
            if not filtered_schedule.empty:
                # Format for better display
                display_df = filtered_schedule.copy()
                display_df['Match Time'] = display_df['start_time'] + " - " + display_df['end_time']
                display_df = display_df[['date', 'round_number', 'court', 'Match Time', 'group1', 'group2', 'match_number']]
                display_df.columns = ['Date', 'Round', 'Court', 'Time', 'Group 1', 'Group 2', 'Match #']
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No matches found for the selected filters.")
        
        elif view_format == "Timeline View":
            # Group by date and show timeline
            for date in sorted(filtered_schedule['date'].unique()):
                st.markdown(f"### 📅 {date}")
                date_matches = filtered_schedule[filtered_schedule['date'] == date].sort_values('start_time')
                
                for _, match in date_matches.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 3, 2, 1])
                    
                    with col1:
                        st.write(f"**{match['start_time']}**")
                    with col2:
                        st.write(f"{match['group1']} vs {match['group2']}")
                    with col3:
                        st.write(f"*{match['court']}*")
                    with col4:
                        st.write(f"Match {match['match_number']}")
        
        elif view_format == "Court Schedule":
            # Show schedule organized by court
            for court in sorted(filtered_schedule['court'].unique()):
                st.markdown(f"### 🏟️ {court}")
                court_matches = filtered_schedule[filtered_schedule['court'] == court].sort_values(['date', 'start_time'])
                
                for _, match in court_matches.iterrows():
                    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
                    
                    with col1:
                        st.write(f"**{match['date']}**")
                    with col2:
                        st.write(f"{match['start_time']}")
                    with col3:
                        st.write(f"{match['group1']} vs {match['group2']}")
                    with col4:
                        st.write(f"#{match['match_number']}")
        
        # Export functionality
        st.divider()
        st.subheader("📤 Export Schedule")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Export as CSV"):
                csv_data = schedule_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download Schedule CSV",
                    data=csv_data,
                    file_name=f"tournament_schedule_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📋 Copy to Clipboard"):
                schedule_text = schedule_df.to_string(index=False)
                st.code(schedule_text, language="text")
                st.info("Schedule formatted for copying above ☝️")

                st.code(schedule_text, language="text")
                st.info("Schedule formatted for copying above ☝️")

# --- TAB 4: STANDINGS ---
elif menu == "Standings & Qualifiers":
    st.header("🏆 Tournament Standings & Qualification")
    
    # Check if we have any match data (individual matches or legacy clash data)
    individual_matches = st.session_state.get('individual_matches', [])
    legacy_data = st.session_state.get('tournament_data', {})
    
    if not individual_matches and not legacy_data:
        st.info("📝 No tournament matches recorded yet. Please record some matches first!")
        st.info("💡 Go to **'Record a Clash'** to start recording individual match results.")
    else:
        # Use appropriate calculation method based on available data
        if individual_matches:
            standings_df = calculate_standings_from_matches()
            st.success(f"📊 Displaying standings from {len(individual_matches)} individual matches")
        else:
            standings_df = calculate_standings()  # Legacy calculation for backward compatibility
            st.info("📊 Displaying standings from legacy clash data")
        
        if not standings_df.empty:
            st.subheader("📊 Current Standings")
            # Display standings table with better formatting
            standings_display = standings_df.copy()
            
            # Format the display based on data type
            if 'Rank' in standings_display.columns:
                standings_display['Rank'] = standings_display['Rank'].astype(str) + '.' 
            
            st.dataframe(standings_display, use_container_width=True, hide_index=True)
            
            # Show match summary
            if individual_matches:
                st.subheader("📋 Recent Matches")
                recent_matches = sorted(individual_matches, key=lambda x: x['recorded_at'], reverse=True)[:5]
                
                for match in recent_matches:
                    winner_display = st.session_state.group_names.get(match['winner'], match['winner'])
                    loser = match['team1'] if match['winner'] == match['team2'] else match['team2'] 
                    loser_display = st.session_state.group_names.get(loser, loser)
                    
                    st.write(f"🏆 **{winner_display}** def. {loser_display} {match['score_display']} ({match['match_points']} pts) - {match['recorded_at'][:19]}")
            
            # Qualification analysis (adapted for individual matches)
            st.subheader("🎯 Qualification Analysis")
            
            total_teams = len(standings_df)
            if total_teams >= 4:
                # Top 2 teams qualify
                qualified_teams = standings_display.head(2)
                eliminated_teams = standings_display.tail(total_teams - 2)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.success("✅ **QUALIFIED TEAMS**")
                    for idx, team in qualified_teams.iterrows():
                        if individual_matches:
                            st.write(f"🥇 **{team['Team']}** - {team['Points']} pts ({team['Wins']}-{team['Losses']} record)")
                        else:
                            st.write(f"🥇 **{team['Team']}** - {team['Points']} pts ({team['Clash Wins']}CW-{team['Clash Losses']}CL)")
                
                with col2:
                    st.error("❌ **ELIMINATED TEAMS**")
                    for idx, team in eliminated_teams.iterrows():
                        if individual_matches:
                            st.write(f"💔 **{team['Team']}** - {team['Points']} pts ({team['Wins']}-{team['Losses']} record)")
                        else:
                            st.write(f"💔 **{team['Team']}** - {team['Points']} pts ({team['Clash Wins']}CW-{team['Clash Losses']}CL)")
                        
                # Tournament completion check (adapted for individual match system)
                if individual_matches:
                    total_matches = len(individual_matches)
                    st.info(f"📊 **Tournament Progress:** {total_matches} individual matches recorded")
                    
                    # Check if we have a clear winner 
                    top_team = standings_display.iloc[0]
                    if top_team['Wins'] >= 3:  # Threshold for declaring winner
                        st.balloons()
                        st.success(f"🎉 **POTENTIAL TOURNAMENT LEADER!** {top_team['Team']} is dominating with {top_team['Wins']} wins!")
                else:
                    # Legacy tournament completion check
                    matches_played = sum(len(matches) for matches in legacy_data.values())
                    if matches_played > 0:
                        st.info(f"📊 **Tournament Progress:** {matches_played} clash matches from legacy system")
                    
                # Final rankings display
                st.subheader("🏆 Current Tournament Rankings")
                for idx, team in standings_display.head(6).iterrows():  # Show top 6
                    if idx == 0:
                        st.write(f"🥇 **{team['Team']}** - {team['Points']} points")
                    elif idx == 1:
                        st.write(f"🥈 **{team['Team']}** - {team['Points']} points")
                    elif idx == 2:
                        st.write(f"🥉 **{team['Team']}** - {team['Points']} points")
                    else:
                        st.write(f"#{idx+1} **{team['Team']}** - {team['Points']} points")
            else:
                st.warning("⚠️ Need at least 4 teams for qualification analysis")
        else:
            st.warning("⚠️ No valid tournament data available for standings calculation")
    

# --- TAB 5: RECORD A CLASH ---
elif menu == "Record a Clash":
    # Check if user has permission to record clashes
    if not is_authenticated():
        st.error("🚫 Access Denied. Please login to record clashes.")
        st.stop()
    
    user_role = get_current_user_role()
    if user_role not in ['superuser', 'admin']:
        st.error("🚫 Access Denied. Only administrators can record clashes.")
        st.stop()
    
    st.header("🏸 Record & Manage Individual Matches")
    st.info("💡 **New Simplified Approach**: Record one doubles match at a time with easy player selection and score entry.")
    
    # Tabs for different actions
    if user_role == 'superuser':
        tab1, tab2, tab3 = st.tabs(["🆕 Record Match", "📝 Manage Matches", "📜 Edit History"])
    else:
        tab1, tab2, tab3 = st.tabs(["🆕 Record Match", "👁️ View Results", "🚫 Admin Only"])
    
    with tab1:
        st.subheader("Record New Match")
        record_new_clash()  # This now calls the simplified single match interface
    
    with tab2:
        if user_role == 'superuser':
            st.subheader("Manage Match Records")
            edit_clash_results()  # This now calls the match management interface
        else:
            st.subheader("View Match Results")
            view_clash_results()  # This now shows individual match results
    
    with tab3:
        if user_role == 'superuser':
            st.subheader("Match Edit History")
            show_edit_history()
        else:
            st.error("🚫 Only superusers can view edit history")

# --- TAB 6: MANAGE PLAYERS ---
elif menu == "Manage Players":
    st.header("👥 Quick Player Management")
    st.info("Use this for quick edits. For comprehensive setup, use the 'Setup Groups & Players' tab.")
    
    for group_name, players in st.session_state.groups.items():
        st.subheader(f"📋 {group_name}")
        new_list = st.text_area(
            f"Edit Players (comma-separated):", 
            value=", ".join(players),
            key=f"quick_edit_{group_name}"
        )
        
        if st.button(f"Update {group_name}", key=f"quick_update_{group_name}"):
            updated_players = [p.strip() for p in new_list.split(",") if p.strip()]
            # Ensure exactly 10 players
            updated_players = updated_players[:10]  # Take first 10
            while len(updated_players) < 10:
                updated_players.append(f"Player {len(updated_players)+1}")
            
            st.session_state.groups[group_name] = updated_players
            st.success(f"Updated {group_name}!")
            st.rerun()

    # Data Export Section
    st.divider()
    st.subheader("📥 Export Tournament Data")
    st.info("Export your tournament data to CSV files for external analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Standings"):
            if not st.session_state.standings.empty:
                standings_csv = st.session_state.standings.to_csv()
                st.download_button(
                    label="💾 Download Standings CSV",
                    data=standings_csv,
                    file_name="tournament_standings.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No standings data to export")
    
    with col2:
        if st.button("👥 Export Players"):
            if not st.session_state.player_database.empty:
                players_csv = st.session_state.player_database.to_csv(index=False)
                st.download_button(
                    label="💾 Download Players CSV",
                    data=players_csv,
                    file_name="tournament_players.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No player data to export")
    
    with col3:
        if st.button("🏆 Export Groups"):
            if st.session_state.groups:
                # Create a CSV with group assignments
                group_data = []
                for group_name, players in st.session_state.groups.items():
                    for i, player in enumerate(players, 1):
                        group_data.append({
                            'Group': st.session_state.group_names.get(group_name, group_name),
                            'Position': i,
                            'Player': player
                        })
                
                groups_df = pd.DataFrame(group_data)
                groups_csv = groups_df.to_csv(index=False)
                st.download_button(
                    label="💾 Download Groups CSV",
                    data=groups_csv,
                    file_name="tournament_groups.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No group data to export")

# --- TAB 8: USER MANAGEMENT ---
elif menu == "User Management":
    st.header("👥 User Management")
    
    # Only superuser can access this page
    if get_current_user_role() != 'superuser':
        st.error("🚫 Access Denied. Only superusers can manage users.")
        st.stop()
    
    tab1, tab2 = st.tabs(["👤 View Users", "➕ Create Admin User"])
    
    with tab1:
        st.subheader("📋 Current Users")
        
        if st.session_state.users:
            users_data = []
            for username, user_info in st.session_state.users.items():
                users_data.append({
                    'Username': username,
                    'Role': user_info['role'].title(),
                    'Created By': user_info.get('created_by', 'Unknown'),
                    'Created At': user_info.get('created_at', 'Unknown')[:19] if user_info.get('created_at') else 'Unknown'
                })
            
            users_df = pd.DataFrame(users_data)
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            
            # Delete user section (only non-superusers can be deleted)
            st.subheader("🗑️ Delete User")
            deletable_users = [user for user, info in st.session_state.users.items() 
                             if info['role'] != 'superuser']
            
            if deletable_users:
                user_to_delete = st.selectbox("Select user to delete:", deletable_users)
                if st.button(f"🗑️ Delete User: {user_to_delete}", type="secondary"):
                    if st.session_state.get('confirm_delete', False):
                        del st.session_state.users[user_to_delete]
                        auto_save()  # Save after user deletion
                        st.success(f"User '{user_to_delete}' has been deleted.")
                        st.session_state.confirm_delete = False
                        st.rerun()
                    else:
                        st.session_state.confirm_delete = True
                        st.warning(f"⚠️ Click again to confirm deletion of user '{user_to_delete}'")
            else:
                st.info("No deletable users (only admin users can be deleted, not superusers)")
        else:
            st.info("No users found")
    
    with tab2:
        st.subheader("➕ Create New Admin User")
        
        with st.form("create_admin_form"):
            new_username = st.text_input("Username", help="Choose a unique username")
            new_password = st.text_input("Password", type="password", help="Choose a secure password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            create_admin = st.form_submit_button("👑 Create Admin User")
            
            if create_admin:
                # Validation
                if not new_username or not new_password:
                    st.error("❌ Username and password are required")
                elif new_username in st.session_state.users:
                    st.error(f"❌ Username '{new_username}' already exists")
                elif new_password != confirm_password:
                    st.error("❌ Passwords do not match")
                elif len(new_password) < 4:
                    st.error("❌ Password must be at least 4 characters long")
                else:
                    # Create new admin user
                    st.session_state.users[new_username] = {
                        'password_hash': hash_password(new_password),
                        'role': 'admin',
                        'created_by': get_current_user(),
                        'created_at': datetime.now().isoformat()
                    }
                    auto_save()  # Save user data immediately
                    st.success(f"✅ Admin user '{new_username}' created successfully!")
                    st.info(f"👤 **Username:** {new_username}\\n🔑 **Role:** Admin\\n🎯 **Permissions:** Can record clashes")
                    st.rerun()
        
        # Instructions
        st.markdown("---")
        st.subheader("ℹ️ User Roles & Permissions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🌟 Superuser (You)**
            - Full access to all features
            - Can create/delete admin users
            - Can import players & create teams
            - Can record clashes
            - Can view all reports
            """)
        
        with col2:
            st.markdown("""
            **👑 Admin User**
            - Can record clashes only
            - Cannot create teams or import players
            - Cannot manage other users
            - Can view team details & standings
            """)
        
        st.info("🌐 **Guest/Public Access:** Anyone can view Team Details and Standings & Qualifiers without logging in.")
