# Import Streamlit
import streamlit as st

# File handling and JSON parsing
import os
import orjson

# Data analysis tools
import polars as pl

# String matching
import Levenshtein
from collections import Counter, defaultdict

# Math functions
from math import ceil

# Dates and times
from datetime import datetime

# Helper functions
from helper_functions import correct_cap

def correct_unit_names(unit_rows, list_rows):
    '''Function to correct unit names that differ by a single character within the same faction.'''
    # Map list_id to faction for quick lookup
    list_id_to_faction = {row['list_id']: row['Faction'] for row in list_rows}
    # Group unit names by faction
    faction_units = defaultdict(list)
    for row in unit_rows:
        faction = list_id_to_faction.get(row['list_id'])
        if faction:
            faction_units[faction].append(row['Name'])
    # Find corrections
    name_corrections = {}
    for faction, names in faction_units.items():
        name_counts = Counter(names)
        unique_names = list(name_counts.keys())
        for i, name1 in enumerate(unique_names):
            for name2 in unique_names[i+1:]:
                if Levenshtein.distance(name1, name2) == 1:
                    popular = name1 if name_counts[name1] >= name_counts[name2] else name2
                    less_popular = name2 if popular == name1 else name1
                    name_corrections[(faction, less_popular)] = popular
    # Apply corrections
    for row in unit_rows:
        faction = list_id_to_faction.get(row['list_id'])
        key = (faction, row['Name'])
        if key in name_corrections:
            row['Name'] = name_corrections[key]
    return unit_rows

def correct_option_names(option_rows):
    '''Function to correct option names that differ by a single character within the same unit.'''
    # Group option names by Unit Name
    unit_options = defaultdict(list)
    for row in option_rows:
        unit_options[row['Unit Name']].append(row['Option Name'])
    # Find corrections
    option_corrections = {}
    option_type_corrections = {}
    for unit_name, options in unit_options.items():
        option_counts = Counter(options)
        unique_options = list(option_counts.keys())
        for i, opt1 in enumerate(unique_options):
            for opt2 in unique_options[i+1:]:
                if Levenshtein.distance(opt1, opt2) == 1:
                    popular = opt1 if option_counts[opt1] >= option_counts[opt2] else opt2
                    less_popular = opt2 if popular == opt1 else opt1
                    option_corrections[(unit_name, less_popular)] = popular
    # Update Option Type to match the most popular variant
    for row in option_rows:
        key = (row['Unit Name'], row['Option Name'])
        if key in option_corrections:
            # Find the most common Option Type for the corrected name
            corrected_name = option_corrections[key]
            types = [r['Option Type'] for r in option_rows if r['Unit Name'] == row['Unit Name'] and r['Option Name'] == corrected_name]
            if types:
                most_common_type = Counter(types).most_common(1)[0][0]
                row['Option Name'] = corrected_name
                row['Option Type'] = most_common_type
    return option_rows


