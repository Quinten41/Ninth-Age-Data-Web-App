# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import seaborn as sns

# Data analysis tools
import polars as pl
import pandas as pd
import numpy as np

@st.fragment()
def faction_list_count(tournament_type, list_data, faction_keys, start_date, end_date):
    '''Helper function to create a bar chart of the number of games played with each faction.'''

    poss_splits = ['No Split', 'By Turn', 'By Opponent Faction', 'By Score', 'By Date']
    if tournament_type == 'Any':
        poss_splits.append('By Singles or Teams')
    
    bar_stack = st.pills('Select Bar Split', poss_splits, default='By Turn')

    # Make a histogram of the number of games played with each faction
    if bar_stack == 'No Split':
        counts = np.array([list_data.filter(pl.col('Faction') == fac).height for fac in faction_keys])
        ind = np.arange(len(faction_keys))
        width = 0.7
        fig, ax = plt.subplots(layout='constrained')
        ax.bar(ind, counts, width)
        
    elif bar_stack == 'By Turn':
        turns = ['First', 'Second', 'Unknown']
        counts = {turn: np.array([list_data.filter((pl.col('Faction') == fac) & (pl.col('Turn') == turn)).height for fac in faction_keys]) for turn in turns}

        ind = np.arange(len(faction_keys))
        width = 0.7
        fig, ax = plt.subplots(layout='constrained')
        ax.bar(ind, counts['First'], width, bottom=counts['Unknown'] + counts['Second'], label='First')
        ax.bar(ind, counts['Second'], width, bottom=counts['Unknown'], label='Second')
        ax.bar(ind, counts['Unknown'], width, label='Unknown')
        ax.legend(title='Turn')

    elif bar_stack == 'By Opponent Faction':
        opponent_factions = list_data.select('Opponent').unique().to_series().to_list()
        counts = {opp: np.array([list_data.filter((pl.col('Faction') == fac) & (pl.col('Opponent') == opp)).height for fac in faction_keys]) for opp in opponent_factions}

        ind = np.arange(len(faction_keys))
        width = 0.7
        fig, ax = plt.subplots(layout='constrained')
        bottom = np.zeros(len(faction_keys))
        for opp in opponent_factions:
            ax.bar(ind, counts[opp], width, bottom=bottom, label=opp)
            bottom += counts[opp]
        ax.legend(title='Opponent Faction', bbox_to_anchor=(1, 1))

    elif bar_stack == 'By Score':
        score_bins = [0, 4, 8, 13, 17]
        score_labels = ['<4', '4-7', '8-12', '13-16', '>16']
        counts = {score: np.array([
            list_data.filter(
                (pl.col('Faction') == fac) & (pl.col('Score') < score_bins[i+1]) & (pl.col('Score') >= score_bins[i])
            ).height if i < len(score_bins)-1 else
            list_data.filter(
                (pl.col('Faction') == fac) & (pl.col('Score') >= score_bins[i])
            ).height for fac in faction_keys
        ]) for i, score in enumerate(score_labels)}

        ind = np.arange(len(faction_keys))
        width = 0.7
        fig, ax = plt.subplots(layout='constrained')
        bottom = np.zeros(len(faction_keys))
        for score in score_labels:
            ax.bar(ind, counts[score], width, bottom=bottom, label=score)
            bottom += counts[score]
        ax.legend(title='Score')

    elif bar_stack == 'By Date':
        # Create monthly bins between start_date and end_date
        date_range = pd.date_range(start=start_date, end=end_date, freq='MS')
        date_labels = [date.strftime('%Y-%m') for date in date_range]
        counts = {}
        for date in date_range:
            start = date.date()
            end = (date + pd.DateOffset(months=1)).date()
            label = date.strftime('%Y-%m')
            counts[label] = np.array([
                list_data.filter(
                    (pl.col('Faction') == fac) &
                    (pl.col('Start Date') >= start) &
                    (pl.col('Start Date') < end)
                ).height for fac in faction_keys
            ])

        ind = np.arange(len(faction_keys))
        width = 0.7
        fig, ax = plt.subplots(layout='constrained')
        bottom = np.zeros(len(faction_keys))
        for date in date_labels:
            ax.bar(ind, counts[date], width, bottom=bottom, label=date)
            bottom += counts[date]
        ax.legend(title='Month', bbox_to_anchor=(1, 1))

    elif bar_stack == 'By Singles or Teams':
        types = ['Singles', 'Teams']
        counts = {t: np.array([list_data.filter((pl.col('Faction') == fac) & (pl.col('Type') == t)).height for fac in faction_keys]) for t in types}

        ind = np.arange(len(faction_keys))
        width = 0.7
        fig, ax = plt.subplots(layout='constrained')
        ax.bar(ind, counts['Singles'], width, bottom=counts['Teams'], label='Singles')
        ax.bar(ind, counts['Teams'], width, label='Teams')
        ax.legend(title='Tournament Type')


    ax.set_xticks(ind)
    ax.set_xticklabels(faction_keys, rotation=45, ha='right')

    plt.title('Number of Games Played with Each Faction')
    plt.xlabel('Faction')
    plt.ylabel('Number of Games')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)  # Axes background transparent
    st.pyplot(fig)
    plt.close(fig)

