# Import Streamlit
import streamlit as st

# Data analysis tools
import polars as pl

# Other utilities
from datetime import datetime
from datetime import date
#import psutil
import gc

# Import functions to generate the different pages
from welcome_page import welcome_page
from game_wide_page import game_wide_page
from faction_specific_page import faction_specific_page
from list_finder import list_finder_page

# Import function to organise and load data
from load_and_organise_data import load_and_organise_data

# Import constants
from constants import faction_keys, faction_names

# Set Streamlit page layout to wide
# st.set_page_config(layout="wide")

# Display the Ninth Age Logo
st.image('https://bedroombattlefields.com/wp-content/uploads/2021/11/the-ninth-age-1024x479.png')

# process = psutil.Process()
# st.write(f"Memory usage: {process.memory_info().rss / 1024 ** 2:.2f} MB")
# st.write(f"CPU usage: {process.cpu_percent()}%")

# First load the data into three polars dataframes


# Cached function to get the minimum and maximums for sliders
@st.cache_data
def get_max_min(raw_list_data):
    return raw_list_data['Tournament Size'].max(), raw_list_data['Game Size'].max(), raw_list_data['Game Size'].min()

# Get the dataframes and minimum and maximums for sliders
with st.spinner('Loading data...'):
    raw_list_data, raw_unit_data, raw_option_data, tnum_games, magic_paths = load_and_organise_data()
    max_tournament_size, max_game_size, min_game_size = get_max_min(raw_list_data)

# Add a sidebar for filtering and page selection
with st.sidebar:
    st.title('Navigation & Filters')

    st.header('Page Selection')
    page = st.pills(
        'Select Page',
        ['Welcome',
         'Game-Wide',
         'Faction Specific',
         'List Finder',
         'Raw Data'],
         default='Welcome',
    )

    st.header('Data Filters')

    # Date range slider
    start_date, end_date = st.slider(
        "Select Date Range",
        value=(date(2024, 1, 1), date.today()),
        format="YYYY-MM-DD",
        min_value=date(2024, 1, 1),
        max_value=date.today()
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
            min_value=min_game_size,
            max_value=max_game_size,
            value=(min_game_size, max_game_size),
            step=1
        )
    else:
        min_list_size, max_list_size = None, None

    # Minimum and maximum tournament size slider
    min_size, max_size = st.slider(
        "Select Tournament Size Range (# of players)",
        min_value=0,
        max_value=max_tournament_size,
        value=(0, max_tournament_size),
        step=1
    )

    # Tournament type selector
    tournament_type = st.pills(
        'Select Tournament Type',
        ['Any', 'Singles', 'Teams'],
        default='Any',
        selection_mode='single'
    )

    # Now lets apply these filters to the raw data
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
        valid_list_ids = filtered_list_data.select(pl.col("list_id")).unique().to_series().implode()

        # Filter unit and option data based on valid list IDs
        filtered_unit_data = raw_unit_data.filter(pl.col("list_id").is_in(valid_list_ids))
        filtered_option_data = raw_option_data.filter(pl.col("list_id").is_in(valid_list_ids))

        return filtered_list_data, filtered_unit_data, filtered_option_data, filtered_list_data.height // 2

    # Get the filtered data
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

# Depending on the selected page, we show the appropriate content
if page == 'Welcome':
    welcome_page()

elif page == 'Game-Wide':
    game_wide_page(tournament_type, faction_keys, magic_paths, list_data, unit_data, option_data, num_games)

elif page == 'Faction Specific':
    faction_name = st.selectbox('Select a Faction', faction_names, index=None)

    if faction_name == None:
        st.caption('Please select a faction using the widget above to display data.')
    else:
        # Filter data to only include the selected faction
        fkey = faction_keys[ faction_names.index(faction_name) ]
        flist_data = list_data.filter(pl.col('Faction') == fkey)
        valid_list_ids = flist_data.select(pl.col("list_id")).unique().to_series().implode()
        funit_data = unit_data.filter(pl.col('list_id').is_in(valid_list_ids))
        foption_data = option_data.filter(pl.col('list_id').is_in(valid_list_ids))
        # Display the faction specific page
        # This is a fragment so data won't be resorted on each interaction
        faction_specific_page(faction_name, flist_data, funit_data, foption_data)

elif page == 'List Finder':
    list_finder_page(faction_keys, magic_paths, list_data, unit_data, option_data, num_games)

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

# Garbage collecting
gc.collect()