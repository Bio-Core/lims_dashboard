from bokeh.plotting import *
from bokeh.models import HoverTool, CrosshairTool, PanTool, WheelZoomTool, ColumnDataSource, FactorRange
from bokeh.palettes import Category20 # color palette
from bokeh.core.properties import value
from bokeh.transform import dodge
from bokeh.models import Select
from bokeh.layouts import row, column
from bokeh.layouts import column
from bokeh.plotting import figure
import numpy as NP
import pandas
from datetime import datetime as DT
from collections import defaultdict
import re # regular expression module
from math import log10
import itertools
from common_functions import setattrs

def modify_doc(doc):
    """
    Function to be registered into bokeh application server thread
    """

    def year_callback(attr, old, new):
        current_year = int(new)

        month_select.options = map(str, availData_tree[current_year].keys())
        month_select.value = str(availData_tree[current_year].keys()[0])

        std_select.options = map(str, availData_tree[current_year][current_month].keys())
        std_select.value = str(availData_tree[current_year][current_month].keys()[0])

        refreshDoc_callback()

    def month_callback(attr, old, new):
        current_month = int(new)

        std_select.options = map(str, availData_tree[current_year][current_month].keys())
        std_select.value = str(availData_tree[current_year][current_month].keys()[0])

        refreshDoc_callback()

    def std_callback(attr, old, new):
        std_select.value = str(new)
        refreshDoc_callback()

    def refreshDoc_callback():
        fig = plot_data(prep_data(int(year_select.value),int(month_select.value),int(std_select.value)))
        controls = row(year_select, month_select, std_select)

        doc.clear()
        doc.add_root(column(controls,fig))

    # options and values for dropdown menu (must be converted to strings from int)
    year_opts = map(str, availData_tree.keys())
    current_year_opt = str(current_year)
    month_opts = map(str, availData_tree[current_year].keys())
    current_month_opt = str(current_month)
    std_opts = map(str, availData_tree[current_year][current_month].keys())
    current_std_opt = str(current_std)

    # create dropdown menu
    year_select = Select(value=current_year_opt, title='Year', options=year_opts, width=80)
    month_select = Select(value=current_month_opt, title='Month', options=month_opts, width=80)
    std_select = Select(value=current_std_opt, title='Standard', options=std_opts, width=80)
    
    # register callback function to call upon change detected in dropwdown menu
    year_select.on_change('value', year_callback)
    month_select.on_change('value', month_callback)
    std_select.on_change('value', std_callback)
    
    refreshDoc_callback()

def prep_data(year, month, std):
    """
    Prepare log10_IS data to be plotted given a year, month, standard input
    """

    # NOTE: only preps p210 data for now

    std2_idx = availData_tree[year][month][std]['std2_idx']
    std3_idx = availData_tree[year][month][std]['std3_idx']
    data_idx = availData_tree[year][month][std]['data_idx']

    # get std ranges
    std2_rngs = df.loc[std2_idx,p210_all_cols].map(lambda string: re.findall(r'^(\d+\.\d+) - (\d+\.\d+)$', string))
    std2_rngs = std2_rngs.map(lambda tuple_list: tuple(itertools.chain.from_iterable(tuple_list))) # flatten tuples
    std2_rngs = std2_rngs.drop(p210_all_cols[2])
    std2_rngs = std2_rngs.drop(p210_all_cols[4])
    std2_rngs = std2_rngs.map(lambda tuple: (-log10(float(tuple[0])/100),-log10(float(tuple[1])/100)) )

    std3_rngs = df.loc[std3_idx,p210_all_cols].map(lambda string: re.findall(r'^(\d+\.\d+) - (\d+\.\d+)$', string))
    std3_rngs = std3_rngs.map(lambda tuple_list: tuple(itertools.chain.from_iterable(tuple_list))) # flatten tuples
    std3_rngs = std3_rngs.drop(p210_all_cols[2])
    std3_rngs = std3_rngs.drop(p210_all_cols[4])
    std3_rngs = std3_rngs.map(lambda tuple: (-log10(float(tuple[0])/100),-log10(float(tuple[1])/100)) )

    # prep data
    def apply_logOfIS(string):
        try:
            return -log10(float(string)/100)
        except Exception as e:
            return None

    # append empty dataframe
    raw_data = df.loc[data_idx,p210_all_cols].applymap(apply_logOfIS).reset_index(drop=True)
    empty_arr = NP.empty((len(raw_data)))
    empty_arr[:] = NP.NAN
    empty_df = pandas.DataFrame({col: empty_arr for col in p210_all_cols})

    # merge data columns
    data = raw_data.append(pandas.DataFrame(empty_df), ignore_index=True)
    data[p210_all_cols[1]] = raw_data[p210_all_cols[1]].append(raw_data[p210_all_cols[2]], ignore_index=True)
    data = data.drop(p210_all_cols[2],axis=1)
    data = data.drop(p210_all_cols[4],axis=1)

    # append std data
    for col in p210_existing_cols:
        data[col+'_std2_down'] = [std2_rngs[col][0]]*len(data)
        data[col+'_std2_up'] = [std2_rngs[col][1]]*len(data)
        data[col+'_std3_down'] = [std3_rngs[col][0]]*len(data)
        data[col+'_std3_up'] = [std3_rngs[col][1]]*len(data)

    return data

