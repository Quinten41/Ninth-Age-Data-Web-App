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

# Helper functions
from helper_functions import colourmap

def calc_mean_se(df, group_col, filter_cond, alias_name):
    """Helper function to calculate mean and standard error, returning a formatted string column."""
    return df.filter(filter_cond).group_by(group_col).agg(
        pl.col('Score').mean().round(2).alias('mean'),
        (pl.col('Score').std() / pl.len().sqrt()).fill_null(0.0).round(2).alias('se')
    ).with_columns(
        pl.format("{} ± {}", pl.col('mean'), pl.col('se')).alias(alias_name)
    ).select([group_col, alias_name])


@st.fragment()
def faction_performance_breakdown(list_data, faction_keys):
    st.subheader('Faction Performance Breakdown')
    
    st.markdown('''<p>The scatterplot below visualizes the performance and popularity of factions for a selected deployment, primary, or secondary objective. The y-axis represents the average score, while the size and color of the bubbles indicate the popularity of the selection for that faction. Error bars represent the calculated margin of error based on your selected confidence interval.</p>''', unsafe_allow_html=True)
    
    # Widget to select confidence interval
    confidence_interval = st.slider('Confidence Interval for Error Bars', 
                                    min_value=50.0, 
                                    max_value=99.9, 
                                    value=95.0, 
                                    step=0.1,
                                    format="%.1f%%",
                                    key='faction_perf_ci')
    
    col1, col2 = st.columns(2)
    category_options = ['Deployment', 'Primary', 'Secondary'] 
    
    with col1:
        category = st.selectbox('Select Category', category_options)
    
    available_types = list_data.filter(
        pl.col(category).is_not_null() & (pl.col(category) != 'Unknown')
    ).select(category).unique().to_series().sort().to_list()
    
    with col2:
        specific_type = st.selectbox(f'Select {category} Type', available_types)
        
    if not specific_type:
        st.warning('No data available for the selected category.')
        return

    filtered_data = list_data.filter(
        (pl.col(category) == specific_type) & (pl.col('Faction').is_in(faction_keys))
    )
    
    if filtered_data.height == 0:
        st.info('Not enough data to display faction performance for this selection.')
        return

    # Group by faction and calculate mean, count, std
    summary = filtered_data.group_by('Faction').agg([
        pl.col('Score').mean().alias('mean'),
        pl.col('Score').count().alias('count'),
        pl.col('Score').std().alias('std')
    ]).sort('mean', descending=True)
    
    z_ci = norm.ppf(1 - (1 - confidence_interval / 100) / 2)
    summary = summary.with_columns([
        (z_ci * pl.col('std') / pl.col('count') ** 0.5).alias('margin'),
        (pl.col('count') / pl.col('count').sum() * 100).alias('percent')
    ]).fill_nan(0).fill_null(0) # Fill NaN/Null margins for sample sizes of 1

    # Convert to numpy arrays/lists for plotting
    factions = summary['Faction'].to_list()
    x_vals = range(len(factions))
    y_vals = summary['mean'].to_numpy()
    margin_vals = summary['margin'].to_numpy()
    percent_vals = summary['percent'].to_numpy()

    fig, ax = plt.subplots(layout="constrained", figsize=(10, 5))
    
    # Draw error bars
    ax.errorbar(
        x_vals, y_vals, yerr=margin_vals,
        fmt='none', ecolor='gray', capsize=4, alpha=0.7, zorder=1
    )
    
    # Draw popularity bubbles
    scatter = ax.scatter(
        x_vals, y_vals,
        s=percent_vals*25,
        c=percent_vals, cmap='Blues', alpha=0.8, zorder=2, edgecolor='k'
    )

    # Adjust ylim to fit the data better
    ax.set_ylim(bottom=max(min(y_vals)-1.5, 0), top=min(max(y_vals)+1.5, 20))

    # Add text labels for each point showing the percentage value
    rgba = mcolors.to_hex(plt.get_cmap('Blues')(0.8))
    for x, y, pct in zip(x_vals, y_vals, percent_vals):
        if ax.get_ylim()[0] < y + 0.175 < ax.get_ylim()[1]:
            ax.text(x, y + 0.175, f"{pct:.1f}%", ha='center', va='bottom', fontsize=8, color=rgba)
    
    ax.axhline(10, linestyle='--', color='gray', alpha=0.5)
    ax.set_xticks(x_vals)
    ax.set_xticklabels(factions, rotation=45, ha='right')
    ax.set_xlabel('Faction')
    ax.set_ylabel('Average Score')
    ax.set_title(f'Performance and Popularity: {specific_type}')
    plt.colorbar(scatter, ax=ax, label='Popularity (%)')
    
    # Clean background
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    ax.grid(True, axis='y', linestyle=':', alpha=0.6)
    
    st.pyplot(fig)
    plt.close(fig)


