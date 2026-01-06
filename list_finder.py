# Import Streamlit
import streamlit as st

# Plotting tools
import matplotlib.pyplot as plt
import seaborn as sns

# Data analysis tools
import polars as pl
import numpy as np
from scipy.stats import norm
from collections import Counter
import itertools as itr

# Math functions
from math import sqrt

# Full name list
from constants import faction_names, faction_keys

# Helper functions
from helper_functions import colourmap, round_sig

@st.fragment()
def list_finder_page(faction_keys, magic_paths, list_data, unit_data, option_data):
    ''' The content of the list finder page '''

    # The title of the page
    st.title('List Finder')

    # Add a description of the page
    st.markdown(f'''<p>This page allows you to select a faction and specify list and game details (units, options, opponents).
                    Then, it will display data on all the lists meeting these criteria along with the option to
                    display the lists themselves with the details of the game.</p>''', unsafe_allow_html=True)
    
    st.markdown('''<h5>Select Faction</h5><p>Select the faction you want to examine.</p>''', unsafe_allow_html=True)
        
    faction_name = st.selectbox('Select a Faction', faction_names, index=None)
    
    if faction_name == None:
        st.caption('Please select a faction using the widget above to display data.')
        return
    
    # Get the faction key
    fkey = faction_keys[ faction_names.index(faction_name) ]

    # Filter the data for the selected faction including only games that submitted lists
    flist_data = list_data.filter((pl.col('Faction') == fkey) & pl.col('List'))
    funit_data = unit_data.filter(pl.col('list_id').is_in(flist_data['list_id'].implode()))
    foption_data = option_data.filter(pl.col('list_id').is_in(flist_data['list_id']))

    num_faction_lists = flist_data.height
    avg_faction_lists = flist_data['Score'].mean()
    var_faction_lists = flist_data['Score'].var() if num_faction_lists > 1 else 0

    # Get all units for the selected faction
    available_units = sorted( funit_data['Name'].unique().to_list() )

    st.markdown('''<h5>Select Units</h5><p>Select units that must be included in the lists shown below.
                    Note that if the same unit is selected 'n' times only lists containing 'n' copies
                    of that unit will be shown. Once you have selected a unit, you can then specify any options
                    that unit must have and/or any options that unit can not have. If you do not specify any options, all lists containing the selected unit
                    will be shown. To remove a selected unit, click the 'x' in the far right of the appropriate selectbox.</p>''', unsafe_allow_html=True)

    selected_units = []
    selected_options = []
    banned_options = []
    selected_model_counts = []
    while True:
        st.markdown(f'<b>Selected Unit {len(selected_units) + 1}</b>', unsafe_allow_html=True)
        select_unit = st.selectbox(f'Select Unit Type', 
                                available_units,
                                key=f'unit_selectbox_{len(selected_units)}',
                                index=None
                                )
        if select_unit == None:
            break
        selected_units.append(select_unit)

        # If the unit has multiple model counts, allow the user to select a range
        try:
            model_counts = funit_data.filter(pl.col('Name') == select_unit)['Models'].unique().to_list()
            selected_model_counts.append(st.slider('Select Unit Size Range',
                                    min_value=min(model_counts),
                                    max_value=max(model_counts),
                                    value=(min(model_counts), max(model_counts)),
                                    key=f'size_slider_{len(selected_units)}'
                                    ))
            plural = True
        except:
            selected_model_counts.append(None)
            plural = False

        select_options = set(st.multiselect(
            f'Select Options {plural and "these" or "this"} {select_unit} MUST have',
            sorted( foption_data.filter((pl.col('Unit Name') == select_unit) & (pl.col('Option Type') != 'Model Count'))['Option Name'].unique().to_list() ),
            key=f'option_select_{len(selected_units)}'
        ))

        ban_options = set(st.multiselect(
            f'Select Options {plural and "these" or "this"} {select_unit} CAN NOT have',
            sorted( foption_data.filter((pl.col('Unit Name') == select_unit) & (pl.col('Option Type') != 'Model Count'))['Option Name'].unique().to_list() ),
            key=f'option_ban_{len(selected_units)}'
        ))

        if select_options.intersection(ban_options):
            st.error('You have selected the same option to be both required and banned. Please adjust your selections.')

        # Add the selected and banned options to the respective lists. These will be in the same order as the list selected_units.
        selected_options.append(select_options)
        banned_options.append(ban_options)

    st.markdown('''<h5>Select Opponents</h5><p>Use the multiselect below to specify the possible opponents' faction.</p>''', unsafe_allow_html=True)

    selected_opponents = st.multiselect(
        'Select Opponents',
        faction_keys,
        default=faction_keys,
        key=f'opponent_multiselect_{len(selected_units)}'
    )

    st.markdown('''<h5>Specify Turn Order</h5><p>Use the following selectbox to specify whether the lists should have gone
                first or second in the game. If "Any" is selected, lists from games where the faction went
                either first or second will be included.</p>''', unsafe_allow_html=True)
    
    turn_order = st.selectbox('Select Turn Order',
                            ['Any', 'First', 'Second'],
                            key='turn_order_selectbox')
    
    st.markdown('''<h5>Specify Deployment</h5><p>Use the multiselect below to filter the games by
                the deployment type. Note that the 'Unknown' option indicates games where no
                deployment information is available.</p>''', unsafe_allow_html=True)

    all_deployments = list_data['Deployment'].unique().to_list()
    deployment = st.multiselect('Select Deployment',
                            all_deployments,
                            default=all_deployments,
                            key='deployment_selectbox')

    st.markdown('''<h5>Specify Primary Deployment</h5><p>Use the multiselect below to filter the games by
                the primary deployment type. Note that the 'Unknown' option indicates games where no
                deployment information is available.</p>''', unsafe_allow_html=True)

    all_primaries = list_data['Primary'].unique().to_list()
    primary = st.multiselect('Select Primary',
                            all_primaries,
                            default=all_primaries,
                            key='primary__selectbox')

    # Now that all the criteria are selected the user is given the option to generate the data
    st.markdown('''<h5>Generate List Data</h5><p>Once you are happy with your selected criteria for the lists you wish to examine,
                click on the button below to find all the lists that meet the above specifications.</p>''',
                unsafe_allow_html=True)

    submit = st.button('Find Selected Lists', disabled=(faction_name is None))

    if submit:
        # First cut the size of the data down by filtering for turn order, deployment, primary, and selected opponents
        if turn_order == 'First':
            flist_data = flist_data.filter(pl.col('Turn') == 'First')
        elif turn_order == 'Second':
            flist_data = flist_data.filter(pl.col('Turn') == 'Second')
        if len(deployment) < len(all_deployments):
            flist_data = flist_data.filter(pl.col('Deployment').is_in(deployment))
        if len(primary) < len(all_primaries):
            flist_data = flist_data.filter(pl.col('Primary').is_in(primary))
        if len(selected_opponents) < len(faction_keys):
            flist_data = flist_data.filter(pl.col('Opponent').is_in(selected_opponents))

        # Get the valid list ids
        valid_list_ids = flist_data['list_id'].unique()

        # Now filter the unit and option data for these list ids
        funit_data = funit_data.filter(pl.col('list_id').is_in(valid_list_ids))
        foption_data = foption_data.filter(pl.col('list_id').is_in(valid_list_ids))

        # Sort the selected_units, selected_options, selected_model_counts, and banned_options so like units are next to each other
        perm, selected_units = map(list, zip( *sorted(enumerate(selected_units),key=lambda x: x[1]) ) )
        selected_options = [ selected_options[perm[i]] for i in range(len(selected_options)) ]
        selected_model_counts = [ selected_model_counts[perm[i]] for i in range(len(selected_model_counts)) ]
        banned_options = [ banned_options[perm[i]] for i in range(len(banned_options)) ]
        
        # Get required unit counts
        unit_counts = Counter(selected_units).items()
        # Get unit counts in the actual data
        unit_mults = (
            funit_data
            .group_by(['list_id', 'Name'])
            .agg(pl.count().alias('unit_count'))
        )
        valid_list_ids = funit_data['list_id'].unique()
        for unit, count in unit_counts:
            ids_with_enough = (
                unit_mults
                .filter((pl.col('Name') == unit) & (pl.col('unit_count') >= count))['list_id']
                .unique()
            )
            valid_list_ids = pl.Series(valid_list_ids).filter(pl.Series(valid_list_ids).is_in(ids_with_enough)).to_list()

        # Now filter the data for valid list ids
        flist_data = flist_data.filter(pl.col('list_id').is_in(valid_list_ids))
        funit_data = funit_data.filter(pl.col('list_id').is_in(valid_list_ids))
        foption_data = foption_data.filter(pl.col('list_id').is_in(valid_list_ids))

        # Next, filter for the selected options
        matched_list_ids = [] # List to store the lits that are matched to the selected and banned options
        for list_id in valid_list_ids:
            units_in_list = funit_data.filter(pl.col('list_id') == list_id)
            # For each unique unit name, get all unit_ids
            unit_id_assignments = []
            for unit_name, count in unit_counts:
                unit_ids = units_in_list.filter(pl.col('Name') == unit_name)['unit_id'].to_list()
                # Generate all possible assignments of unit_ids to the selected units of this name
                if len(unit_ids) >= count:
                    unit_id_assignments.append(list(itr.permutations(unit_ids, count)))
                else:
                    unit_id_assignments.append([])  # Not enough units, will fail

            # Now, for all possible combinations of assignments for all unit names
            for assignment in itr.product(*unit_id_assignments):
                # Flatten assignment to get the full unit_id list in the order of selected_units
                flat_unit_ids = []
                for group in assignment:
                    flat_unit_ids.extend(group)
                # Map flat_unit_ids to selected_units
                match = True
                for idx, unit_id in enumerate(flat_unit_ids):
                    required_options = selected_options[idx]
                    unit_options = set(foption_data.filter(pl.col('unit_id') == unit_id)['Option Name'].to_list())
                    if not required_options.issubset(unit_options) or unit_options.intersection(banned_options[idx]):
                        match = False
                        break
                    # Check model counts
                    if selected_model_counts[idx] is not None:
                        unit_size = funit_data.filter(pl.col('unit_id') == unit_id)['Models'][0]
                        if not (selected_model_counts[idx][0] <= unit_size <= selected_model_counts[idx][1]):
                            match = False
                            break
                if match:
                    matched_list_ids.append(list_id)
                    break  # Only need one valid assignment per list_id

        # Filter the data for valid list ids
        flist_data = flist_data.filter(pl.col('list_id').is_in(matched_list_ids))
        # Check if any lists remain
        if flist_data.is_empty():
            st.warning('No lists found matching the specified criteria. Please adjust your selections and try again.')
            return
        # If lists remain filter the unit and option data as well
        funit_data = funit_data.filter(pl.col('list_id').is_in(matched_list_ids))
        foption_data = foption_data.filter(pl.col('list_id').is_in(matched_list_ids))

        # Show the data on the filtered lists
        show_filtered_data(faction_name, matched_list_ids, flist_data, funit_data, foption_data, num_faction_lists, avg_faction_lists, var_faction_lists)