def plot_data(data):
    """
    Generate a plot based on the data produced by prep_data()
    """

    fig = figure(plot_height=600,plot_width=600,tools='')

    palette = {p210_existing_cols[idx]:Category20[20][idx] for idx in range(0,len(p210_existing_cols))}

    for col in p210_existing_cols:
        y = data[col].dropna()
        fig.multi_line(
            xs=[range(0,len(data))]*3,
            ys=[y,data[col+'_std2_down'],data[col+'_std2_up']],
            color=palette[col], legend=col)
        fig.circle(
            x=range(0,len(y)),
            y=y,
            size=5,
            color=palette[col], legend=col)

    setattrs(fig.xaxis, axis_label=pcr_col_str)
    setattrs(fig.yaxis, axis_label='Log10 of IS', axis_label_standoff=10)

    setattrs(fig.xgrid, minor_grid_line_color='black', minor_grid_line_alpha=0.05)
    setattrs(fig.ygrid, minor_grid_line_color='black', minor_grid_line_alpha=0.05)

    setattrs(fig.legend, background_fill_alpha=0.5)

    hover = HoverTool(tooltips=[('y', '@y')],mode='vline')
    crosshair = CrosshairTool(line_alpha=0.3)

    fig.add_tools(hover, crosshair)
    fig.toolbar_location=None

    return fig


#====[ Initialzations ]====#

# load csv file to dataframe
current_project_name = 'BCR_ABL'
data_dir = 'data'
csv = './'+ data_dir + '/' + 'QC' + '_' + current_project_name + '.csv'
df = pandas.read_csv(csv)

# parse dataframe column indices
p210_all_cols = list(df.columns)[4:10]
p190_cols = list(df.columns)[11:-2]

p210_drop_cols = [p210_all_cols[2],p210_all_cols[4]]
p210_existing_cols = list(set(p210_all_cols)-set(p210_drop_cols))

# parse all available dates
date_col_str = 'Date'
dt_series = df[date_col_str].map(lambda string: DT.strptime(string, '%Y-%m'))
years = dt_series.map(lambda dt: dt.year).unique().tolist()

# build tree with info on all available year, month, and standards, and their data dataframe indices
def Tree(): return defaultdict(Tree)

availData_tree = Tree()
pcr_col_str = 'PCR#'
for year in years :
    year_TFidx = dt_series.map(lambda dt: dt.year == year)
    months = dt_series[year_TFidx].map(lambda dt: dt.month).unique().tolist()

    for month in months :
        month_TFidx = dt_series.map(lambda dt: dt.month == month)

        std2_TFidx = df[pcr_col_str][month_TFidx].map(lambda string: string.find('Mean+/-2Std') >= 0)
        std3_TFidx = df[pcr_col_str][month_TFidx].map(lambda string: string.find('Mean+/-3Std') >= 0)
        std2_idx = df[pcr_col_str][month_TFidx].index[std2_TFidx].tolist()
        std3_idx = df[pcr_col_str][month_TFidx].index[std3_TFidx].tolist()
        
        data_idx = NP.split(std2_TFidx , NP.where(std2_TFidx == True)[0].tolist())
        data_idx.pop(0)
        data_idx = map(lambda pdseries: pdseries.index.tolist(),data_idx)
        data_idx = map(lambda lst: lst[2:] ,data_idx)
        
        for std in range(0,len(std2_idx)) :
            availData_tree[year][month][std] = {
                'std2_idx':std2_idx[std],
                'std3_idx':std3_idx[std],
                'data_idx':data_idx[std]
            }

# default parameters
current_year = int(availData_tree.keys()[0])
current_month = int(availData_tree[current_year].keys()[0])
current_std = int(availData_tree[current_year][current_month].keys()[0])