def popularity_page(tournament_type, faction_keys, list_data, start_date, end_date):
    st.title('Faction Popularity')

    st.subheader('Faction Popularity')

    st.markdown('<p>The pie chart below shows the popularity of each faction as a percentage of all games played.</p>', 
                unsafe_allow_html=True)
    # Make a pie chart of the number of games played with each faction
    faction_counts = list_data.group_by('Faction').agg([
        pl.count().alias('num_games')
    ]).sort('num_games', descending=True)
    faction_counts_pd = faction_counts.to_pandas()
    fig, ax = plt.subplots(layout='constrained')
    ax.pie(faction_counts_pd['num_games'], labels=faction_counts_pd['Faction'], autopct='%1.1f%%', startangle=140)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('Faction Popularity', y=1.015)
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)  # Axes background transparent
    st.pyplot(fig)
    plt.close(fig)

    st.markdown('''<p>The histogram below shows the absolute number of games played by each faction.
                You can use the widget to decide how to show stacks in the bars.</p>''', unsafe_allow_html=True)
    
    # Show the bar chart (in a fragment to avoid the widget recomputing the whole page)
    faction_list_count(tournament_type, list_data, faction_keys, start_date, end_date)

    st.subheader('Pairing Popularity')
    if tournament_type == 'Singles':
        st.caption('You must select a Tournament Type of "Teams" or "Any" in the sidebar to display \
                    information about pairing popularity in team tournaments.')
        return

    team_games = list_data.filter(pl.col('Type') == 'Teams')
    # Count games for each (Opponent, Faction) pair
    counts = team_games.group_by(['Opponent', 'Faction']).agg([
        pl.count().alias('num_games')
    ])
    # Pivot to wide format
    counts_pivot = counts.pivot(
        values='num_games',
        index='Opponent',
        columns='Faction'
    ).fill_null(0)
    # For each Faction, compute the total number of games played (as Faction)
    faction_totals = team_games.group_by('Faction').agg([
        pl.count().alias('All')
    ])
    # Total number of games
    All = faction_totals['All'].sum()

    st.markdown(f'The heatmap below shows the percentage of games each faction has been paired against an opponent in a team tournament \
                out of all games played by that faction in team tournaments. \
                The rows indicate the faction, while the columns indicate the opponent. \
                The colour provides a visual cue of the percentage, with darker colours indicating a higher percentage. \
                The "All" column is the percentage of games played by that faction in team tournaments out of all games played in team tournaments; \
                given the current selections, the total number of games played in team tournaments is {All//2}.</p>',
                unsafe_allow_html=True)

    # Calculate the percent for each (Opponent, Faction) entry
    percent_table = counts_pivot.clone()
    for col in percent_table.columns:
        if col != 'Opponent':
            total = faction_totals.filter(pl.col('Faction') == col)['All'][0]
            percent_table = percent_table.with_columns([
                (pl.col(col) / total * 100).alias(col)
            ])
    # Add "All" row: percent of games played as each faction (sum over opponents)
    all_row = faction_totals.with_columns([
        (pl.col('All') / All * 100).round(1)
    ])
    # Convert to pandas for heatmap
    percent_table_pd = percent_table.to_pandas().set_index('Opponent')
    all_row_pd = all_row.to_pandas().set_index('Faction').T
    percent_table_pd = pd.concat([all_row_pd, percent_table_pd])

    sns.heatmap(
        percent_table_pd,
        annot=True,
        fmt='.0f',
        cmap='Blues',
        cbar_kws={'label': 'Percent (%)'},
        linewidths=0.5,
        linecolor='gray'
    )
    plt.rcParams['figure.constrained_layout.use'] = True
    plt.xlabel('Faction')
    plt.ylabel('Opponent')
    plt.title('Matchup Popularity in Team Tournaments')
    fig = plt.gcf()
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)  # Axes background transparent
    st.pyplot(fig)
    plt.close(fig)