# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import seaborn as sns

# Data analysis tools
import polars as pl
import numpy as np
from scipy import stats

# Math functions
from math import sqrt

# Full name list
from constants import faction_names, faction_keys
from helper_functions import colourmap, round_sig

@st.fragment()
def average_list_tool_page(faction_keys, list_data, unit_data, option_data):
    st.title('Average List Tool')
    
    st.markdown('''<p>Select a faction to adjust the point costs of units and options. The tool will calculate how these adjustments impact the average cost of existing lists.</p>''', unsafe_allow_html=True)
    
    faction_name = st.selectbox('Select a Faction', faction_names, index=None)
    if not faction_name:
        st.caption('Please select a faction using the widget above.')
        return
        
    fkey = faction_keys[faction_names.index(faction_name)]
    flist_data = list_data.filter((pl.col('Faction') == fkey) & pl.col('List'))
    valid_list_ids = flist_data['list_id'].unique()
    funit_data = unit_data.filter(pl.col('list_id').is_in(valid_list_ids))
    foption_data = option_data.filter(pl.col('list_id').is_in(valid_list_ids))
    
    if flist_data.is_empty():
        st.warning("No lists found for this faction.")
        return

    # Define global option condition
    magic_cond = (
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('magic items')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('favour')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('gifts of the dark gods')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('blood power')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('manifestations')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('honour')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('battle runes')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('big names')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('big name')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('heroic traits')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('aspect of nature')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('howdah')) |
        (pl.col('Option Name').is_not_null() & pl.col('Option Type').str.to_lowercase().str.contains('totems'))
    )

    # Separate global vs unit-specific options
    global_options_df = foption_data.filter(magic_cond)
    global_option_names = sorted(global_options_df['Option Name'].unique().to_list())
    
    unit_names = sorted(funit_data['Name'].unique().to_list())
    
    st.markdown("### Point Adjustments Form")
    
    with st.form("points_adjustment_form"):
        changes = {}
        
        st.markdown("#### Global Options")
        cols = st.columns(3)
        for i, opt in enumerate(global_option_names):
            with cols[i % 3]:
                val = st.number_input(f"{opt}", value=0, step=1, key=f"global_{opt}")
                if val != 0:
                    changes[('Global', opt)] = val
        
        st.markdown("#### Units & Unit Options")
        for unit in unit_names:
            with st.expander(f"Unit: {unit}"):
                u_cols = st.columns(3)
                
                # Base Cost & Extra Models
                with u_cols[0]:
                    b_val = st.number_input("Base", value=0, step=1, key=f"{unit}_base")
                    if b_val != 0:
                        changes[(unit, 'Base Cost')] = b_val
                
                models_data = funit_data.filter((pl.col('Name') == unit) & pl.col('Models').is_not_null())
                has_models = not models_data.is_empty()
                if has_models:
                    with u_cols[1]:
                        e_val = st.number_input("Extra Models", value=0, step=1, key=f"{unit}_extramodels")
                        if e_val != 0:
                            changes[(unit, 'Extra Models')] = e_val

                # Unit Options (Exclude global options and Model Count types)
                unit_options = foption_data.filter(
                    (pl.col('Unit Name') == unit) & 
                    (~magic_cond) & 
                    (pl.col('Option Type') != 'Model Count')
                )['Option Name'].unique().to_list()
                
                for i, opt in enumerate(sorted(unit_options)):
                    with u_cols[(i + (2 if has_models else 1)) % 3]:
                        val = st.number_input(f"{opt}", value=0, step=1, key=f"{unit}_{opt}")
                        if val != 0:
                            changes[(unit, opt)] = val
        
        submitted = st.form_submit_button("Calculate Point Changes")

    if submitted:
        if not changes:
            st.info("No point changes were entered.")
            return
            
        # Exception logic setup
        unit_names_set = set(unit_names)
        generic_options = set(foption_data.filter(~pl.col('Unit Name').is_in(unit_names_set))['Option Name'].unique().to_list())
        generic_options = generic_options - {'Venom Sacs', 'Bronze Backbone', 'Piercing Spike', 'Incendiary Ichor'}
        PER_UNIT_EXCEPTIONS = { 'Wizard Conclave (1)', 'Wizard Conclave (2)', 'Wizard Conclave (3)', 
                                'Wizard Conclave', 'Totem Bearer', 'Warlock Acolytes', 'Knight Banneret', 
                                'Prepared Position', 'Mark of the Eternal Champion', 'Sorcerous Antannae',
                                'Tunnel Digger', 'Firestarter (Spear of Infinity)', 'Firestarter (Smite the Unbeliever)'} | generic_options
        if 'Creepy-Crawlies' in PER_UNIT_EXCEPTIONS:
            PER_UNIT_EXCEPTIONS.remove('Creepy-Crawlies')

        HOWDAH = {'Unnatural Roots', 'Lodestone Shield', 'Monolith of Vitalism', 
                  'Magnetic Great Bow', 'Carved Wisdom', 'Suncatcher Crystal'}

        # Calculate Minimum unit sizes 
        def calc_min_size(s):
            val = s.min()
            return (val // 5) * 5 if val >= 10 else val

        min_sizes_df = (
            funit_data.filter(pl.col('Models').is_not_null())
            .group_by('Name')
            .agg(pl.col('Models').min().alias('Min Size Raw'))
            .with_columns(
                pl.when(pl.col('Min Size Raw') >= 10)
                .then((pl.col('Min Size Raw') // 5) * 5)
                .otherwise(pl.col('Min Size Raw'))
                .alias('Min Size')
            )
            .select(['Name', 'Min Size'])
        )

        units = funit_data
        options_data = foption_data

        # Scaling logic
        options_with_models = options_data.join(
            units.select(["list_id", "unit_id", "Models"]),
            on=["list_id", "unit_id"], how="left"
        ).with_columns(pl.col("Models").fill_null(1).cast(pl.Int64))

        options_scaled = (
            options_with_models
            .with_columns(
                pl.when(
                    (~pl.col("Option Name").is_in(global_option_names)) &
                    (~pl.col("Option Name").is_in(PER_UNIT_EXCEPTIONS)) & 
                    (~pl.col("Option Name").is_in(["Base Cost", "Extra Models"])) &
                    (~((pl.col("Option Name") == 'Ambush') & (pl.col('Unit Name').is_in({'Wildhorn Herd'})))) |
                    ((pl.col("Option Name").is_in(HOWDAH)) & (pl.col('Unit Name') == 'Thyroscutus Herd'))
                )
                .then(pl.col("Models"))
                .otherwise(1)
                .alias("Scale")
            )
        )

        # Build Dataframes of scales per list
        base_costs = (
            units.group_by(["list_id", pl.col("Name").alias("Unit Name")])
            .agg(pl.len().cast(pl.Int64).alias("Scale"))
            .with_columns(pl.lit("Base Cost").alias("Option Name"))
        )

        extra_models = (
            units.join(min_sizes_df, left_on="Name", right_on="Name", how="left")
            .with_columns((pl.col("Models") - pl.col("Min Size")).fill_null(0).alias("Extra"))
            .group_by(["list_id", pl.col("Name").alias("Unit Name")])
            .agg(pl.sum("Extra").cast(pl.Int64).alias("Scale"))
            .with_columns(pl.lit("Extra Models").alias("Option Name"))
            .filter(pl.col("Scale") > 0)
        )
        
        option_entries = (
            options_scaled.group_by(["list_id", "Unit Name", "Option Name"])
            .agg(pl.sum("Scale").cast(pl.Int64).alias("Scale"))
        )

        all_entries = pl.concat([
            base_costs.select(["list_id", "Unit Name", "Option Name", "Scale"]),
            extra_models.select(["list_id", "Unit Name", "Option Name", "Scale"]),
            option_entries.select(["list_id", "Unit Name", "Option Name", "Scale"])
        ])

        # Apply price changes
        changes_list = []
        for (u, o), val in changes.items():
            if u == 'Global':
                changes_list.append({'Option Name': o, 'Change': val})
            else:
                changes_list.append({'Unit Name': u, 'Option Name': o, 'Change': val})
                
        changes_df = pl.DataFrame(changes_list)
        if 'Unit Name' in changes_df.columns:
            joined = all_entries.join(changes_df, on=["Unit Name", "Option Name"], how="inner")
        else:
            # Handle if only globals were changed
            joined = all_entries.join(changes_df, on=["Option Name"], how="inner")
            
        list_impacts = (
            joined.with_columns((pl.col("Scale") * pl.col("Change")).alias("Point Delta"))
            .group_by("list_id")
            .agg(pl.sum("Point Delta").alias("Total Delta"))
        )
        
        # Merge with all lists (fill nulls with 0)
        final_impacts = (
            flist_data.select(["list_id", "Score", "Total Points"])
            .join(list_impacts, on="list_id", how="left")
            .with_columns(pl.col("Total Delta").fill_null(0))
        )

        deltas = final_impacts["Total Delta"].to_numpy()
        scores = final_impacts["Score"].to_numpy()
        total_pts = final_impacts["Total Points"].to_numpy()
        
        avg_delta = np.mean(deltas)
        std_delta = np.std(deltas)
        se_delta = std_delta / sqrt(len(deltas)) if len(deltas) > 0 else 0
        
        avg_pct = np.mean(deltas / total_pts) * 100 if len(deltas) > 0 else 0
        se_pct = np.std(deltas / total_pts) * 100 / sqrt(len(deltas)) if len(deltas) > 0 else 0

        st.markdown("### Change Statistics")
        st.markdown("These statistics summarize the overall impact of your proposed point adjustments across all analyzed lists. The **Average Absolute Point Change** shows the raw number of points lists will gain or lose on average, while the **Average Percentage Point Change** normalizes this against the total points of the lists to give a sense of the relative impact.")
        st.markdown(f"**Average Absolute Point Change:** {avg_delta:.2f} ± {se_delta:.2f} pts")
        st.markdown(f"**Average Percentage Point Change:** {avg_pct:.2f}% ± {se_pct:.2f}%")
        
        if len(deltas) > 1 and np.std(scores) > 0 and std_delta > 0:
            r, p = stats.pearsonr(deltas, scores)
            st.markdown(f"**Correlation with List Score:** Pearson's r = {r:.3f} (p-value: {p:.4f})")
            if r > 0:
                st.caption("A positive correlation indicates that the lists performing well (higher scores) are the ones facing the largest point increases under your proposed changes.")
            else:
                st.caption("A negative correlation indicates that lists performing poorly are going up in price, or that stronger lists are benefiting from point decreases.")

        # Distribution Plot
        fig1, ax1 = plt.subplots(figsize=(10, 6), layout="constrained")
        fig1.patch.set_alpha(0.0)
        ax1.patch.set_alpha(0.0)

        sns.histplot(deltas, kde=True, ax=ax1, color="#254C73")
        ax1.set_title("Distribution of List Point Changes")
        ax1.set_xlabel("Point Change")
        ax1.set_ylabel("Number of Lists")
        ax1.axvline(avg_delta, color='black', linestyle='--', label=f'Mean: {avg_delta:.1f}')
        ax1.legend()
        st.pyplot(fig1)
        plt.close(fig1)

        # Correlation Plot
        fig2, ax2 = plt.subplots(figsize=(10, 6), layout="constrained")
        fig2.patch.set_alpha(0.0)
        ax2.patch.set_alpha(0.0)

        sns.regplot(x=deltas, y=scores, ax=ax2, scatter_kws={'alpha':0.5, 'color':'#DEAA46'}, line_kws={'color':'black'})
        ax2.set_title("Point Change vs. List Score")
        ax2.set_xlabel("Point Change")
        ax2.set_ylabel("List Score")
        
        st.pyplot(fig2)
        plt.close(fig2)
