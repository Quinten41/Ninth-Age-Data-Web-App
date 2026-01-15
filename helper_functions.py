import streamlit as st
from math import log, floor

from constants import faction_keys

# Functions for handling faction names
lower_to_correct = {key.lower(): key for key in faction_keys} # Dictionary to map lowercase keys to the correct capitalization
def correct_cap(key):
    '''Convert a given key to the correct capitalization as used in faction_keys.

    Args:
        key (str): The key to be converted.

    Returns:
        str: The key in the correct capitalization.
    '''
    return lower_to_correct[key.lower()]

# Helper colourmap function for text
def colourmap(value):
    '''
    Maps a value to an HSL colour string.
    0   -> green (hsl(120, 100%, 50%))
    2   -> yellow (hsl(60, 100%, 50%))
    ±4  -> red (hsl(0, 100%, 50%))
    '''
    # Clamp value to [-4, 4] then normalize to [0, 1]
    v = abs( max(-3.5, min(3.5, value) )) / 3.5
    # Map value to hue: -4 (red, 0), 0 (green, 120), 4 (red, 0)
    hue = 120 - 120*v*v*(3-2*v)  # Cubic easing for smoother transition
    return f'hsl({int(hue)}, 100%, {v*(1-v)*50+20}%)'

# Function to round a number and its error to correct number of significant digits
def round_sig(num, err):
    '''Round a number and its associated error to the appropriate significant digits.

    Args:
        num (float): The number to be rounded.
        err (float): The associated error of the number.

    Returns:
        tuple: A tuple containing the rounded number and its rounded error.
    '''
    # Find the number of significant digits in the error
    if err < 0:
        raise ValueError("The error must be a positive number to determine significant digits.")  
    elif err is None or err == 0:
        return (round(num, 2), 0)
    sig_dig = -floor( log( err, 10 ) )
    err = round( err, ndigits = sig_dig )
    sig_dig = -floor( log( err, 10 ) ) # We repeate this in case the first rounding changed the signifigant digits
    if sig_dig > 0:
        return ( round( num, ndigits = sig_dig ), round( err, ndigits = sig_dig ) )
    elif sig_dig == 0:
        return ( int(round( num, ndigits = sig_dig )), int(round( err, ndigits = sig_dig )) )
    else:
        return (int(round(num)), int(round(num)))
         