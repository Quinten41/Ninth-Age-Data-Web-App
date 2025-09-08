# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.lines as mlines
import matplotlib.ticker as mticker

# Data analysis tools
import polars as pl
import pandas as pd
import numpy as np
from scipy import stats

# Import plotting functions
from plotting_functions import labelled_scatterplot_regions, scatterplot_with_errors

# Import helper functions
from helper_functions import colourmap

# Full name dictionary
# This should be in the same order as faction_keys in main_page.py
faction_names = ['Beast Herds', 'Dread Elves', 'Dwarven Holds',\
            'Demon Legions', 'Empire of Sonnstahl', 'Highborn Elves',\
            'Infernal Dwarves', 'Kingdom of Equitaine', 'Ogre Khans',\
            'Orcs and Goblins', 'Saurian Ancients', 'Sylvan Elves',\
            'Undying Dynasties', 'Vampire Covenant', 'Vermin Swarm',\
            'Warriors of the Dark Gods']

def faction_specific_page(tournament_type, faction_keys, magic_paths, list_data, unit_data, option_data, num_games):
    '''Display the Faction Specific Page content.'''

    faction_name = st.selectbox('Select a Faction',
                 ['None'] + faction_names)
    
    if faction_name == 'None':
        st.caption('Please select a faction using the selector above to display data.')

    else:
        fkey = faction_keys[ faction_names.index(faction_name) ]
        st.title(faction_name)

        # Set styling for plots
        sns.set_theme()
        plt.style.use(['seaborn-v0_8','fast'])

        # Filter data to only include the selected faction
        flist_data = list_data.filter(pl.col('Faction') == fkey)
        funit_data = unit_data.filter(pl.col('list_id').is_in(flist_data['list_id']))
        foption_data = option_data.filter(pl.col('list_id').is_in(flist_data['list_id']))

        # First a section on the categories in the faction
        st.subheader('Categories')
        
        # Get all unique categories for this faction
        categories = funit_data.select('Category').unique().to_series().to_list()

        # Precompute category points per list using polars
        cat_points = funit_data.group_by(['list_id', 'Category']).agg([
            pl.col('Cost').sum().alias('cat_points')
        ])

        # Pivot to wide format
        cat_points_wide = cat_points.pivot(
            values='cat_points',
            index='list_id',
            columns='Category'
        ).fill_null(0)

        # Join with Score and Total Points from flist_data
        cat_points_wide = cat_points_wide.join(
            flist_data.select(['list_id', 'Score', 'Total Points']),
            on='list_id',
            how='left'
        )

        # Melt to long format for plotting
        melt_vars = [cat for cat in categories if cat in cat_points_wide.columns]
        cat_data = cat_points_wide.melt(
            id_vars=['list_id', 'Score', 'Total Points'],
            value_vars=melt_vars,
            variable_name='Category',
            value_name='cat_points'
        ).filter(pl.col('cat_points').is_not_null())

        cat_data = cat_data.with_columns([
            (pl.col('cat_points') / pl.col('Total Points')).alias('Percent Taken')
        ])

        desired_order = ['Characters', 'Core', 'Special']
        other_cats = [cat for cat in melt_vars if cat not in desired_order]
        category_order = desired_order + other_cats

        # Build sorted list of category keys
        sorted_cats = [cat for cat in category_order if cat in cat_data['Category'].unique()]

        # Create a mapping from category to its order index
        category_order_map = {cat: i for i, cat in enumerate(category_order)}

        cat_data = cat_data.with_columns([
            pl.col('Category').replace(category_order_map).alias('CategoryOrder')
        ])

        cat_data = cat_data.sort('CategoryOrder')

        # Group by category and aggregate using polars
        cat_data_grouped = cat_data.group_by('Category').agg([
        pl.col('Percent Taken').mean().alias('mean'),
        pl.col('Percent Taken').std().alias('std'),
        pl.col('Percent Taken').median().alias('median'),
        ])

        # Pearson r and p-value for each category using polars
        def pearsonr_safe_polars(df):
            x = df['Percent Taken'].to_numpy()
            y = df['Score'].to_numpy()
            if len(x) > 1 and np.std(y) > 0:
                r, p = stats.pearsonr(x, y)
                return r, p
            else:
                return np.nan, np.nan

        pearson_results = []
        for cat in sorted_cats: #cat_data_grouped['Category'].to_list():
            subdf = cat_data.filter(pl.col('Category') == cat)
            r, p = pearsonr_safe_polars(subdf)
            pearson_results.append({'Category': cat, 'r': r, 'p': p})
        pearson_df = pl.DataFrame(pearson_results)

        # Build the table in polars
        data_table_cat = cat_data_grouped.join(pearson_df, on='Category', how='left')
        # Convert to pandas for formatting and .to_html()
        data_table_cat_pd = data_table_cat.to_pandas()
        # Format columns for display
        data_table_cat_pd['<b>Mean Points Taken</b>'] = (data_table_cat_pd['mean']*100).round(1).astype(str) + '%'
        data_table_cat_pd['<b>Median Points Taken</b>'] = (data_table_cat_pd['median']*100).round(1).astype(str) + '%'
        data_table_cat_pd['<b>Standard Deviation</b>'] = (data_table_cat_pd['std']*100).round(1).astype(str) + '%'
        data_table_cat_pd['<b>Pearson\'s r</b>'] = [
            f'<span style="color:{colourmap(4 * abs(r) if pd.notnull(r) else 0)}">{r:.4f}</span>' if pd.notnull(r) else '—'
            for r in data_table_cat_pd['r']
        ]
        data_table_cat_pd['<b>p-value</b>'] = [
            f'<span style="color:{colourmap(stats.norm.ppf(1-p/2) if pd.notnull(p) and p > 0 else 0)}">{p:.4f}</span>' if pd.notnull(p) else '—'
            for p in data_table_cat_pd['p']
        ]
        # Reorder and rename columns for display
        display_cols = ['<b>Mean Points Taken</b>', '<b>Median Points Taken</b>', '<b>Standard Deviation</b>', "<b>Pearson's r</b>", '<b>p-value</b>']
        data_table_cat_pd = data_table_cat_pd.set_index('Category')[display_cols].T.reset_index(drop=True)
        data_table_cat_pd.columns.name = None
        data_table_cat_pd.insert(0, '', display_cols)
        df_html_cat = data_table_cat_pd[category_order].to_html(index=False, escape=False, border=1)

        st.markdown(f'''
            <p>The table below summarises the performance and popularity of different categories in {faction_name}. \
            The mean points taken, median points taken, and standard deviation provide insights into the amount of points being spent by players \
            within each category; \
            about two thirds of the lists will fall within one standard deviation of the mean for any given category. \
            The Pearson correlation coefficient and p-value help assess the strength and significance of the relationship between \
            the amount of points spent in each category and the score achieved. The Pearson correlation coefficient is a number between -1 and 1 \
            that indicates how close the data points are to following a linear trend. A value of +1 (-1) indicates the data can be
            perfectly modeled by a straight line with positive (negative) slope. The p-value tells you how likely it is that there is
            no linear correlation between the variables; a small p-value, therefore, indicates a high probability of list performance \
            being correlated with how many points are spent in that category (one has to examine the sign of the Pearson correlation coefficient \
            to determine whether this is a beneficial or detrimental relationship).</p>''', unsafe_allow_html=True)
        st.markdown(df_html_cat, unsafe_allow_html=True)

        # Next add a plot displaying the correlation between points spent in a category and the score

        # Now we make a plot of category performance

        st.markdown(f'<p>The plot below and to the right provides a visualisation of the relationship between the points being spent in a category and army performance. \
        Please note that, to allow for a clear representation of the data, a smoothing algorithm has been applied to the raw data.</p>', unsafe_allow_html=True)

        palette = sns.color_palette(n_colors=len(cat_data['Category'].unique()))
        legend_lines = []

        for i, cat in enumerate(sorted_cats):
            group = cat_data.filter(pl.col('Category') == cat).to_pandas()
            sns.regplot(
                data=group,
                x='Percent Taken',
                y='Score',
                lowess=True,
                scatter=False,
                line_kws={'label': cat, 'color': palette[i]}
            )
            # Create a proxy artist for the legend
            legend_lines.append(mlines.Line2D([], [], color=palette[i], label=cat[0] if isinstance(cat, tuple) else str(cat)))

        ax = plt.gca()
        fig = plt.gcf()
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
        plt.xlabel('Percentage of Points Spent in Category')
        plt.ylabel('Average Score')
        plt.title(f'Category Performance in {faction_name}')
        plt.legend(handles=legend_lines, title='Category')
        fig.patch.set_alpha(0.0)  # Figure background transparent
        ax.patch.set_alpha(0.0)   # Axes background transparent
        st.pyplot(fig)


        # Next a section on the units in the faction
        st.subheader('Units')

        # Create a plot using labelled_scatterplot_regions 
        # to display the internal performance of all the factions units

        # Remove duplicates
        funit_data_unique = funit_data.unique(subset=['Name', 'list_id'])

        # Get unique games (lists) and their scores
        list_games = funit_data_unique.unique(subset=['list_id'])['Score']
        num_unit_games = list_games.len()
        unit_mean = list_games.mean()
        unit_var = list_games.var()

        # Aggregate unit points and mean score using polars
        unit_points = funit_data_unique.group_by('Name').agg([
            pl.col('list_id').n_unique().alias('x'),
            pl.col('Score').mean().alias('y')
        ])

        # Convert to pandas for plotting if needed
        unit_points_pd = unit_points.to_pandas()

        fig, ax = labelled_scatterplot_regions(
            zip(unit_points_pd['x'], unit_points_pd['y']),
            unit_points_pd['Name'].tolist(),
            num_unit_games,
            unit_var,
            unit_mean
        )
        plt.title('Unit Performance and Popularity')
        fig.patch.set_alpha(0.0)  # Figure background transparent
        ax.patch.set_alpha(0.0)   # Axes background transparent

        st.markdown(f'<p>The plot below shows the performance and popularity of units in {faction_name}. Each point represents a unit, with its popularity (number of games played) on the x-axis and its average score on the y-axis. \
        The heatmap the points are superimposed upon shows the |z|-score of a unit taken in that percentage of games with that mean score. \
        The red region indicates very unlikely performances, whereas the green region indicates more statistically typical performances; \
        about 67% of the points should be in the green region and 95% within the bounds of the yellow/red region. Points well into \
        the red/yellow region may indicate a balance problem.</p>', unsafe_allow_html=True)

        st.pyplot(fig)

        # Create a plot showing the average number of units of each type taken in a list
        # And the average number of points spent on each type of unit

        st.markdown('<p>The plot below displays the average number of points spent on each unit and the average number of units taken in a given list. \
        By points spent, it is the total number of points spent on that unit type across all entries; to obtain the average number of points spent per unit taken, \
        one should divide the y-value by the x-value. The error bars in both directions indicate one standard deviation.</p>',
        unsafe_allow_html=True)

        # Create a plot showing how many units are being taken and how many points are being spent on them
        unit_stats = funit_data.group_by(['Name', 'list_id']).agg([
            pl.col('Name').count().alias('count'),
            pl.col('Cost').sum().alias('points')
        ])
        unit_summary = unit_stats.group_by('Name').agg([
            pl.col('count').mean().alias('avg_count'),
            pl.col('count').std().alias('std_count'),
            pl.col('points').mean().alias('avg_points'),
            pl.col('points').std().alias('std_points')
        ])
        points = list(zip(unit_summary['avg_count'], unit_summary['avg_points']))
        unit_names = unit_summary['Name'].to_list()
        xerr = unit_summary['std_count'].to_list()
        yerr = unit_summary['std_points'].to_list()

        fig, ax = scatterplot_with_errors(
            points, unit_names, xerr=xerr, yerr=yerr,
            xlabel='Average Number per List',
            ylabel='Average Points per List',
            title='Unit Usage: Average Number and Points per List'
        )
        fig.patch.set_alpha(0.0)  # Figure background transparent
        ax.patch.set_alpha(0.0)   # Axes background transparent
        st.pyplot(fig)


        # Add a section on options for individual units
        st.subheader('Unit Options')

        st.markdown('<p>Use the selectbox below to choose a unit to display its options.</p>', unsafe_allow_html=True)
        unit_name = st.selectbox('Select a Unit', ['None'] + sorted(unit_names))
        if unit_name == 'None':
            st.caption('Please select a unit using the selectbox above to display data.')
        else:
            # Filter option data to only include the selected unit
            uunit_data = funit_data.filter(pl.col('Name') == unit_name)
            unique_uunit_data = uunit_data.unique(subset=['list_id'])
            num_lists = unique_uunit_data.shape[0]
            if num_lists < 5:
                st.markdown(f'<p>There is insufficient data on {unit_name} in the current dataset \
                            to show any further analysis.</p>', unsafe_allow_html=True)
            else:
                uoption_data = foption_data.filter(pl.col('Unit Name') == unit_name).unique(subset=['Option Name', 'list_id'])
                unit_specific_report(faction_name, unit_name, uoption_data, uunit_data, unique_uunit_data, num_lists)



