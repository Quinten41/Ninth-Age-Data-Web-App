# Import Streamlit
import streamlit as st

# File handling and JSON parsing
import os
import orjson

# Data analysis tools
import polars as pl

# Math functions
from math import ceil

# Other utilities
from datetime import datetime
from datetime import date

# Import functions to generate the different pages
from welcome_page import welcome_page
from game_wide_page import game_wide_page
from faction_specific_page import faction_specific_page

# Set Streamlit page layout to wide
#st.set_page_config(layout="wide")

# Display the Ninth Age Logo
st.image('https://bedroombattlefields.com/wp-content/uploads/2021/11/the-ninth-age-1024x479.png')

# Define a list for the factions
faction_keys = ['BH', 'DE', 'DH', 'DL', 'EoS', 'HE', 'ID', 'KoE', 'OK', 'OnG', 'SA', 'SE', 'UD', 'VC', 'VS', 'WDG']
num_faction = len(faction_keys) # Should be 16

lower_to_correct = {key.lower(): key for key in faction_keys} # Dictionary to map lowercase keys to the correct capitalization
def correct_cap(key):
    '''Convert a given key to the correct capitalization as used in faction_keys.

    Args:
        key (str): The key to be converted.

    Returns:
        str: The key in the correct capitalization.
    '''
    return lower_to_correct[key.lower()]

# First load the data into three polars dataframes

# Cached function to load and organise the data
@st.cache_data
def load_and_organise_data(root_folder="data"):
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
                            u_ind += 1
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
                        'Start Date': datetime.strptime(tourn[0]['start'], "%Y-%m-%d"),
                        'End Date': datetime.strptime(tourn[0]['end'], "%Y-%m-%d"),
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
    raw_list_data = pl.DataFrame(list_rows).with_columns([
        pl.col("Faction").cast(pl.Categorical),
        pl.col("Turn").cast(pl.Categorical)
    ])
    raw_unit_data = pl.DataFrame(unit_rows)
    raw_option_data = pl.DataFrame(option_rows)
    magic_paths = (
        raw_option_data
        .filter(pl.col("Option Type") == "Path")
        .select("Option Name")
        .unique()
        .to_series()
        .to_list()
    )
    return raw_list_data, raw_unit_data, raw_option_data, num_games, magic_paths

# get the dataframes
with st.spinner('Loading data...'):
    raw_list_data, raw_unit_data, raw_option_data, tnum_games, magic_paths = load_and_organise_data()

