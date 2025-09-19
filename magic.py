# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Data analysis tools
import polars as pl

# Plotting functions
from plotting_functions import labelled_scatterplot_regions


def magic_page(list_data, option_data, magic_paths):
    st.title('Magic')

    st.subheader('Magic Path Performance and Popularity')

    # First create a plot showing the performance of magic paths

    # Polars version for magic points
    path_option_data = option_data.filter(pl.col('Option Type') == 'Path')
    path_list_ids = path_option_data.select('list_id').unique().to_series().implode()
    magic_scores = list_data.filter(pl.col('list_id').is_in(path_list_ids))['Score']
    mavg = magic_scores.mean()

    # For each path, find all unique list_ids where it was taken
    path_points = []
    for path in magic_paths:
        spell_list_ids = path_option_data.filter(pl.col('Option Name') == path).select('list_id').unique().to_series().implode()
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
    st.subheader('Magicalness Performance and Popularity')

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