# Helper function to make an option plot
@st.cache_data
def make_option_plot(group, num_lists, var_score, mean_score, plot_num=None):
    option_stats = (
        group.groupby('Option Name')
        .agg(
            lists_with_option=('list_id', pd.Series.nunique),
            avg_score=('Score', 'mean')
        )
        .reset_index()
    )

    fig, ax = labelled_scatterplot_regions(
        points=zip(option_stats['lists_with_option'], option_stats['avg_score']),
        labels=option_stats['Option Name'].tolist(),
        num_games=num_lists,
        variance=var_score,
        mean=mean_score,
        xlim=(15,30),
        ylim=(8,12)
    )
    if plot_num != None:
        plt.title(f'Option Performance and Popularity ({plot_num})')
    else:
        plt.title(f'Option Performance and Popularity')

    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)   # Axes background transparent

    return fig,ax

def unit_specific_report(faction_name, unit_name, uoption_data, uunit_data, unique_uunit_data, num_lists):
    # Add information about the number of units being taken to uoption_data using polars
    unit_counts = uunit_data.group_by('list_id').agg([
        pl.col('unit_id').count().alias('num_units'),
        pl.col('Score').first().alias('Score')
    ])
    # Build new rows as polars DataFrame
    new_rows = unit_counts.with_columns([
        pl.when(pl.col('num_units') == 1)
        .then(pl.lit('1 Unit'))
        .otherwise(pl.col('num_units').cast(str) + pl.lit(' Units'))
        .alias('Option Name'),
        pl.lit(unit_name).alias('Unit Name'),
        pl.lit('Number of Units').alias('Option Type'),
        pl.lit(None).alias('unit_id')
    ]).select(['list_id', 'unit_id', 'Unit Name', 'Option Name', 'Option Type', 'Score'])

    # Concatenate with uoption_data (convert both to pandas for compatibility with downstream code)
    uoption_data_pd = uoption_data.to_pandas() if hasattr(uoption_data, 'to_pandas') else uoption_data
    new_rows_pd = new_rows.to_pandas()
    uoption_data_pd = pd.concat([uoption_data_pd, new_rows_pd], ignore_index=True)

    # Calculate the mean and variance of the unit's scores
    mean_score = unique_uunit_data['Score'].mean()
    var_score = unique_uunit_data['Score'].var()

    if uoption_data_pd.empty:
        st.markdown(f'<p>There are no options for {unit_name} taken in the current dataset.</p>', unsafe_allow_html=True)
    else:
        unique_option_data = uoption_data_pd.drop_duplicates(subset=['Option Name', 'list_id'])
        # Count number of options per Option Type
        option_type_counts = unique_option_data.groupby('Option Type')['Option Name'].nunique().sort_values(ascending=False)
        total_count = option_type_counts.sum()
        num_plots = (total_count - 1) // 25 + 1  # Number of graphs needed if we limit to 25 options each
        unique_types = list(option_type_counts.index)

        if len(unique_types) == 1 or num_plots == 1:
            fig,_ = make_option_plot(unique_option_data, num_lists, var_score, mean_score)
            st.markdown(f'''
            <p>The scatter plot below shows the performance and popularity of options for {'' if unit_name[-1]=='s' else 'a'} {unit_name}. 
            The x-axis is the percentage of games played with one or more choices of each option. The percentage is not calculated 
            with respect to all the games played by {faction_name}, but just the games in which {'' if unit_name[-1]=='s' else 'a'} {unit_name} {'were' if unit_name[-1]=='s' else 'was'} taken. 
            The y-axis shows the average score of the games in which one or more choices of the given option was taken. 
            Finally, the heatmap displays the z-score for the mean; options in the green region score similarily to a random sample 
            with the same mean, whereas options in the red region do not. If the scores were randomly assigned, 
            one would expect 95% of them to have a z-score of |z|<2.</p>''', unsafe_allow_html=True)
            st.pyplot(fig)
        else:
            # Greedily assign types to num_plots groups to balance total number of options
            group_types = [[] for _ in range(num_plots)]
            group_counts = [0] * num_plots
            for opt_type, count in option_type_counts.items():
                # Assign to group with current minimum count
                min_idx = group_counts.index(min(group_counts))
                group_types[min_idx].append(opt_type)
                group_counts[min_idx] += count

            st.markdown(f'''
                <p>The scatter plot below shows the performance and popularity of options for {'' if unit_name[-1]=='s' else 'a'} {unit_name}. 
                The x-axis is the percentage of games played with one or more choices of each option. The percentage is not calculated 
                with respect to all the games played by {faction_name}, but just the games in which {'' if unit_name[-1]=='s' else 'a'} {unit_name} {'were' if unit_name[-1]=='s' else 'was'} taken. 
                The y-axis shows the average score of the games in which one or more choices of the given option was taken. 
                Finally, the heatmap displays the z-score for the mean; options in the green region score similarily to a random sample 
                with the same mean, whereas options in the red region do not. If the scores were randomly assigned, 
                one would expect 95% of them to have a z-score of |z|<2. As {'' if unit_name[-1]=='s' else 'a'} {unit_name} has many options, 
                for clarity the options have been split across {num_plots} scatterplots. Before each scatterplot there is a list of the 
                option types the scatterplot shows.</p>''', unsafe_allow_html=True)
            
            # Create and display each plot
            for i in range(num_plots):
                group = unique_option_data[unique_option_data['Option Type'].isin(group_types[i])]
                fig,_ = make_option_plot(group, num_lists, var_score, mean_score, plot_num=i+1)
                st.markdown(f'''
                <p>This scatterplot shows options of the following types:</p>
                <ul>
                {''.join([f'<li>{opt_type}</li>' for opt_type in group_types[i]])}
                </ul>''', unsafe_allow_html=True)
                st.pyplot(fig)