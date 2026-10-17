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

# File handling and parsing
import os
import re
import json
from collections import defaultdict

# Full name list and pricing exceptions
from constants import (
    faction_names,
    faction_keys,
    EXCLUDED_OPTION_RULES,
    FACTION_LEVEL_RULES,
    PER_UNIT_RULES,
    SCALE_MULTIPLIER_RULES,
    UNIT_CATEGORY_ORDER,
)
from helper_functions import colourmap, round_sig

# Location of units.js (same folder as this file)
UNITS_JS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'units.js')

# Internal labels. FACTION_LEVEL is used in place of a unit name for options that are
# priced at the faction level; BASE_KEY / EXTRA_KEY label the unit's base cost and
# extra-model cost (they are deliberately not valid option names).
FACTION_LEVEL = '__faction__'
BASE_KEY = '__base_cost__'
EXTRA_KEY = '__extra_models__'


# ---------------------------------------------------------------------------
# units.js parsing
# ---------------------------------------------------------------------------
def _unescape(s):
    '''Turn the contents of a JS double-quoted string into a normal Python string.'''
    try:
        return json.loads(f'"{s}"')
    except ValueError:
        return s


@st.cache_data
def _parse_units_js(path, mtime):
    '''Parse units.js into {faction_key: {unit_name: {'category': str, 'min': int or None}}}.
    mtime is only used so the cache refreshes when the file is edited.'''
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    # Drop whole-line comments
    text = re.sub(r'^\s*//.*$', '', text, flags=re.MULTILINE)

    unit_info = {}
    # Each faction is a block of the form: const XX = [ ... ];
    for block in re.finditer(r'const\s+(\w+)\s*=\s*\[(.*?)^\];', text, flags=re.DOTALL | re.MULTILINE):
        fkey, body = block.group(1), block.group(2)
        units = {}
        # Each unit is a flat {...} object
        for obj in re.finditer(r'\{[^{}]*\}', body):
            obj_text = obj.group(0)
            name = re.search(r'"name"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_text)
            if not name:
                continue
            category = re.search(r'"category"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_text)
            min_size = re.search(r'"min"\s*:\s*(\d+)', obj_text)
            units[_unescape(name.group(1))] = {
                'category': _unescape(category.group(1)) if category else None,
                'min': int(min_size.group(1)) if min_size else None,
            }
        unit_info[fkey] = units
    return unit_info


def load_unit_info(fkey):
    '''Unit categories and minimum sizes for one faction, read from units.js.'''
    return _parse_units_js(UNITS_JS_PATH, os.path.getmtime(UNITS_JS_PATH)).get(fkey, {})


def attach_unit_info(unit_df, unit_info):
    '''Add 'Min Size' (from units.js) to the unit data and take 'Category' from units.js,
    falling back to the category stored in the data for units not found in units.js.'''
    info_df = pl.DataFrame(
        {
            'Name': list(unit_info.keys()),
            'JS Category': [v['category'] for v in unit_info.values()],
            'Min Size': [v['min'] for v in unit_info.values()],
        },
        schema={'Name': pl.Utf8, 'JS Category': pl.Utf8, 'Min Size': pl.Int64},
    )
    return (
        unit_df.join(info_df, on='Name', how='left')
        .with_columns(pl.coalesce(['JS Category', 'Category']).alias('Category'))
        .drop('JS Category')
    )


# ---------------------------------------------------------------------------
# Pricing rules (rules themselves live in constants.py)
# ---------------------------------------------------------------------------
def _rule_condition(rule, fkey):
    '''Polars expression that is true for option rows matching the rule, or None if the
    rule does not apply to this faction. Expects the columns Option Name, Option Type,
    Unit Name and Category.'''
    if 'factions' in rule and fkey not in rule['factions']:
        return None
    cond = pl.lit(True)
    if 'option_types' in rule:
        cond = cond & pl.col('Option Type').str.to_lowercase().is_in([t.lower() for t in rule['option_types']])
    if 'option_names' in rule:
        cond = cond & pl.col('Option Name').str.to_lowercase().is_in([n.lower() for n in rule['option_names']])
    if 'unit_names' in rule:
        cond = cond & pl.col('Unit Name').is_in(list(rule['unit_names']))
    if 'not_unit_names' in rule:
        cond = cond & ~pl.col('Unit Name').is_in(list(rule['not_unit_names']))
    if 'unit_categories' in rule:
        cond = cond & pl.col('Category').str.to_lowercase().is_in([c.lower() for c in rule['unit_categories']])
    return cond


def _any_rule(rules, fkey):
    '''True when any applicable rule matches.'''
    expr = pl.lit(False)
    for rule in rules:
        cond = _rule_condition(rule, fkey)
        if cond is not None:
            expr = expr | cond
    return expr


def _multiplier(rules, fkey):
    '''Product of the multipliers of all matching rules (1 if none match).'''
    expr = pl.lit(1, dtype=pl.Int64)
    for rule in rules:
        cond = _rule_condition(rule, fkey)
        if cond is not None:
            expr = pl.when(cond).then(expr * rule['multiplier']).otherwise(expr)
    return expr


def build_option_entries(unit_df, option_df, fkey):
    '''One row per option taken, with:
      Price Unit    - the unit the option is priced under, or FACTION_LEVEL
      Faction Level - whether the option is priced at the faction level
      Scale         - how many times a 1 point price change is paid for this row
                      (number of models unless priced per unit, times any multiplier)'''
    opts = (
        option_df
        .filter(pl.col('Option Name').is_not_null())
        .with_columns(pl.col('Option Type').fill_null(''))
        .filter(pl.col('Option Type') != 'Model Count')
        .select(['list_id', 'unit_id', 'Option Name', 'Option Type'])
        # Take the unit's name from the unit data (it has had its typos corrected)
        .join(
            unit_df.select(['list_id', 'unit_id', pl.col('Name').alias('Unit Name'), 'Category', 'Models']),
            on=['list_id', 'unit_id'], how='inner',
        )
        .with_columns(
            pl.col('Category').fill_null(''),
            pl.col('Models').fill_null(1).cast(pl.Int64),  # No model count = 1 model
        )
        # Options with no price are left out entirely
        .filter(~_any_rule(EXCLUDED_OPTION_RULES, fkey))
        .with_columns(
            _any_rule(FACTION_LEVEL_RULES, fkey).alias('Faction Level'),
            _any_rule(PER_UNIT_RULES, fkey).alias('Per Unit'),
            _multiplier(SCALE_MULTIPLIER_RULES, fkey).alias('Multiplier'),
        )
        .with_columns(
            pl.when(pl.col('Faction Level')).then(pl.lit(FACTION_LEVEL)).otherwise(pl.col('Unit Name')).alias('Price Unit'),
            (
                pl.when(pl.col('Per Unit')).then(pl.lit(1, dtype=pl.Int64)).otherwise(pl.col('Models'))
                * pl.col('Multiplier')
            ).alias('Scale'),
        )
    )
    return opts


def compute_list_impacts(unit_df, opts, flist_data, changes):
    '''Total point change for every list in flist_data.
    changes maps (price_unit, option_key) -> change in points, where price_unit is a unit
    name or FACTION_LEVEL and option_key is an option name, BASE_KEY or EXTRA_KEY.'''
    entry_cols = ['list_id', 'Price Unit', 'Option Name', 'Scale']

    # Base cost: once per unit taken
    base_costs = (
        unit_df.group_by(['list_id', pl.col('Name').alias('Price Unit')])
        .agg(pl.len().cast(pl.Int64).alias('Scale'))
        .with_columns(pl.lit(BASE_KEY).alias('Option Name'))
        .select(entry_cols)
    )

    # Extra models: models above the minimum size listed in units.js
    extra_models = (
        unit_df.filter(pl.col('Min Size').is_not_null() & pl.col('Models').is_not_null())
        .with_columns(
            pl.when(pl.col('Models') > pl.col('Min Size'))
            .then(pl.col('Models') - pl.col('Min Size'))
            .otherwise(0)
            .cast(pl.Int64)
            .alias('Extra')
        )
        .group_by(['list_id', pl.col('Name').alias('Price Unit')])
        .agg(pl.sum('Extra').cast(pl.Int64).alias('Scale'))
        .with_columns(pl.lit(EXTRA_KEY).alias('Option Name'))
        .filter(pl.col('Scale') > 0)
        .select(entry_cols)
    )

    # Options
    option_entries = (
        opts.group_by(['list_id', 'Price Unit', 'Option Name'])
        .agg(pl.sum('Scale').cast(pl.Int64).alias('Scale'))
        .select(entry_cols)
    )

    all_entries = pl.concat([base_costs, extra_models, option_entries])

    changes_df = pl.DataFrame(
        {
            'Price Unit': [k[0] for k in changes],
            'Option Name': [k[1] for k in changes],
            'Change': list(changes.values()),
        },
        schema={'Price Unit': pl.Utf8, 'Option Name': pl.Utf8, 'Change': pl.Int64},
    )

    list_impacts = (
        all_entries.join(changes_df, on=['Price Unit', 'Option Name'], how='inner')
        .with_columns((pl.col('Scale') * pl.col('Change')).alias('Point Delta'))
        .group_by('list_id')
        .agg(pl.sum('Point Delta').alias('Total Delta'))
    )

    # Merge with all lists (fill nulls with 0)
    return (
        flist_data.select(['list_id', 'Score', 'Total Points'])
        .join(list_impacts, on='list_id', how='left')
        .with_columns(pl.col('Total Delta').fill_null(0))
    )


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
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

    if flist_data.is_empty():
        st.warning("No lists found for this faction.")
        return

    try:
        unit_info = load_unit_info(fkey)
    except FileNotFoundError:
        st.error(f'Could not find units.js. It should be in the same folder as average_list_tool.py ({UNITS_JS_PATH}).')
        return

    valid_list_ids = flist_data['list_id'].unique().implode()
    funit_data = attach_unit_info(unit_data.filter(pl.col('list_id').is_in(valid_list_ids)), unit_info)
    foption_data = option_data.filter(pl.col('list_id').is_in(valid_list_ids))

    # Work out how each option is priced (faction level / per unit / per model)
    opts = build_option_entries(funit_data, foption_data, fkey)

    # Faction-level options grouped by Option Type. If an option name appears under more
    # than one type, it is shown once, under the type it appears under most often.
    name_to_type = {}
    for opt_type, opt_name, _ in (
        opts.filter(pl.col('Faction Level'))
        .group_by(['Option Type', 'Option Name']).len()
        .sort(['len', 'Option Type'], descending=[True, False])
        .iter_rows()
    ):
        name_to_type.setdefault(opt_name, opt_type)
    faction_options_by_type = defaultdict(list)
    for opt_name, opt_type in name_to_type.items():
        faction_options_by_type[opt_type].append(opt_name)

    unit_options = defaultdict(list)
    for unit_name, option_name in opts.filter(~pl.col('Faction Level')).select(['Unit Name', 'Option Name']).unique().iter_rows():
        unit_options[unit_name].append(option_name)

    # Group units by category: the categories in UNIT_CATEGORY_ORDER first, then the rest alphabetically
    unit_categories = dict(
        funit_data.select(['Name', 'Category']).unique(subset='Name', keep='first', maintain_order=True).iter_rows()
    )
    preferred = {c.lower(): c for c in UNIT_CATEGORY_ORDER}
    units_by_category = defaultdict(list)
    category_labels = {}
    for unit in sorted(unit_categories):
        category = (unit_categories[unit] or 'Other').strip()
        units_by_category[category.lower()].append(unit)
        category_labels.setdefault(category.lower(), preferred.get(category.lower(), category))
    category_order = [c.lower() for c in UNIT_CATEGORY_ORDER if c.lower() in units_by_category]
    category_order += sorted(c for c in units_by_category if c not in category_order)

    # Units with extra-model data but no minimum size in units.js can't have extra models priced
    units_with_models = funit_data.filter(pl.col('Models').is_not_null())['Name'].unique().to_list()
    missing_min = sorted(u for u in units_with_models if unit_info.get(u, {}).get('min') is None)

    st.markdown("### Point Adjustments Form")
    if missing_min:
        st.caption(
            'No minimum unit size was found in units.js for the following units, so their extra models '
            'cannot be adjusted: ' + ', '.join(missing_min)
        )

    with st.form("points_adjustment_form"):
        changes = {}

        st.markdown("#### Global Options")
        st.caption('These options are priced at the faction level: a change applies to every unit that took the option.')
        if not faction_options_by_type:
            st.caption('No faction-level options were taken in this faction\'s lists.')
        for opt_type in sorted(faction_options_by_type, key=str.lower):
            with st.expander(opt_type if opt_type else 'Other'):
                cols = st.columns(3)
                for i, opt in enumerate(sorted(faction_options_by_type[opt_type])):
                    with cols[i % 3]:
                        val = st.number_input(f"{opt}", value=0, step=1, key=f"global::{opt}")
                        if val != 0:
                            changes[(FACTION_LEVEL, opt)] = val

        st.markdown("#### Units & Unit Options")
        for category in category_order:
            st.markdown(f"##### {category_labels[category]}")
            for unit in units_by_category[category]:
                with st.expander(f"Unit: {unit}"):
                    min_size = unit_info.get(unit, {}).get('min')

                    # (label, key used in `changes`, help text)
                    fields = [('Base', BASE_KEY, None)]
                    if min_size is not None:
                        fields.append(('Extra Models', EXTRA_KEY, f'Applies to each model above the minimum unit size of {min_size}.'))
                    fields += [(opt, opt, None) for opt in sorted(unit_options.get(unit, []))]

                    u_cols = st.columns(3)
                    for i, (label, option_key, help_text) in enumerate(fields):
                        with u_cols[i % 3]:
                            val = st.number_input(label, value=0, step=1, key=f"unit::{unit}::{option_key}", help=help_text)
                            if val != 0:
                                changes[(unit, option_key)] = val

        submitted = st.form_submit_button("Calculate Point Changes")

    if submitted:
        if not changes:
            st.info("No point changes were entered.")
            return

        final_impacts = compute_list_impacts(funit_data, opts, flist_data, changes)

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
