from bokeh.plotting import *
from bokeh.models import (HoverTool, CrosshairTool, PanTool, WheelZoomTool, ColumnDataSource, FactorRange)
from bokeh.resources import INLINE
from bokeh.embed import (components, server_document)
from bokeh.transform import factor_cmap
from bokeh.palettes import Category20
from bokeh.core.properties import value
from bokeh.transform import dodge
from bokeh.models import Select
from bokeh.layouts import row, column
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Slider
from bokeh.plotting import figure
import numpy as NP
import pandas
import random
from datetime import datetime as DT
import re
import csv

def modify_doc(doc):
    lab_names = ['AMDL', 'TGH']
    project_names = ['OCP', 'AGILE', 'OCTANE', 'IDH']

    current_lab_name = lab_names[0]
    current_project_name = project_names[0]

    data_dir = 'data'
    csv = './'+ data_dir + '/' + current_lab_name + '_' + current_project_name + '.csv'

    data = prep_data(csv)
    fig = make_plot(data)

    lab_select = Select(value=current_lab_name, title='Lab', options=lab_names, width=120)
    project_select = Select(value=current_project_name, title='Project', options=project_names, width=120)

    def callback(attr, old, new):
        current_lab_name = lab_select.value
        current_project_name = project_select.value
        csv = './'+ data_dir + '/' + current_lab_name + '_' + current_project_name + '.csv'

        data = prep_data(csv)
        fig = make_plot(data)
        controls = row(lab_select,project_select)

        doc.clear()   
        doc.add_root(column(controls,fig))

    lab_select.on_change('value', callback)
    project_select.on_change('value', callback)

    controls = row(lab_select,project_select)    
    doc.add_root(column(controls,fig))


def prep_data(csv):
    # load pandas dataframe
    df =pandas.read_csv(csv)

    # find all range of reported years and months
    dateReported_col_str = 'Date Reported'
    dt_series = df[dateReported_col_str].map(lambda string: DT.strptime(string, '%Y-%m-%d'))
    years = dt_series.map(lambda dt: dt.year).unique().tolist()
    months = range(1,13)

    # find all stage names (ex. Rec>Ext)
    regex = re.compile(r'^\w\w\w+>\w\w\w+$')
    df_colNames = df.axes[1]
    stages = filter(regex.search, df_colNames)

    # prep plot source data:
    data = {}

    # y-data:
    nodata_stages = [] # stages with nodata are to be removed from plotting

    for stage in stages:
        medians = []
        for year in years:
            for month in months:
                logical_idx = dt_series.map(lambda dt: (dt.year == year) & (dt.month == month))
                counts = df.loc[logical_idx, stage] # filter by logical index
                medians.append(counts.median())
        if NP.all(NP.isnan(medians)):
            nodata_stages.append(stage)
        else:
            data[stage] = medians


    # remove stages with no data
    [ stages.remove(stage) for stage in nodata_stages ]

    # find max median data
    max_median = NP.nanmax([ NP.nanmax(data[stage]) for stage in stages ])

    # x-data:
    years_months = [(str(year), str(month)) for year in years for month in months]
    data['x'] = years_months

    return data

def make_plot(data):

    stages = data.keys()
    stages.remove('x')

    # prepare bar plot fill colors
    stages_palette = Category20[20][0:len(stages)]

    switch =2
    if switch==1:

        # generate plot
        fig = figure(x_range=FactorRange(*data['x']), 
                     plot_height=350,plot_width=600,
                     tools='xpan,xwheel_zoom',)

        bar_thickness = 0.8
        bar_width = ( float(1) / (len(stages)+1) ) * bar_thickness
        bar_position = NP.array( range(0,len(stages)) )
        bar_position = bar_position /float(bar_position[-1]+2)
        bar_position += bar_width / 2

        # vbar = fig.vbar_stack(stages,x='x', width = 0.5, source=data, color=stages_palette,legend=stages)

        for idx in range(0,len(stages)):
            vbar = fig.vbar(x=dodge('x',bar_position[idx],range=fig.x_range), top=stages[idx], 
                     width=bar_width, source=data, color=stages_palette[idx],legend=value(stages[idx]))

        fig.y_range.start = 0
        fig.y_range.range_padding = 0.1
        fig.xaxis.major_label_orientation = 1
        fig.xgrid.grid_line_color = 'black'
        fig.xgrid.grid_line_alpha = 0.2
        fig.xgrid.grid_line_dash = [6, 4]

        fig.ygrid.minor_grid_line_color = 'black'
        fig.ygrid.minor_grid_line_alpha = 0.05

        fig.legend.orientation = "vertical"
        fig.legend.location = "top_right"

        tooltips = [(stage,'@{'+stage+'}') for stage in stages]

        fig.add_tools(HoverTool(
            tooltips=tooltips,
            mode='vline'
        ))

    elif switch==2:

        # 
        div_width = 600
        div_height = 600

        plot_height = int( (float(div_height) / len(stages)) )
        plot_width = div_width

        figs = []

        for idx in range(0,len(stages)):
            
            if idx == 0:
                fig = figure(x_range=FactorRange(*data['x']), 
                             plot_height=plot_height,plot_width=plot_width,
                             tools='',)
                fig.xaxis.visible = True if len(stages) == 1 else False
            if (0<idx) and (idx<len(stages)-1):
                fig = figure(x_range=figs[0].x_range, 
                             plot_height=plot_height,plot_width=plot_width,
                             tools='',)
                fig.xaxis.visible = False
            elif idx == len(stages)-1:
                fig = figure(x_range=figs[0].x_range, 
                             plot_height=plot_height,plot_width=plot_width,
                             tools='',)
                fig.xaxis.visible = True

            fig.y_range.start = 0
            fig.y_range.range_padding = 1
            # fig.y_range.end = max_median*1.25
            
            fig.xaxis.axis_line_width = 1
            fig.yaxis.axis_line_width = 1

            fig.yaxis.axis_label = stages[idx]
            fig.yaxis.axis_label_standoff = 10
            fig.yaxis.axis_label_text_font_size = '1em'
            fig.yaxis.minor_tick_line_alpha = 0

            fig.xaxis.major_label_orientation = 1
            fig.xgrid.grid_line_color = 'black'
            fig.xgrid.grid_line_alpha = 0.2
            fig.xgrid.grid_line_dash = [6, 4]

            fig.legend.orientation = "vertical"
            fig.legend.location = "top_right"

            fig.outline_line_width = 2
            fig.outline_line_alpha = 0.1
            fig.outline_line_color = "black"
            
            fig.add_tools(WheelZoomTool(dimensions='width'))
            fig.add_tools(PanTool(dimensions='width'))
            fig.add_tools(CrosshairTool(line_alpha=0.3))
            fig.add_tools(HoverTool(
                tooltips=[(stages[idx],'@{'+stages[idx]+'}')],
                mode='vline'
                ))

            vbar = fig.vbar(x=dodge('x',0.4,range=fig.x_range), top=stages[idx], 
                     width=0.8, source=data, color=stages_palette[idx])
        
            figs.append(fig)

        
        fig = gridplot([[fig] for fig in figs], sizing_mode='fixed', merge_tools=True, toolbar_location='right')

    return fig
