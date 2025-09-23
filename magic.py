# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns

# Data analysis tools
import polars as pl
import pandas as pd
from scipy.stats import norm

# Plotting functions
from plotting_functions import labelled_scatterplot_regions
from matplotlib.ticker import FuncFormatter

# The faction keys
from constants import faction_keys


@st.fragment()
def path_performance_plot(list_data, option_data, magic_paths):
    '''Helper function to create a scatterplot of the performance and popularity of magic paths.'''

    # Select what factions to include
    factions = st.multiselect(
        'Select Factions to Include',
        options=faction_keys,
        default=faction_keys,
        key='path_performance_factions'
    )
    
    
    if len(factions) == 0:
        st.warning('Please select at least one faction.')
        return
    elif len(factions) != len(faction_keys):
        flist_data = list_data.filter(pl.col('Faction').is_in(factions))
        path_option_data = option_data.filter((pl.col('Option Type') == 'Path') & (pl.col('list_id').is_in(flist_data['list_id'].implode())))
    else:
        flist_data = list_data
        path_option_data = option_data.filter(pl.col('Option Type') == 'Path')

    # Get magic points
    path_list_ids = path_option_data.select('list_id').unique().to_series().implode()
    magic_scores = flist_data.filter(pl.col('list_id').is_in(path_list_ids))['Score']
    mavg = magic_scores.mean()

    if len(path_list_ids[0]) == 0:
        st.error('No data available for the selected factions.')
        return
    
    # For each path, find all unique list_ids where it was taken
    path_points = []
    # Make a copy of magic_paths to modify for display
    fmagic_paths = magic_paths.copy()
    for i in range(len(magic_paths)-1,-1,-1):
        spell_list_ids = path_option_data.filter(pl.col('Option Name') == magic_paths[i]).select('list_id').unique().to_series().implode()
        if len(spell_list_ids[0]) == 0:
            fmagic_paths.pop(i)
            continue
        # Get the scores for these lists
        scores = flist_data.filter(pl.col('list_id').is_in(spell_list_ids))['Score']
        path_points.append((len(scores), scores.mean()))

    # Account for the fact the magic_paths were processed in reverse order in tha above loop
    path_points.reverse()

    if len(path_points) == 0:
        st.error('No data available for the selected factions.')
        return

    # Create a figure about the performance of magic paths
    fig, ax = labelled_scatterplot_regions(
        figsize=(8,6), # Matplotlib default
        points=path_points,
        labels=fmagic_paths,
        num_games=len(magic_scores),
        variance=magic_scores.var(),
        mean=mavg,
        xlim = (0,30),
        ylim = (8,12)
    )
    plt.title('Performance and Popularity of Magic Paths')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)  # Axes background transparent

    st.pyplot(fig)
    plt.close(fig)