@st.fragment()
def show_filtered_data(faction_name, matched_list_ids, flist_data, funit_data, foption_data, num_faction_lists, avg_faction_lists, var_faction_lists):
    ''' Show data on the filtered lists '''    
    # Set the styles for the plots
    sns.set_theme()
    plt.style.use(['seaborn-v0_8','fast'])

    num_found = flist_data.height
    st.success(f'Found {num_found} lists matching the specified criteria from the {num_faction_lists} lists for {faction_name} in the dataset.')

    # Compute the average score and its error
    avg = flist_data['Score'].mean()
    std = flist_data['Score'].std() if num_found > 1 else 0
    err = std / sqrt(num_found) if std is not None else 0
    avg, err = round_sig(avg, err)
    colour = colourmap((avg - 10) / err if err != 0 else 0)

    # Now compute the descrepency from the internal results of the faction
    if (var_faction_lists * (1 - (num_found - 1) / (num_faction_lists - 1))) != 0:
        z_value = abs(avg - avg_faction_lists) * sqrt(num_found) / sqrt(var_faction_lists * (1 - (num_found - 1) / (num_faction_lists - 1)))
        p_value = (2 * norm.sf(abs(z_value))).round(4)  # Two-tailed p-value
        colour_p = colourmap(z_value)

        # Display the average score and some text explaining the histogram
        st.markdown(f'''<p>The average score of the selected lists is <span style="color:{colour};">{avg} ± {err}</span>. Comparing the average score of the selected lists
                    to the distribution of scores in all {faction_name} lists, we find a p-value for the obtained average of <span style="color:{colour_p};">{p_value}</span>
                    (recall that the average score for all {faction_name} lists is {avg_faction_lists:.1f}). The exact distribution of scores for
                    the selected lists is shown in the histogram below. The curvy horizontal line shows the kernel density estimate of the score distribution.
                    Intuitively, this is like a smoothed version of the histogram, providing a clearer view of the score distribution.</p>''', unsafe_allow_html=True)
    else:
        # Display the average score and some text explaining the histogram
        st.markdown(f'''<p>The average score of the selected lists is <span style="color:{colour};">{avg} ± {err}</span>. The exact distribution of scores 
                    for the selected lists is shown in the histogram below. The curvy horizontal line shows the kernel density estimate of the score distribution.
                    Intuitively, this is like a smoothed version of the histogram, providing a clearer view of the score distribution.</p>''', unsafe_allow_html=True)


    fig, ax = plt.subplots(layout='constrained')
    fig.patch.set_alpha(0.0)  # Figure background transparent
    ax.patch.set_alpha(0.0)   # Axes background transparent
    sns.histplot(flist_data.to_pandas(), x='Score', bins=np.linspace(-0.5,20.5,num=22), kde=True, ax=ax, line_kws={'color':'black', 'linewidth':3})
    ax.set_title(f'Score Distribution of {faction_name} Lists Matching Criteria')
    ax.set_xlabel('Score')
    ax.set_ylabel('Number of Lists')
    ax.axvline(avg,label='Mean', linestyle='--', color='black')
    if isinstance(std, (int, float)):
        ax.axvline(avg+std,label='+1 Standard Deviation', linestyle=':', color='green')
        ax.axvline(avg-std,label='-1 Standard Deviation', linestyle=':', color='red')
    ax.legend(loc='upper right')

    st.pyplot(fig)
    plt.close(fig)

    st.markdown('''<p>You can see the details of the selected lists, by using the selectbox below to 
                choose a list. This will display the actual list, along with some details about the game in which
                it was played. The list number shown in the selectbox is the list ID in the whole dataset
                (i.e., including all factions).</p>''', unsafe_allow_html=True)

    # Create strings of the form "List {list_id}" for the selectbox
    valid_list_strings = [f'List {lid}' for lid in sorted( matched_list_ids )]
    selected_list_string = st.selectbox('Select a List to View Details', valid_list_strings, key='list_details_selectbox')
    id = int(selected_list_string.split(' ')[1])
    # Get the data for this list
    this_list = flist_data.filter(pl.col('list_id') == id).to_dicts()[0]
    these_units = funit_data.filter(pl.col('list_id') == id)
    these_options = foption_data.filter(pl.col('list_id') == id)

    # Print some overall stats
    st.markdown(f'''<h4>Game Details</h4><ul>
                <li>Date: {this_list['Start Date']}</li>
                <li>Tournament Size: {this_list['Tournament Size']}</li>
                <li>Game Size: {this_list['Game Size']}</li>
                <li>Opponent's Faction: {faction_names[faction_keys.index(this_list['Opponent'])]}</li>
                <li>Turn: {this_list['Turn']}</li>
                <li>Deployment: {this_list['Deployment']}</li>
                <li>Primary: {this_list['Primary']}</li>
                <li>Score: {this_list['Score']}</li>
                <li>Number of Units: {these_units.height}</li>
                <li>List Points: {this_list['Total Points']}</li>
                ''', unsafe_allow_html=True)
    
    st.markdown('<h4>List Composition</h4>', unsafe_allow_html=True)

    # Get and sort the categories to have Characters, Core, Special first
    priority = ['Characters', 'Core', 'Special']
    categories = these_units['Category'].unique().to_list()
    categories = [cat for cat in priority if cat in categories] + [cat for cat in categories if cat not in priority]

    # Display the list
    for cat in categories:
        st.markdown(f'''<h5>{cat}</h5><ul>''', unsafe_allow_html=True)
        units = these_units.filter(pl.col('Category') == cat)
        for unit in units.to_dicts():
            uoptions = these_options.filter((pl.col('unit_id') == unit['unit_id'])&(pl.col('Option Type') != 'Model Count'))['Option Name'].to_list()
            option_list = ', '+', '.join(uoptions) if uoptions else ''
            if 'Models' in unit and unit['Models'] is not None:
                st.markdown(f'''<li><b>{unit['Models']} {unit['Name']}</b>{option_list} - {unit['Cost']}</li>''', unsafe_allow_html=True)
            else:
                st.markdown(f'''<li><b>{unit['Name']}</b>{option_list} - {unit['Cost']}</li>''', unsafe_allow_html=True)
        st.markdown('</ul>', unsafe_allow_html=True)

        
