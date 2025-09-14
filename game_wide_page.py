# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as mcolors

# Data analysis tools
import polars as pl
import pandas as pd
import numpy as np
import scipy.stats as stats

# Plotting functions
from plotting_functions import labelled_scatterplot_regions

# Import helper function
from helper_functions import colourmap, round_sig

# Import constants
from constants import faction_keys

@st.fragment()
def game_wide_page(tournament_type, faction_keys, magic_paths, list_data, unit_data, option_data, num_games):
    ''' The content of the game-wide statistics page '''
    num_faction = len(faction_keys) # Should be 16
    # Set styling for plots
    sns.set_theme()
    plt.style.use(['seaborn-v0_8','fast'])

    # The title of the page
    st.title('Game-Wide Statistics')

    # Some basic filtering and computations; first about turn order then removing mirror matchups
    first_data = list_data.filter(pl.col('Turn') == 'First')
    second_data = list_data.filter(pl.col('Turn') == 'Second')
    fa, fe = round_sig(first_data['Score'].mean(), first_data['Score'].std() / (first_data.height ** 0.5))
    sa, se = round_sig(second_data['Score'].mean(), second_data['Score'].std() / (second_data.height ** 0.5))

    scores = list(range(21))
    first_counts = [first_data.filter((pl.col('Score') == i)).height for i in scores]
    second_counts = [second_data.filter((pl.col('Score') == i)).height for i in scores]

    no_mirror_list_data = list_data.filter(pl.col('Faction') != pl.col('Opponent'))


    # To start with, let's just show a basic scatter plot of faction performance
    st.subheader('Faction Performance')

    # Add an explanation of the plot
    st.markdown(f'<p>The scatterplot below shows the average score of each faction (excluding mirror matchups) along with error bars indicating \
            two standard deviations of the mean (95% confidence interval, assuming normally distributed means). Please keep in mind, \
            with {num_faction} different factions, it is not statistically unreasonable for 1-2 factions to fall outside two \
            standard deviations of the mean, even if balance is theoretically "perfect".</p>', unsafe_allow_html=True)

    fig,ax = plt.subplots(layout="constrained")
    
    sns.pointplot(data=no_mirror_list_data.to_pandas(), x='Faction', order=faction_keys, y='Score', linestyle = 'none', ax=ax)
    plt.axhline(y=10, linestyle='--')
    plt.title('Average Score of Each Faction')
    plt.xlabel('Faction')
    plt.ylabel('Average Score')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)   # Axes background transparent

    st.pyplot(fig)
    plt.close(fig)

    # Now let's look at the distribution of scores when going first and second
    st.subheader('Score Distribution')

    st.markdown(f'<p>The histogram below shows the distribution of scores across all games when going first and second.</p>', 
            unsafe_allow_html=True
            )

    # Plot using seaborn barplot with polars
    bar_data = pl.DataFrame({
        'Number of Games': first_counts + second_counts,
        'Score': scores * 2,
        'Turn': ['First'] * 21 + ['Second'] * 21
    })

    fig, ax = plt.subplots(layout="constrained")
    sns.barplot(data=bar_data.to_pandas(), x='Score', y='Number of Games', hue='Turn')
    plt.title('Distribution of Scores When Going First and Second')
    plt.xlabel('Score')
    plt.ylabel('Number of Games')
    plt.legend(title='Turn')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)  # Axes background transparent

    st.pyplot(fig)
    plt.close(fig)

    st.subheader('Matchup Performance Table')

    # Add an explanation of a table
    st.markdown(f'<p>The external performances of all the factions \
                are displayed in a table. The columns indicate the various factions, and the rows display \
                the scenarios in which the performance of the faction is being measured. Each entry is formatted as: mean ± standard error. \
                The mean value indicates the average score of that faction over all the games indicated by the row label (e.g. the row \
                "first" indicates all games where that faction went first whereas the row "VC" indicates all games played by \
                the terrifying legions of the undead). Note that, unlike the plot at the begining of this page, the "All" row includes mirror matchups. \
                <p>Assuming The Ninth Age has "perfect" balance, about 65% of the entries should lie within one error of \
                10 points, the average score, 95% entries should be within two errors of 10 points, and essentially all of them should be \
                within three errors of 10 points. The text is colour coded based on how many errors the mean is away from 10 points; green \
                is very close, whereas red text is very far.</p> \
                <p>Across all games, the average score when going first is \
                <span style="color:{colourmap((fa - 10) / fe)}">{fa} ± {fe}</span>, whereas when going second it is \
                <span style="color:{colourmap((sa - 10) / se)}">{sa} ± {se}</span>.</p>', 
                unsafe_allow_html=True
                )

    # Now we will generate a table with various performance data
    # Create a matchup table: columns = factions, rows = factions, entries = 'mean±standard error'
    def matchup_table_df(list_data, first_data, second_data, factions):
        # Build the table as a DataFrame
        rows = []
        index = []
        # All row
        all_row = []
        for fac in factions:
            scores = list_data.filter(pl.col('Faction') == fac)['Score'].to_list()
            if len(scores) == 0:
                cell = ''
            else:
                mean = np.mean(scores)
                sem = stats.sem(scores) if len(scores) > 1 else 0
                mean, sem = round_sig(mean, sem)
                cell = f'{mean}±{sem}'
            all_row.append(cell)
        rows.append(all_row)
        index.append('All')
        # First row
        first_row = []
        for fac in factions:
            scores = first_data.filter(pl.col('Faction') == fac)['Score'].to_list()
            if len(scores) == 0:
                cell = ''
            else:
                mean = np.mean(scores)
                sem = stats.sem(scores) if len(scores) > 1 else 0
                mean, sem = round_sig(mean, sem)
                cell = f'{mean}±{sem}'
            first_row.append(cell)
        rows.append(first_row)
        index.append('First')
        # Second row
        second_row = []
        for fac in factions:
            scores = second_data.filter(pl.col('Faction') == fac)['Score'].to_list()
            if len(scores) == 0:
                cell = ''
            else:
                mean = np.mean(scores)
                sem = stats.sem(scores) if len(scores) > 1 else 0
                mean, sem = round_sig(mean, sem)
                cell = f'{mean}±{sem}'
            second_row.append(cell)
        rows.append(second_row)
        index.append('Second')
        # Matchup rows
        for opp in factions:
            matchup_row = []
            for fac in factions:
                if fac == opp:
                    matchup_row.append('-')
                    continue
                scores = list_data.filter((pl.col('Faction') == fac) & (pl.col('Opponent') == opp))['Score'].to_list()
                if len(scores) == 0:
                    cell = ''
                else:
                    mean = np.mean(scores)
                    sem = stats.sem(scores) if len(scores) > 1 else 0
                    mean, sem = round_sig(mean, sem)
                    cell = f'{mean}±{sem}'
                matchup_row.append(cell)
            rows.append(matchup_row)
            index.append(opp)
        df = pd.DataFrame(rows, columns=factions, index=index)
        return df

    # Function to colour the table cells based on z-score
    def colour_matchup(val):
        if val in ('', '-'): return ''
        try:
            mean, sem = val.split('±')
            mean = float(mean)
            sem = float(sem)
            z_score = (mean - 10) / sem if sem else 0
            colour = colourmap(z_score)
            return f'color: {colour}'
        except:
            return ''

    # Show the table
    matchup_df = matchup_table_df(list_data, first_data, second_data, faction_keys)
    st.write(matchup_df.style.map(colour_matchup))

    # Section for additional data
    st.subheader('Additional Data')

    # Function for additional data (fragment to avoid reloading the whole page)
    display_additional_data(list_data, option_data, magic_paths, tournament_type)