# Add a sidebar for filtering and page selection
with st.sidebar:
    st.title('Filters & Navigation')
    st.header('Data Filters')
    # Date range slider
    start_date, end_date = st.slider(
        "Select Date Range",
        value=(date(2024, 1, 1), date.today()),
        format="YYYY-MM-DD"
    )

    # Inject custom CSS to change selectbox format
    st.markdown(
        """
        <style>
            div[data-baseweb="select"] > div:first-child {
                background-color: #f2f2f2;  /* change to desired background */
                color: #254C73;  /* change the selected text's colour */
            }

            ul[data-testid="stSelectboxVirtualDropdown"]>div>div>li {
                color: #254C73; /* change the dropdown text's colour */
            }

            /* Attempt to style the dropdown arrow */
            .stSelectbox [data-baseweb="select"] svg {
                color: #254C73 !important;  /* Change to your desired color */
                fill: #254C73 !important;
            }
            /* Change the cursor color in input and textarea fields */
            input, textarea {
                caret-color: #254C73 !important;
            }

            ul[data-testid="stSelectboxVirtualDropdown"]>div>div>li[aria-selected="true"] {
                background: #DEAA46;  /* change the highlighting background */
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Choose whether or not to select by list size
    select_by_list_size = st.checkbox('Filter by List Size (in points)', value=False)
    st.caption('If unchecked, all games will be included regardless of list size. \
            Please note that not all games have list size data, so checking this box will \
            exclude games from the dataset regardless of the resulting selection.')
    if select_by_list_size:
        # Minimum and maximum list size slider
        min_list_size, max_list_size = st.slider(
            "Select List Size Range (in points)",
            min_value=3000,
            max_value=6000,
            value=(3000, 6000),
            step=1
        )
    else:
        min_list_size, max_list_size = None, None

    # Minimum and maximum tournament size slider
    # Get the maximum tournament size first
    @st.cache_data
    def get_max_tournament_size(raw_list_data):
        return raw_list_data['Tournament Size'].max()
    max_tournament_size = get_max_tournament_size(raw_list_data)
    min_size, max_size = st.slider(
        "Select Tournament Size Range (# of players)",
        min_value=0,
        max_value=max_tournament_size,
        value=(0, max_tournament_size),
        step=1
    )

    # Tournament type selector
    tournament_type = st.selectbox(
        "Select Tournament Type",
        ["Any", "Singles", "Teams"]
    )

    # Now lets apply these filters to the raw data
    @st.cache_data
    def filter_data(
        raw_list_data,
        raw_unit_data,
        raw_option_data,
        start_date,
        end_date,
        select_by_list_size,
        min_list_size,
        max_list_size,
        min_size,
        max_size,
        tournament_type
    ):
        if select_by_list_size:
            filtered_list_data = raw_list_data.filter(
                (pl.col("Start Date") >= datetime.combine(start_date, datetime.min.time())) &
                (pl.col("End Date") <= datetime.combine(end_date, datetime.max.time())) &
                (pl.col("Game Size") >= min_list_size) &
                (pl.col("Game Size") <= max_list_size) &
                (pl.col("Tournament Size") >= min_size) &
                (pl.col("Tournament Size") <= max_size)
            )
        else:
            filtered_list_data = raw_list_data.filter(
                (pl.col("Start Date") >= datetime.combine(start_date, datetime.min.time())) &
                (pl.col("End Date") <= datetime.combine(end_date, datetime.max.time())) &
                (pl.col("Tournament Size") >= min_size) &
                (pl.col("Tournament Size") <= max_size)
            )
        if tournament_type != "Any":
            filtered_list_data = filtered_list_data.filter(pl.col("Type") == tournament_type)

        # Get the list of valid list IDs after filtering
        valid_list_ids = filtered_list_data.select(pl.col("list_id")).unique().to_series().to_list()

        # Filter unit and option data based on valid list IDs
        filtered_unit_data = raw_unit_data.filter(pl.col("list_id").is_in(valid_list_ids))
        filtered_option_data = raw_option_data.filter(pl.col("list_id").is_in(valid_list_ids))

        return filtered_list_data, filtered_unit_data, filtered_option_data, filtered_list_data.height // 2
    list_data, unit_data, option_data, num_games = filter_data(
        raw_list_data,
        raw_unit_data,
        raw_option_data,
        start_date,
        end_date,
        select_by_list_size,
        min_list_size,
        max_list_size,
        min_size,
        max_size,
        tournament_type
    )

    st.caption(f'After applying your filters, there are {num_games} games in the dataset out of a possible {tnum_games} games.')

    st.header('Page Selection')
    page = st.selectbox(
        'Select Page',
        ['Welcome',
         'Game-wide',
         'Faction specific',
         'Raw Data']
    )

# Depending on the selected page, we show the appropriate content
if page == 'Welcome':
    welcome_page()

elif page == 'Game-wide':
    game_wide_page(tournament_type, faction_keys, magic_paths, list_data, unit_data, option_data, num_games)

elif page == 'Faction specific':
    faction_specific_page(tournament_type, faction_keys, magic_paths, list_data, unit_data, option_data, num_games)

elif page == 'Raw Data':
    st.title('Raw Data')
    st.markdown('##### List Data')
    st.markdown("""
                The game wide data from all the uploaded lists is shown below.
                As a reminder, you can use the filters in the sidebar to filter the data.
                The "List" column indicates whether a valid army list was provided for that entry.
                A "None" in the "Game Size", "Total Points" or "Magicalness" columns indicates either that no valid army list
                was provided for that entry, or the computation of that entry failed for some reason.
                You can also download this data as a CSV file by mousing over the top right corner of the table.
                """)
    st.write(list_data)

    st.markdown('##### Unit Data')
    st.markdown('The individual unit data from all the uploaded lists is shown below; \
                the "list_id" column indicates which list the unit was taken in. \
                Note that the "models" column will display None for units that can not take additional models. \
                As a reminder, you can use the filters in the sidebar to filter the data. \
                You can also download this data as a CSV file by mousing over the top right corner of the table.')
    st.write(unit_data)

    st.markdown('##### Option Data')
    st.markdown('The individual option data from all the uploaded lists is shown below; \
                the "unit_id" column indicates which unit selected the given option. \
                As a reminder, you can use the filters in the sidebar to filter the data. \
                You can also download this data as a CSV file by mousing over the top right corner of the table.')
    st.write(option_data)