@st.fragment()
def magicalness_plot(list_data):
    '''Helper function to create a scatterplot of the performance and popularity of magicalness levels.'''

    # Wdiget to select confidence interval
    confidence_interval = st.slider('Confidence Interval for Error Bars', 
                                    min_value=50.0, 
                                    max_value=99.9, 
                                    value=95.0, 
                                    step=0.1,
                                    format="%.1f%%",
                                    key='magicalness_ci')
    
    # Widget to select factions
    factions = st.multiselect(
        'Select Factions to Include',
        options=faction_keys,
        default=faction_keys,
        key='magicalness_factions'
    )

    # Prepare data
    if len(factions) == 0:
        st.warning('Please select at least one faction.')
        return
    elif len(factions) != len(faction_keys):
        magicalness_data = list_data.filter((pl.col('Faction').is_in(factions)) & (pl.col('Magicalness').is_not_null()))
    else:
        magicalness_data = list_data.filter(pl.col('Magicalness').is_not_null())

    if magicalness_data.height == 0:
        st.error('No data available for the selected factions.')
        return
    
    # Group by magicalness and calculate mean, count, std, sem, percent
    summary = magicalness_data.group_by('Magicalness').agg([
        pl.col('Score').mean().alias('mean'),
        pl.col('Score').count().alias('count'),
        pl.col('Score').std().alias('std')
    ])
    z_ci = norm.ppf(1 - (1 - confidence_interval / 100) / 2)
    summary = summary.with_columns([
        (z_ci * pl.col('std') / pl.col('count') ** 0.5).alias('sem'),
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

    st.pyplot(fig)
    plt.close(fig)

def magic_page(list_data, option_data, magic_paths):
    st.title('Magic')

    # Set styling for plots
    sns.set_theme()
    plt.style.use(['seaborn-v0_8','fast'])

    st.subheader('Path Popularity by Faction')

    # Explain the plot
    st.markdown('''<p>The stacked bar chart below shows the popularity of different magic paths for each faction.
    Each bar represents a faction, with the segments of the bar indicating the proportion of wizards that took each magic path.
    Note that factions whose wizards took no magic paths in any lists in the current dataset are not displayed</p>''',
    unsafe_allow_html=True)

    # Create the plot
    # Build a DataFrame with all (Faction, Path) counts in one go
    # Join list_data and option_data on 'list_id'
    joined = list_data.join(
        option_data.filter(pl.col('Option Type') == 'Path'),
        on='list_id',
        how='inner'
    )

    # Group by Faction and Option Name (Path), count occurrences
    counts_df = (
        joined
        .group_by(['Faction', 'Option Name'])
        .agg(pl.count().alias('count'))
        .filter(pl.col('Option Name').is_in(magic_paths))
    )

    # Pivot so each path is a column, each faction is a row
    pivot_df = (
        counts_df
        .pivot(
            values='count',
            index='Faction',
            columns='Option Name'
        )
        .fill_null(0)
    )
    
    # Reindex to ensure all factions are present and in the right order
    pivot_pd = pivot_df.to_pandas().set_index('Faction')
    pivot_pd = pivot_pd.reindex(faction_keys, fill_value=0)

    # Remove columns (paths) that were never taken
    pivot_pd = pivot_pd.loc[:, (pivot_pd.sum(axis=0) > 0)]
    # Remove rows (factions) that have no data
    # Loop over faction_keys and remove if there is no data
    # Also create faction_keys_filtered
    faction_keys_filtered = []
    for fac in faction_keys:
        if pivot_pd.loc[fac].sum() == 0:
            pivot_pd = pivot_pd.drop(fac, axis=0, errors='ignore')
        else:
            faction_keys_filtered.append(fac)

    # Normalize to get proportions
    path_df_percent = pivot_pd.div(pivot_pd.sum(axis=1), axis=0).fillna(0)

    # Create the figure and axes with constrained layout
    fig, ax = plt.subplots(layout='constrained')
    ax = path_df_percent.plot(kind='bar', stacked=True, colormap='Paired', width=0.7, ax=ax)
    ax.set_ylabel('Percentage of Lists (%)')
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{100*y:.0f}%'))
    ax.set_xlabel('Faction')
    ax.set_title('Magic Path Popularity by Faction')
    ax.legend(title='Magic Path', bbox_to_anchor=(1, 1))
    ax.set_xticklabels(faction_keys_filtered, rotation=45, ha='right')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)  # Axes background transparent
    st.pyplot(fig)
    plt.close(fig)

    st.subheader('Magic Path Performance and Popularity')

    # First create a plot showing the performance of magic paths

    # Explain the plot
    st.markdown('''<p>The scatterplot below shows the performance of the different magic paths. Each point represents a magic path,
    with the x-axis showing the percentage of games played (out of all games where at least one magic path was selected)
    and the y-axis showing the average score. The shading indicates the statistical significance of the results as z-scores.
    The means should be normally distributed so a z-score of 2 corresponds to a p-value of 0.05. You can use the multiselect widget
    above the plot to exclude/include factions from the data.</p>''',
    unsafe_allow_html=True)
    
    # Show the plot (in a fragment so widgets don't rerun the whole page)
    path_performance_plot(list_data, option_data, magic_paths)

    # Now add a plot about magicalness
    st.subheader('Magicalness Performance and Popularity')

    # Explain the plot
    st.markdown('<p>The scatterplot below shows the performance and popularity of magic paths at different levels of magicalness. \
        Magicalness is calculated by adding the number of spells in the army to the number of channels with \
        a couple extra points potentially added for certain powerful magic-based abilities (e.g. +1 to cast). \
        The x-axis indicates the magicalness, while the y-axis shows the average score achieved when using that level of magicalness. \
        Each point is labelled with the popularity of that level of magicalness. \
        The colour and size of the dot provides a quick visual indication of the popularity of that level of magicalness. \
        You can use the widgets to select the confidence interval the error bars show and to include/exclude specific factions.</p>',
        unsafe_allow_html=True)
    
    # Show the plot (in a fragment so widgets don't rerun the whole page)
    magicalness_plot(list_data)