def objectives_deployment_page(list_data, faction_keys):
    st.title('Objectives & Deployment')
    
    sns.set_theme()
    plt.style.use(['seaborn-v0_8','fast'])

    # -------------------------------------------------------------------------
    # Deployment Stats
    # -------------------------------------------------------------------------
    st.subheader('Deployment Popularity and Advantage')
    st.markdown('''<p>The table below details the frequency of each deployment type alongside the average score achieved by the player taking the first turn, including the standard error.</p>''', unsafe_allow_html=True)

    dep_games = list_data.filter(pl.col('Deployment') != 'Unknown').unique(subset=['game_id']).group_by('Deployment').agg(
        pl.len().alias('Games played')
    )
    
    dep_scores = calc_mean_se(
        list_data, 
        'Deployment', 
        (pl.col('Deployment') != 'Unknown') & (pl.col('Turn') == 'First'), 
        '1st Turn Avg Score (±SE)'
    )
    
    dep_table = dep_games.join(dep_scores, on='Deployment', how='left').sort('Games played', descending=True).to_pandas()
    st.dataframe(dep_table.set_index('Deployment'), use_container_width=True)

    # -------------------------------------------------------------------------
    # Primary Objective Stats
    # -------------------------------------------------------------------------
    st.subheader('Primary Objectives')
    st.markdown('''<p>The table below tracks the total frequency of each primary objective. It provides the average scores and standard error for both the attacking and defending players across all matches.</p>''', unsafe_allow_html=True)

    prim_games = list_data.filter(pl.col('Primary') != 'Unknown').unique(subset=['game_id']).group_by('Primary').agg(
        pl.len().alias('Total Games')
    )
    
    prim_attacker = calc_mean_se(
        list_data, 
        'Primary', 
        (pl.col('Primary') != 'Unknown') & (pl.col('Turn') == 'First'), 
        'Attacker Avg Score (±SE)'
    )
    
    prim_defender = calc_mean_se(
        list_data, 
        'Primary', 
        (pl.col('Primary') != 'Unknown') & (pl.col('Turn') == 'Second'), 
        'Defender Avg Score (±SE)'
    )

    prim_table = prim_games.join(prim_attacker, on='Primary', how='left') \
                           .join(prim_defender, on='Primary', how='left') \
                           .sort('Total Games', descending=True).to_pandas()
    
    st.dataframe(prim_table.set_index('Primary'), use_container_width=True)

    # -------------------------------------------------------------------------
    # Secondary Objective Stats
    # -------------------------------------------------------------------------
    st.subheader('Secondary Objectives')
    st.markdown('''<p>The table below displays the total selections for each secondary objective. It breaks down the average scores (including standard error) overall, as well as grouped by attackers and defenders.</p>''', unsafe_allow_html=True)

    sec_filter = (pl.col('Secondary').is_not_null()) & (pl.col('Secondary') != 'Unknown')

    sec_games = list_data.filter(sec_filter).group_by('Secondary').agg(
        pl.len().alias('Total Selections')
    )
    
    sec_overall = calc_mean_se(
        list_data, 
        'Secondary', 
        sec_filter, 
        'Overall Avg Score (±SE)'
    )
    
    sec_attacker = calc_mean_se(
        list_data, 
        'Secondary', 
        sec_filter & (pl.col('Turn') == 'First'), 
        'Attacker Avg Score (±SE)'
    )
    
    sec_defender = calc_mean_se(
        list_data, 
        'Secondary', 
        sec_filter & (pl.col('Turn') == 'Second'), 
        'Defender Avg Score (±SE)'
    )

    sec_table = sec_games.join(sec_overall, on='Secondary', how='left') \
                         .join(sec_attacker, on='Secondary', how='left') \
                         .join(sec_defender, on='Secondary', how='left') \
                         .sort('Total Selections', descending=True).to_pandas()
    
    st.dataframe(sec_table.set_index('Secondary'), use_container_width=True)


    # -------------------------------------------------------------------------
    # Faction Specific Performance Fragment
    # -------------------------------------------------------------------------
    st.divider()
    faction_performance_breakdown(list_data, faction_keys)
