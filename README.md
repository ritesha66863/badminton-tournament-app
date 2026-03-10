# Badminton Tournament Management System

A comprehensive web application built with Streamlit for managing badminton tournaments with advanced auto-balancing capabilities.

## Features

- **Player Import & Management**: Import players via CSV/Excel, bulk text, or manual entry
- **Advanced Auto-Balance**: Create balanced groups with skill-level subgroups
- **Flexible Tournament Structure**: Configure 2-12 groups with custom player counts
- **Match Scheduling**: Generate round-robin schedules with court management
- **Standings & Qualifiers**: Track wins, points, and qualification progress
- **Clash Recording**: Record match results and update standings
- **Data Persistence**: Automatic saving to JSON files

## Live Demo

🎯 [Try the Application](https://your-app-name.streamlit.app)

## Key Capabilities

### Auto-Balance Groups
- **Skill-Level Subgroups**: Configure two skill ranges (e.g., 1-5 and 6-10)
- **Exact Player Counts**: Specify exact number of players per subgroup
- **Multi-Level Balance**: Ensures skill point balance at group, subgroup1, and subgroup2 levels
- **Dynamic Group Count**: Create 2-12 groups based on tournament size

### Tournament Management
- Support for 16-180+ players
- Gender balance considerations
- Skill variance minimization
- Real-time balance quality metrics

## Usage

1. **Import Players**: Add player data with names, emails, skill levels (1-10), and gender
2. **Configure Tournament**: Set number of groups and skill level ranges
3. **Auto-Balance**: Create perfectly balanced groups with optimized skill distribution
4. **Generate Schedule**: Create match schedules with court assignments
5. **Record Results**: Track match outcomes and update standings

## Technical Details

- Built with Streamlit and Pandas
- Advanced algorithms for skill-based player distribution
- Iterative optimization to minimize skill variance
- JSON-based data persistence
- Responsive web interface

## Installation

```bash
pip install -r requirements.txt
streamlit run badminton.py
```

## Contributing

Feel free to submit issues and enhancement requests!
