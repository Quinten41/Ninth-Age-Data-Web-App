# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import seaborn as sns

# Data analysis tools
import polars as pl
import pandas as pd
import numpy as np
import scipy.stats as stats

# Import helper function
from helper_functions import colourmap, round_sig

@st.fragment()
def show_faction_scores(list_data, faction_keys):
    ''' A fragment to show the average scores of each faction with error bars '''
    no_mirror_list_data = list_data.filter(pl.col('Faction') != pl.col('Opponent'))

    confidence_interval = st.slider('Confidence Interval for Error Bars', 
                                    min_value=50.0, 
                                    max_value=99.9, 
                                    value=95.0, 
                                    step=0.1,
                                    format="%.1f%%",
                                    key='faction_performance_ci'
                                    )

    fig,ax = plt.subplots(layout="constrained")

    sns.pointplot(data=no_mirror_list_data.to_pandas(), 
                  x='Faction', 
                  order=faction_keys, 
                  y='Score', 
                  linestyle='none', 
                  ax=ax, 
                  errorbar=('ci', confidence_interval)
                  )
    
    plt.axhline(y=10, linestyle='--')
    plt.title('Average Score of Each Faction')
    plt.xlabel('Faction')
    plt.ylabel('Average Score')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)   # Axes background transparent

    st.pyplot(fig)
    plt.close(fig)

@st.fragment()
def show_score_distribution(list_data, first_data, second_data, faction_keys):
    ''' A fragment to show the distribution of scores '''

    # Add a multiselect to choose which factions to include
    selected_factions = st.multiselect('Select Factions to Include', options=faction_keys, default=faction_keys, key='score_dist_factions')

    turn_separate = st.toggle('Show First and Second Turn Separately', value=True)

    if not selected_factions:
        st.warning('Please select at least one faction to display the score distribution.')
        return

    scores = list(range(21))
    if len(selected_factions) == len(faction_keys) and turn_separate:
        first_counts = [first_data.filter(pl.col('Score') == i).height for i in scores]
        second_counts = [second_data.filter(pl.col('Score') == i).height for i in scores]
        unknown_counts = [list_data.filter((pl.col('Score') == i) & (pl.col('Turn') == 'Unknown')).height for i in scores]
        bar_data = pd.DataFrame({
            'Number of Games': first_counts + second_counts + unknown_counts,
            'Score': scores * 3,
            'Turn': ['First'] * 21 + ['Second'] * 21 + ['Unknown'] * 21
        })
    elif turn_separate:
        first_counts = [first_data.filter((pl.col('Score') == i) & (pl.col('Faction').is_in(selected_factions))).height for i in scores]
        second_counts = [second_data.filter((pl.col('Score') == i) & (pl.col('Faction').is_in(selected_factions))).height for i in scores]
        unknown_counts = [list_data.filter((pl.col('Score') == i) & (pl.col('Turn') == 'Unknown') & (pl.col('Faction').is_in(selected_factions))).height for i in scores]
        bar_data = pd.DataFrame({
            'Number of Games': first_counts + second_counts + unknown_counts,
            'Score': scores * 3,
            'Turn': ['First'] * 21 + ['Second'] * 21 + ['Unknown'] * 21
        })

    else:
        if len(selected_factions) == len(faction_keys):
            counts = [list_data.filter(pl.col('Score') == i).height for i in scores]
        else:
            counts = [list_data.filter((pl.col('Score') == i) & (pl.col('Faction').is_in(selected_factions))).height for i in scores]
        bar_data = pd.DataFrame({
            'Number of Games': counts,
            'Score': scores
        })

    fig, ax = plt.subplots(layout="constrained")
    sns.barplot(data=bar_data, x='Score', y='Number of Games', hue='Turn' if turn_separate else None, ax=ax)
    plt.title('Distribution of Scores')
    plt.xlabel('Score')
    plt.ylabel('Number of Games')
    if turn_separate:
        plt.legend(title='Turn')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)  # Axes background transparent

    st.pyplot(fig)
    plt.close(fig)

# Main function of this document
def scores_page(faction_keys, list_data):
    ''' The content of the scores & performance page '''
    num_faction = len(faction_keys) # Should be 16
    # Set styling for plots
    sns.set_theme()
    plt.style.use(['seaborn-v0_8','fast'])

    # The title of the page
    st.title('Scores & Performance')

    # Some basic filtering and computations; first about turn order then removing mirror matchups
    first_data = list_data.filter(pl.col('Turn') == 'First')
    second_data = list_data.filter(pl.col('Turn') == 'Second')
    fa, fe = round_sig(first_data['Score'].mean(), first_data['Score'].std() / (first_data.height ** 0.5))
    sa, se = round_sig(second_data['Score'].mean(), second_data['Score'].std() / (second_data.height ** 0.5))

    # To start with, let's just show a basic scatter plot of faction performance
    st.subheader('Faction Performance')

    # Add an explanation of the plot
    st.markdown(f'<p>The scatterplot below shows the average score of each faction (excluding mirror matchups) along with error bars indicating \
            the selected confidence interval (95%, or two standard deviations of the mean, is standard). Please keep in mind, \
            with {num_faction} different factions, it is not statistically unreasonable for 1-2 factions to fall outside of \
            95% confidence intervals, even if balance is theoretically "perfect".</p>', unsafe_allow_html=True)

    # Show the plot in a fragment so it doesn't reload the whole page on interaction
    show_faction_scores(list_data, faction_keys)

    # Now let's look at the distribution of scores when going first and second
    st.subheader('Score Distribution')

    st.markdown(f'''<p>The histogram below shows the distribution of scores across all games.
                You can use the multiselect widget below to select which factions are included in the distribution.
                By default, all factions are included.</p>''',
                unsafe_allow_html=True
            )

    # Show the plot in a fragment so it doesn't reload the whole page on interaction
    show_score_distribution(list_data, first_data, second_data, faction_keys)

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
                if sem < 1e-6:
                    cell = f'{int(mean)}'
                else:
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
                if sem < 1e-6:
                    cell = f'{int(mean)}'
                else:
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
                if sem < 1e-6:
                    cell = f'{int(mean)}'
                else:
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
                    if sem < 1e-6:
                        cell = f'{int(mean)}'
                    else:
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