# Cached function to load and organise the data
@st.cache_data
def load_and_organise_data(root_folder="data"):
    '''Function to load and organise data from JSON files in the specified root folder.'''
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, root_folder)
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f'The specified path does not exist: {data_dir}')

    list_rows = []
    unit_rows = []
    option_rows = []
    g_ind = 0  # Game index
    l_ind = 0  # List index
    u_ind = 0  # Unit index

    # Loop through all folders and files, process as we read
    for folder_name in sorted(os.listdir(data_dir)):
        folder_path = os.path.join(data_dir, folder_name)
        if os.path.isdir(folder_path):
            tourn_data = []
            for file_name in sorted(os.listdir(folder_path)):
                if file_name.endswith('.json'):
                    file_path = os.path.join(folder_path, file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            data = orjson.loads(f.read())
                            tourn_data.append(data)
                        except orjson.JSONDecodeError:
                            print(f'Skipping invalid JSON: {file_path}')
            if not tourn_data:
                continue
            # Process tournament data
            tourn = tourn_data
            if tourn[0]['type'] == 0:
                tourn_type = 'Teams'
            elif tourn[0]['type'] == 1:
                tourn_type = 'Singles'
            else:
                tourn_type = 'Unknown'

            for game in tourn[1:]:
                army = [correct_cap(game['armyOne']), correct_cap(game['armyTwo'])]
                arm_key = ('armyListOne', 'armyListTwo')
                scores = (game['scoreOne'], game['scoreTwo'])
                if game['firstTurn'] == 0:
                    turn = ('First', 'Second')
                elif game['firstTurn'] == 1:
                    turn = ('Second', 'First')
                else:
                    turn = ('Unknown', 'Unknown')

                for i in range(2):
                    if arm_key[i] in game:
                        is_list = True
                        alist = game[arm_key[i]]
                        list_points = 0
                        magicalness = game[arm_key[i]]['magicalness'] if not isinstance(game[arm_key[i]]['magicalness'], str) else None
                        for unit in alist['units']:
                            num_models = unit.get('models', None)
                            unit_rows.append({
                                'list_id': l_ind,
                                'unit_id': u_ind,
                                'Name': unit['name'],
                                'Category': unit['category'],
                                'Cost': unit['cost'],
                                'Models': num_models,
                                'Score': scores[i],
                            })
                            list_points += unit['cost']
                            for option in unit['options']:
                                option_rows.append({
                                    'list_id': l_ind,
                                    'unit_id': u_ind,
                                    'Unit Name': unit['name'],
                                    'Option Name': option['name'],
                                    'Option Type': option['type'],
                                    'Score': scores[i],
                                })
                            if num_models:
                                for model_count in range(5, 85, 5):
                                    if num_models <= model_count:
                                        model_count = f'{model_count-4}-{model_count} Models'
                                        break
                                option_rows.append({
                                    'list_id': l_ind,
                                    'unit_id': u_ind,
                                    'Unit Name': unit['name'],
                                    'Option Name': model_count,
                                    'Option Type': 'Model Count',
                                    'Score': scores[i],
                                })
                            u_ind += 1
                    else:
                        list_points = None
                        magicalness = None
                        is_list = False

                    list_rows.append({
                        'game_id': g_ind,
                        'list_id': l_ind,
                        'List': is_list,
                        'Faction': army[i],
                        'Opponent': army[1-i],
                        'Score': scores[i],
                        'Turn': turn[i],
                        'Total Points': list_points,
                        'Magicalness': magicalness,
                        'Type': tourn_type,
                        'Tournament Size': tourn[0]['size'],
                        'Start Date': datetime.strptime(tourn[0]['start'], "%Y-%m-%d").date(),
                        'End Date': datetime.strptime(tourn[0]['end'], "%Y-%m-%d").date(),
                    })
                    l_ind += 1
                g_ind += 1
                points = [row['Total Points'] for row in list_rows[-2:] if row['Total Points'] is not None]
                if points:
                    max_points = ceil( max(points) / 100)*100
                    list_rows[-1]['Game Size'] = max_points
                    list_rows[-2]['Game Size'] = max_points
                else:
                    list_rows[-1]['Game Size'] = None
                    list_rows[-2]['Game Size'] = None

    num_games = g_ind

    # Correct unit and option names
    unit_rows = correct_unit_names(unit_rows, list_rows)
    option_rows = correct_option_names(option_rows)

    # Convert to Polars DataFrames
    raw_list_data = pl.DataFrame(list_rows)#.with_columns([
    #     pl.col('Faction').cast(pl.Categorical),
    #     pl.col('Turn').cast(pl.Categorical)
    # ])
    raw_unit_data = pl.DataFrame(unit_rows)
    raw_option_data = pl.DataFrame(option_rows)
    magic_paths = (
        raw_option_data
        .filter(pl.col('Option Type') == 'Path')
        .select('Option Name')
        .unique()
        .to_series()
        .to_list()
    )

    # Return the data
    return raw_list_data, raw_unit_data, raw_option_data, num_games, sorted(magic_paths)