import streamlit as st

# Helper colourmap function for text
@st.cache_data
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