# Define a list for the factions
faction_keys = ['BH', 'DE', 'DH', 'DL', 'EoS', 'HE', 'ID', 'KoE', 'OK', 'OnG', 'SA', 'SE', 'UD', 'VC', 'VS', 'WDG']
num_faction = len(faction_keys) # Should be 16

# Full name list
# This should be in the same order as faction_keys in main_page.py
faction_names = ['Beast Herds', 'Dread Elves', 'Dwarven Holds',\
            'Demon Legions', 'Empire of Sonnstahl', 'Highborn Elves',\
            'Infernal Dwarves', 'Kingdom of Equitaine', 'Ogre Khans',\
            'Orcs and Goblins', 'Saurian Ancients', 'Sylvan Elves',\
            'Undying Dynasties', 'Vampire Covenant', 'Vermin Swarm',\
            'Warriors of the Dark Gods']


# ---------------------------------------------------------------------------
# Pricing exceptions for the Average List Tool
# (Source of truth: pricing_exceptions.txt)
#
# GENERIC RULE: an option is priced separately for each unit, and its price is
# paid once per model (units with no model count are treated as 1 model).
#
# Everything below describes exceptions to that rule. Each exception is a rule
# (a dict). A rule matches an option taken by a unit when ALL of the criteria it
# lists match; criteria that are left out are ignored.
#
#   'factions'        : faction keys the rule applies to (omit = every faction)
#   'option_types'    : matches if the option's "Option Type" EQUALS any of
#                       these strings (exact match, ignoring case)
#   'option_names'    : matches if the option's name EQUALS any of these
#                       (exact match, ignoring case)
#   'unit_names'      : matches only options taken by these units
#   'not_unit_names'  : never matches options taken by these units
#   'unit_categories' : matches only options taken by units in these categories
#                       (category is read from units.js)
#
# To change an exception, edit / add / remove a rule here; no code changes are
# needed in average_list_tool.py.
# ---------------------------------------------------------------------------

# Options that have no price and are left out of the tool entirely (they don't
# appear in the form and are ignored in the calculation).
EXCLUDED_OPTION_RULES = [
    # BH
    {'factions': ['BH'], 'option_types': ['Totems']},
]

# Options priced at the FACTION level: one price shared by every unit that took
# the option, instead of a separate price for each unit.
FACTION_LEVEL_RULES = [
    # Global
    {'option_types': ['Magic Items']},
    {'option_types': ['Command Group']},
    # DL: Manifestations are faction-level for Characters only. Every other unit
    # prices them at the unit level as normal.
    {'factions': ['DL'], 'option_types': ['Manifestations'], 'unit_categories': ['Characters']},
    # HE
    {'factions': ['HE'], 'option_types': ['Honour']},
    # OK
    {'factions': ['OK'], 'option_types': ['Big Name']},
    # SA
    {'factions': ['SA'], 'option_types': ['Howdah']},
    # SE
    {'factions': ['SE'], 'option_types': ['Kindred', 'Aspect of Nature']},
    # VC
    {'factions': ['VC'], 'option_types': ['Ancestral Blood Power', 'Blood Powers']},
]

# Options whose price is for the ENTIRE UNIT, not per model (the price change is
# NOT multiplied by the number of models in the unit).
PER_UNIT_RULES = [
    # Global
    {'option_types': ['Magic Items']},
    {'option_types': ['Command Group']},
    {'option_names': ['Wizard Conclave']},
    # BH
    {'factions': ['BH'], 'option_types': ['Totem Bearer']},
    # (Centaurs are an exception to this: their Ambush is priced per model)
    {'factions': ['BH'], 'option_names': ['Ambush'], 'not_unit_names': ['Centaurs']},
    # DE
    {'factions': ['DE'], 'option_names': ['Warlock Acolytes'], 'unit_names': ['Dread Acolytes']},
    # DL
    {'factions': ['DL'], 'option_names': ['Mark of the Eternal Champion', 'Sorcerous Antennae',
                                         'Unnatural Roots']},
    # KoE
    {'factions': ['KoE'], 'option_names': ['Solemn Oath', 'Knight Banneret', 'Prepared Position']},
    # OnG
    {'factions': ['OnG'], 'option_names': ['Herd', 'Dashers']},
    # VS
    {'factions': ['VS'], 'option_names': ['Bloodfur Praetorian', 'Tunnel Digger']},
]

# Rules that multiply the points impact of a price change. These rules take the
# same criteria as above plus a 'multiplier'.
SCALE_MULTIPLIER_RULES = [
    # WDG: price changes to Magic Items taken by the Feldrak Ancestor are doubled.
    {'factions': ['WDG'], 'unit_names': ['Feldrak Ancestor'], 'option_types': ['Magic Items'], 'multiplier': 2},
]


# ---------------------------------------------------------------------------
# Average List Tool display
# ---------------------------------------------------------------------------
# Unit categories shown first, in this order, in the Average List Tool form.
# Any other categories follow in alphabetical order (matching ignores case).
UNIT_CATEGORY_ORDER = ['Characters', 'Core', 'Special']
