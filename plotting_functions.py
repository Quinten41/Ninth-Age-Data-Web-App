import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker
import numpy as np
import textalloc as ta
from numba import jit



# Function to draw a heatmap
@jit(nopython=True)
def compute_heatmap(grid_res: int, xlim: tuple, ylim: tuple, num_games: int, mean: float, variance: float):
    '''
    Function to compute a heatmap.
    Outside the class so it can be compiled.
    '''
    xx = np.linspace(xlim[0], xlim[1], grid_res)
    yy = np.linspace(ylim[0], ylim[1], grid_res)
    zz = np.empty((grid_res, grid_res))
    for i in range(grid_res):
        y = yy[i]
        for j in range(grid_res):
            x = xx[j]
            if y == mean:
                zz[i, j] = 0
            elif x >= 100:
                zz[i, j] = 4
            else:
                zz[i, j] = min(4, abs(y - mean) * np.sqrt(x * num_games / 100) / np.sqrt(variance * (1 - (x * num_games / 100 - 1) / (num_games - 1))))
    return zz

def labelled_scatterplot_regions(points, labels, num_games, variance, mean, grid_res=300, xlim=None, ylim=None, x_error=None, y_error=None, figsize=(8, 6), **kwargs):
        '''
        Generates a seaborn scatterplot with non-overlapping text labels,
        superimposed on a heatmap generated from __compute_heatmap, and adds a z-score legend.
        '''
        if isinstance(points, tuple) and len(points) == 2 and all(isinstance(arr, list) for arr in points):
            x, y = points
        else:
            x, y = zip(*points)
        x = np.array(x) / num_games * 100  # Convert to percentage of games played
        y = np.array(y)
        if xlim is None:
            xlim = (max(x.min()-1,0), min(x.max()+1,100))
        if xlim[0] >= x.min():
            xlim = (max(x.min()-1,0), xlim[1])
        if xlim[1] <= x.max():
            xlim = (xlim[0], min(x.max()+1,100))

        if ylim is None:
            ylim = (y.min(), y.max())
        if ylim[0] >= y.min():
            ylim = (y.min()-.2, ylim[1])
        if ylim[1] <= y.max():
            ylim = (ylim[0], y.max()+.2)

        fig, ax = plt.subplots(figsize=figsize, layout="constrained")

        # Define a green-yellow-red colormap
        cmap = mcolors.LinearSegmentedColormap.from_list(
        'matte_green_yellow_red', ["#90ee90", "#fff479", "#ff5555"], N=256
        )
        norm = mcolors.Normalize(vmin=0, vmax=4)

        # Draw a heatmap
        im = ax.imshow(
            compute_heatmap(grid_res, xlim, ylim, num_games, mean, variance), 
            origin='lower', extent=(xlim[0], xlim[1], ylim[0], ylim[1]),
            aspect='auto', alpha=0.5, cmap=cmap, norm=norm
        )

        # Add a colorbar for z-score
        cbar = fig.colorbar(im, ax=ax, orientation='vertical', pad=0.02, aspect=30)
        cbar.set_label('$|z|$-score')
        
        sns.scatterplot(x=x, y=y, ax=ax, color = (.2,.2,.2), edgecolor = (.2,.2,.2), s = 25, **kwargs)

        # Add error bars if provided
        if x_error is not None:
            ax.errorbar(x, y, xerr=x_error, fmt='none', ecolor='white', alpha=0.25, capsize=3)
        if y_error is not None:
            ax.errorbar(x, y, yerr=y_error, fmt='none', ecolor='white', alpha=0.25, capsize=3)

        # Add labels to points using smart text allocation
        ta.allocate(ax,x,y,
            labels,
            x_scatter=x, y_scatter=y,
            textsize=10,
            linecolor='#333333', #rgb(.2,.2,.2)
            linewidth=0.5,
            min_distance=0.005,
            max_distance=0.015*len(labels),
            nbr_candidates = 11*len(labels) # Adjust the number of candidates to the expected difficulty
        )

        # Adjust foratting
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_xlabel(f'Percent of Games Played (Total Number of Games: {num_games})')
        ax.set_ylabel('Average Score')
        ax.grid(True,linestyle='-',color=(37/255,76/255,115/255), alpha=0.25)
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=100, decimals=0))

        return fig, ax

def scatterplot_with_errors(points, labels, xerr=None, yerr=None, figsize=(8, 6), xlabel='', ylabel='', title=''):
        """
        Scatterplot with labels and error bars, no region shading.
        """
        sns.set_theme()
        plt.style.use(['seaborn-v0_8','fast'])
        if isinstance(points, tuple) and len(points) == 2 and all(isinstance(arr, list) for arr in points):
            x, y = points
        else:
            x, y = zip(*points)
            x = np.array(x)
            y = np.array(y)
        fig, ax = plt.subplots(figsize=figsize, layout="constrained")
        # Scatter with error bars
        ax.errorbar(x, y, xerr=xerr, yerr=yerr, fmt='o', color='#DEAA46', ecolor='#DEAA46', alpha=0.8, capsize=0, markersize=6, elinewidth=0.5)

        # Set limits with some padding
        plt.xlim(min(x)-0.1*abs(max(x)-min(x)), max(x)+0.1*abs(max(x)-min(x)))
        plt.ylim(min(y)-0.1*abs(max(y)-min(y)), max(y)+0.1*abs(max(y)-min(y)))
        
        # Add labels using smartalloc for smart text allocation
        ta.allocate(ax,x,y,
            labels,
            x_scatter=x, y_scatter=y,
            textsize=10,
            linecolor='#254C73',
            textcolor='#254C73',
            linewidth=0.7,
            min_distance=0.0025,
            max_distance=0.3,
            nbr_candidates = 10*len(labels)
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)

        return fig, ax