@st.fragment()
def display_additional_data(list_data, option_data, magic_paths, tournament_type):
    ''' A fragment to display additional data based on user selection '''

    # Add a selectbox to choose additional data to display
    additional_data = st.selectbox('Select Additional Data',
                 options=['Magic & Magicalness', 'Faction Popularity & Pairings'],
                 index=None
                 )
    
    # Display the specified additional data

    if additional_data == None:
        st.caption('No additional data has been selected. Please use the selectbox above to choose additional data to display.')
        return

    elif additional_data == 'Magic & Magicalness':
        st.markdown('##### Magic Path Performance and Popularity')

        # First create a plot showing the performance of magic paths

        # Polars version for magic points
        path_option_data = option_data.filter(pl.col('Option Type') == 'Path')
        path_list_ids = path_option_data.select('list_id').unique().to_series().to_list()
        magic_scores = list_data.filter(pl.col('list_id').is_in(path_list_ids))['Score']
        mavg = magic_scores.mean()

        # For each path, find all unique list_ids where it was taken
        path_points = []
        for path in magic_paths:
            spell_list_ids = path_option_data.filter(pl.col('Option Name') == path).select('list_id').unique().to_series().to_list()
            scores = list_data.filter(pl.col('list_id').is_in(spell_list_ids))['Score']
            path_points.append((len(scores), scores.mean()))

        # Create a figure about the performance of magic paths
        fig, ax = labelled_scatterplot_regions(
            figsize=(8,6), # Matplotlib default
            points=path_points,
            labels=magic_paths,
            num_games=len(magic_scores),
            variance=magic_scores.var(),
            mean=mavg,
            xlim = (0,30),
            ylim = (8,12)
        )
        plt.title('Performance and Popularity of Magic Paths')
        fig.patch.set_alpha(0.0)  # Figure background transparent
        ax.patch.set_alpha(0.0)  # Axes background transparent

        # Explain the plot
        st.markdown('<p>The scatterplot below shows the performance of the different magic paths. Each point represents a magic path, \
        with the x-axis showing the percentage of games played (out of all games where at least one magic path was selected) \
        and the y-axis showing the average score. The shading indicates the statistical significance of the results as z-scores. \
        The means should be normally distributed so a z-score of 2 corresponds to a p-value of 0.05.</p>',
        unsafe_allow_html=True)
        st.pyplot(fig)
        plt.close(fig)

        # Now add a plot about magicalness
        st.markdown('##### Magicalness Performance and Popularity')

        # Prepare data using polars
        magicalness_data = list_data.filter(pl.col('Magicalness').is_not_null())
        summary = magicalness_data.group_by('Magicalness').agg([
            pl.col('Score').mean().alias('mean'),
            pl.col('Score').count().alias('count'),
            pl.col('Score').std().alias('std')
        ])
        summary = summary.with_columns([
            (pl.col('std') / pl.col('count') ** 0.5).alias('sem'),
            (pl.col('count') / pl.col('count').sum() * 100).alias('percent')
        ])

        # Convert to numpy arrays for plotting
        x_vals = summary['Magicalness'].to_numpy()
        y_vals = summary['mean'].to_numpy()
        sem_vals = summary['sem'].to_numpy()
        percent_vals = summary['percent'].to_numpy()

        fig, ax = plt.subplots(layout="constrained")
        ax.errorbar(
            x_vals, y_vals, yerr=sem_vals,
            fmt='none', ecolor='gray', capsize=4, alpha=0.7, zorder=1
        )
        scatter = ax.scatter(
            x_vals, y_vals,
            s=percent_vals*25,
            c=percent_vals, cmap='Blues', alpha=0.8, zorder=2, edgecolor='k'
        )

        # Change ylim to fit the data better
        ax.set_ylim(bottom=max( min(y_vals)-1, 7.5), top=min(max(y_vals)+1, 12.5))

        # Add text labels for each point showing the percentage value
        rgba = mcolors.to_hex(plt.get_cmap('Blues')(0.8))
        for x, y, pct in zip(x_vals, y_vals, percent_vals):
            if ax.get_ylim()[0] < y + 0.175 < ax.get_ylim()[1]:
                ax.text(x, y + 0.175, f"{pct:.1f}%", ha='center', va='bottom', fontsize=8, color=rgba)

        ax.axhline(10, linestyle='--', color='gray', alpha=0.5)
        ax.set_xticks(range(int(summary['Magicalness'].max()) + 1))
        ax.set_xlabel('Magicalness')
        ax.set_ylabel('Average Score')
        ax.set_title('Performance and Popularity by Magicalness Level')
        plt.colorbar(scatter, ax=ax, label='Popularity (%)')
        fig.patch.set_alpha(0.0)  # Figure background transparent
        ax.patch.set_alpha(0.0)  # Axes background transparent

        # Explain the plot
        st.markdown('<p>The scatterplot below shows the performance and popularity of magic paths at different levels of magicalness. \
            Magicalness is calculated by adding the number of spells in the army to the number of channels with \
            a couple extra points potentially added for certain powerful magic-based abilities (e.g. +1 to cast). \
            The x-axis indicates the magicalness, while the y-axis shows the average score achieved when using that level of magicalness. \
            Each point is labelled with the popularity of that level of magicalness. \
            The colour and size of the dot provides a quick visual indication of the popularity of that level of magicalness.</p>',
            unsafe_allow_html=True)
        st.pyplot(fig)
        plt.close(fig)

    elif additional_data == 'Faction Popularity & Pairings':
        st.markdown('##### Faction Popularity')

        st.markdown('The histogram below shows the absolute number of games played by each faction \
                    broken up into first and second turn.</p>', unsafe_allow_html=True)
        
        # Make a histogram of the number of games played with each faction with stacks for first and second turn
        # Plot using seaborn histplot

        turns = ['First', 'Second', 'Unknown']
        counts = {turn: np.array([list_data.filter((pl.col('Faction') == fac) & (pl.col('Turn') == turn)).height for fac in faction_keys]) for turn in turns}

        ind = np.arange(len(faction_keys))
        width = 0.7
        fig, ax = plt.subplots(layout='constrained')
        ax.bar(ind, counts['First'], width, bottom=counts['Unknown'] + counts['Second'], label='First')
        ax.bar(ind, counts['Second'], width, bottom=counts['Unknown'], label='Second')
        ax.bar(ind, counts['Unknown'], width, label='Unknown')
        ax.set_xticks(ind)
        ax.set_xticklabels(faction_keys, rotation=45, ha='right')

        ax.legend(title='Turn')

        plt.title('Number of Games Played with Each Faction')
        plt.xlabel('Faction')
        plt.ylabel('Number of Games')
        fig.patch.set_alpha(0.0)  # Figure background transparent
        ax.patch.set_alpha(0.0)  # Axes background transparent
        st.pyplot(fig)
        plt.close(fig)

        st.markdown('##### Pairing Popularity')
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
                    out of all games played by that faction. \
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

