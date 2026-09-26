# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import seaborn as sns

# Data analysis tools
import polars as pl
import pandas as pd

# Helper functions
from helper_functions import colourmap

@st.fragment()
def faction_performance_breakdown(list_data, faction_keys):
    '''Interactive section to explore faction performance across specific objectives and deployments.'''
    
    st.subheader('Faction Performance Breakdown')
    st.markdown('<p>Select a category and a specific type to see how each faction performs under those conditions. The chart displays the average score for each faction.</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        category = st.selectbox('Select Category', ['Deployment', 'Primary', 'Secondary'])
    
    # Dynamically populate the second dropdown based on the available data in the selected category
    available_types = list_data.filter(pl.col(category) != 'Unknown').select(category).unique().to_series().drop_nulls().sort().to_list()
    
    with col2:
        specific_type = st.selectbox(f'Select {category} Type', available_types)
        
    if not specific_type:
        st.warning('No data available for the selected category.')
        return

    # Filter data to the specific selection
    filtered_data = list_data.filter(pl.col(category) == specific_type)
    
    # Calculate average score per faction
    faction_scores = (
        filtered_data.group_by('Faction')
        .agg([
            pl.col('Score').mean().alias('Average Score'),
            pl.len().alias('Lists Played')
        ])
        .filter(pl.col('Faction').is_in(faction_keys))
        .sort('Average Score', descending=True)
        .to_pandas()
    )

    if faction_scores.empty:
        st.info('Not enough data to display faction performance for this selection.')
        return

    # Plotting
    fig, ax = plt.subplots(layout="constrained", figsize=(10, 5))
    sns.barplot(data=faction_scores, x='Faction', y='Average Score', ax=ax, palette='viridis')
    
    ax.axhline(10, linestyle='--', color='gray', alpha=0.7)
    ax.set_title(f'Average Faction Score: {specific_type} ({category})')
    ax.set_ylabel('Average Score')
    ax.set_xlabel('Faction')
    plt.xticks(rotation=45, ha='right')
    
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    st.pyplot(fig)
    plt.close(fig)


def objectives_deployment_page(list_data, faction_keys):
    '''Main render function for the Objectives & Deployment page.'''
    st.title('Objectives & Deployment')
    
    # Set styling for plots
    sns.set_theme()
    plt.style.use(['seaborn-v0_8','fast'])

    # -------------------------------------------------------------------------
    # Deployment Stats
    # -------------------------------------------------------------------------
    st.subheader('Deployment Popularity and Advantage')
    st.markdown('<p>This table tracks how often each deployment type is played and evaluates potential first-turn advantage by displaying the average score achieved by the player taking the first turn.</p>', unsafe_allow_html=True)

    # Calculate distinct games played per deployment
    dep_games = list_data.filter(pl.col('Deployment') != 'Unknown').unique(subset=['game_id']).group_by('Deployment').agg(
        pl.len().alias('Games played')
    )
    
    # Calculate 1st turn average score per deployment
    dep_scores = list_data.filter((pl.col('Deployment') != 'Unknown') & (pl.col('Turn') == 'First')).group_by('Deployment').agg(
        pl.col('Score').mean().round(2).alias('1st turn ØPts')
    )
    
    # Join and format
    dep_table = dep_games.join(dep_scores, on='Deployment', how='left').sort('Games played', descending=True).to_pandas()
    st.dataframe(dep_table.set_index('Deployment'), use_container_width=True)

    # -------------------------------------------------------------------------
    # Primary Objective Stats
    # -------------------------------------------------------------------------
    st.subheader('Primary Objectives')
    st.markdown('<p>Below is a breakdown of the primary objectives played. The total games are divided into times the first turn player (Attacker) won the objective, the second turn player (Defender) won, or a draw occurred. <i>Note: Since raw victory condition data isn\'t binary in the current dataset, Attacker/Defender averages represent their respective final game scores.</i></p>', unsafe_allow_html=True)

    prim_games = list_data.filter(pl.col('Primary') != 'Unknown').unique(subset=['game_id']).group_by('Primary').agg(
        pl.len().alias('Total Games')
    )
    
    prim_attacker = list_data.filter((pl.col('Primary') != 'Unknown') & (pl.col('Turn') == 'First')).group_by('Primary').agg(
        pl.col('Score').mean().round(2).alias('Attacker Avg Score')
    )
    
    prim_defender = list_data.filter((pl.col('Primary') != 'Unknown') & (pl.col('Turn') == 'Second')).group_by('Primary').agg(
        pl.col('Score').mean().round(2).alias('Defender Avg Score')
    )

    prim_table = prim_games.join(prim_attacker, on='Primary', how='left').join(prim_defender, on='Primary', how='left').sort('Total Games', descending=True).to_pandas()
    st.dataframe(prim_table.set_index('Primary'), use_container_width=True)

    # -------------------------------------------------------------------------
    # Secondary Objective Stats
    # -------------------------------------------------------------------------
    st.subheader('Secondary Objectives')
    st.markdown('<p>Unlike Primary Objectives, Secondary Objectives are chosen individually by players. This table shows how many times a secondary objective was selected and the resulting average score for the player who selected it.</p>', unsafe_allow_html=True)

    sec_stats = list_data.filter(pl.col('Secondary') != 'Unknown').group_by('Secondary').agg([
        pl.len().alias('Total Selections'),
        pl.col('Score').mean().round(2).alias('Average Score'),
        pl.col('Score').filter(pl.col('Turn') == 'First').mean().round(2).alias('Attacker Avg Score'),
        pl.col('Score').filter(pl.col('Turn') == 'Second').mean().round(2).alias('Defender Avg Score')
    ]).sort('Total Selections', descending=True).to_pandas()
    
    st.dataframe(sec_stats.set_index('Secondary'), use_container_width=True)

    # -------------------------------------------------------------------------
    # Faction Specific Performance Fragment
    # -------------------------------------------------------------------------
    faction_performance_breakdown(list_data, faction_keys)
