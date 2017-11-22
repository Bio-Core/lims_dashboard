from bokeh.plotting import *
from bokeh.models import HoverTool, CrosshairTool, PanTool, WheelZoomTool, ColumnDataSource, FactorRange, Select, Slider, Button, Div, DateRangeSlider
from bokeh.palettes import Category20 # color palette
from bokeh.core.properties import value
from bokeh.transform import dodge
from bokeh.layouts import row, column, layout, Spacer
from bokeh.plotting import figure
from bokeh.models.callbacks import CustomJS
import numpy as NP
import pandas
from datetime import datetime as DT
import re # regular expression module
from pymongo import MongoClient
from functools import reduce

# parameters
dateReported_col_str = 'Date Reported'
plot_switch = 1 # 1 or 2
fig_width = 600
fig_height = 350

# global dfs
passed_df = pandas.DataFrame(); qcfailed_df = pandas.DataFrame(); delayed_df = pandas.DataFrame()

def modify_doc(doc):

    # top first row controls
    lab_select = Select(value=current_lab_name, title='Lab', options=lab_names,width=140)
    project_select = Select(value=current_project_name, title='Project', options=selection_names,width=140)

    # top second row controls
    overall_year_select = Select(value=overall_current_year, title='Year', options=overall_avail_dates_dict.keys(),width=140)
    overall_month_select = Select(value=overall_current_month, title='Month', options=overall_avail_dates_dict[overall_current_year],width=140)

    # bottom row downloadable sheets
    download_div = Div(text='Downloadable Datasheet: ', width=180)
    passed_dwnld_bttn = Button(label='Passed', width=80)
    qcfailed_dwnld_bttn = Button(label='QC Failed', width=80)
    delayed_dwnld_bttn = Button(label='Delayed', width=80)

    def refreshDoc_callback(attr, old, new):
        current_lab_name = lab_select.value
        current_project_name = project_select.value
        overall_current_year = str(overall_year_select.value)
        overall_current_month = str(overall_month_select.value)
        overall_month_select.options = overall_avail_dates_dict[overall_current_year]

        if current_project_name == 'Overall':
            controls = row(children=[lab_select, Spacer(width=20), project_select, Spacer(width=40), overall_year_select, Spacer(width=20), overall_month_select])
            overall_data = prep_overall_data(overall_current_year ,overall_current_month)
            fig = make_overall_fig(overall_data)
            downloads = row(Spacer())
        else: # individual project
            controls = row(children=[lab_select, Spacer(width=20), project_select])
            global passed_df, qcfailed_df, delayed_df
            project_data, passed_df, qcfailed_df, delayed_df = prep_project_data(current_project_name)
            fig = make_project_fig(project_data)
            filename_prefix = '['+current_lab_name+']['+current_project_name+'][entire_history]'
            passed_dwnld_bttn.callback = CustomJS(args=dict(source=ColumnDataSource(
                data={'filename': [filename_prefix+'_passed.csv'], 
                      'csv_str':[passed_df.to_csv(index=False).replace('\\n','\\\n')]})), 
                code=download_js)
            qcfailed_dwnld_bttn.callback = CustomJS(args=dict(source=ColumnDataSource(
                data={'filename': [filename_prefix+'_qcfailed.csv'], 
                      'csv_str':[qcfailed_df.to_csv(index=False).replace('\\n','\\\n')]})), 
                code=download_js)
            delayed_dwnld_bttn.callback = CustomJS(args=dict(source=ColumnDataSource(
                data={'filename': [filename_prefix+'_delayed.csv'], 
                      'csv_str':[delayed_df.to_csv(index=False).replace('\\n','\\\n')]})), 
                code=download_js)
            downloads = row(download_div, passed_dwnld_bttn, Spacer(width=25), qcfailed_dwnld_bttn, Spacer(width=25), delayed_dwnld_bttn)    
        
        doc.clear()
        doc.add_root(column(controls,fig,downloads))

    download_js = """
        var data = source.get('data')
        var filename = data['filename'][0]
        var csv_str = data['csv_str'][0]
        var blob = new Blob([csv_str], { type: 'text/csv;charset=utf-8;' })

        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, filename)
        } else {
            var link = document.createElement("a")
            if (link.download !== undefined) { // feature detection
                // Browsers that support HTML5 download attribute
                var url = URL.createObjectURL(blob)
                link.setAttribute("href", url)
                link.setAttribute("download", filename)
                link.style.visibility = 'hidden'
                document.body.appendChild(link)
                link.click()
                document.body.removeChild(link)
        }}"""

    lab_select.on_change('value', refreshDoc_callback)
    project_select.on_change('value', refreshDoc_callback)
    overall_year_select.on_change('value', refreshDoc_callback)
    overall_month_select.on_change('value', refreshDoc_callback)

    # initialize document by forcing callback once in the beginning
    refreshDoc_callback(None, None, None) 

def prep_overall_data(overall_current_year,overall_current_month):
    
    target_x = (overall_current_year, overall_current_month)

    project_datas = map(lambda project_name: (project_name, prep_project_data(project_name)[0]), project_names)

    def filter(project_data):
        idx = project_data['x'].index(target_x)
        data = map(lambda stage: project_data[stage][idx], stages)
        return data
            
    overall_data = dict(map(lambda (project_name, project_data): (project_name, filter(project_data)), project_datas))
    overall_data['x'] = stages

    return overall_data

def make_overall_fig(overall_data):
    
    # color palette
    projects_palette = Category20[20][0:len(stages)]

    # create figure
    fig = figure(x_range=FactorRange(*overall_data['x'], range_padding=0.2),
                 plot_width=fig_width, plot_height=fig_height, tools='',
                 x_axis_label='Stages', y_axis_label='Median')

    # plot bar attributes
    bar_thickness = 1.0
    bar_width = ( float(1) / (len(project_names)+1) ) * bar_thickness
    bar_pos = NP.array(range(0,len(project_names)))
    bar_pos = bar_pos - NP.median(bar_pos)
    bar_pos = bar_pos / len(bar_pos) / 1.2

    # draw plots
    for idx in range(0,len(project_names)):
        vbar = fig.vbar(x=dodge('x',bar_pos[idx],range=fig.x_range), top=project_names[idx],
            width=bar_width, source=overall_data, color=projects_palette[idx], legend=value(project_names[idx]))

    # figure attributes
    setattrs(fig.xaxis, axis_label_standoff=10)
    setattrs(fig.xgrid, grid_line_color='black', grid_line_alpha=0.2, grid_line_dash=[6,4])

    setattrs(fig.yaxis, axis_label_standoff = 10)
    setattrs(fig.y_range, start=0, range_padding=0.5)
    setattrs(fig.ygrid, minor_grid_line_color='black', minor_grid_line_alpha=0.05)

    setattrs(fig.legend, orientation='vertical', location='top_left')
    
    # toolbar
    spanTags = map(lambda (project_color,project_name): 
                  '<div><span style="color:'+project_color+';">'+project_name+': <b>@{'+project_name+'}</b></span></div>', 
                  zip(projects_palette, project_names))
    divContent = reduce(lambda accm,string: accm+string, spanTags)
    tooltips = '<div>'+divContent+'</div>'

    hover = HoverTool(tooltips=tooltips,mode='vline')
    
    fig.add_tools(hover)
    fig.toolbar_location=None

    return fig

def prep_project_data(current_project_name):

    # load db data into pandas dataframe
    cursor = db[current_project_name].find()
    df = pandas.DataFrame(list(cursor))

    # find all range of reported years and months
    dt_series = df[dateReported_col_str].map(lambda string: DT.strptime(string, '%Y-%m-%d'))
    years = dt_series.map(lambda dt: dt.year).unique().tolist()
    months = range(1,13)

    # filter QC failed & delayed data
    qcfailed_idx = (df['QC status'] == 'True')
    qcfailed_df = df.where(qcfailed_idx).dropna()
    passed_df = df.mask(qcfailed_idx).dropna()

    delayed_idx = (passed_df['Rec>Rep'] > 50)
    delayed_df = passed_df.where(delayed_idx).dropna()
    passed_df = passed_df.mask(delayed_idx).dropna()

    # where plot source data will be prepped
    project_data = {}
    
    # y-data:
    nodata_stages = [] # stages with nodata are to be removed from plotting
    
    for stage in stages:
        medians = []
        for year in years:
            for month in months:
                logical_idx = dt_series.map(lambda dt: (dt.year == year) & (dt.month == month))
                counts = passed_df.loc[logical_idx, stage] # filter by logical index
                medians.append(counts.median())
        if NP.all(NP.isnan(medians)):
            nodata_stages.append(stage)
        else:
            project_data[stage] = medians
    
    # remove stages that have no data
    [ stages.remove(stage) for stage in nodata_stages ]
    
    # find max median data
    max_median = NP.nanmax([ NP.nanmax(project_data[stage]) for stage in stages ])
    
    # x-data:
    years_months = [(str(year), str(month)) for year in years for month in months]
    project_data['x'] = years_months
    
    return project_data, passed_df, qcfailed_df, delayed_df

def make_project_fig(project_data):
    
    # color palette
    stages_palette = Category20[20][0:len(stages)]
    
    if plot_switch==1:

        # create figure
        fig = figure(x_range=FactorRange(*project_data['x']), 
                     plot_width=fig_width,plot_height=fig_height, tools='',
                     x_axis_label='Year-Month', y_axis_label='Median')

        # plot bar attributes
        bar_thickness = 0.8
        bar_width = ( float(1) / (len(stages)+1) ) * bar_thickness
        bar_pos = NP.array( range(0,len(stages)) )
        bar_pos = bar_pos /float(bar_pos[-1]+2)
        bar_pos += bar_width / 2

        # draw plots
        # vbar = fig.vbar_stack(stages,x='x', width = 0.5, source=project_data, color=stages_palette,legend=stages)
        for idx in range(0,len(stages)):
            vbar = fig.vbar(x=dodge('x',bar_pos[idx],range=fig.x_range), top=stages[idx], 
                     width=bar_width, source=project_data, color=stages_palette[idx], legend=value(stages[idx]))

        # figure attributes
        setattrs(fig.xaxis, axis_label_standoff=10, major_label_orientation=1)
        setattrs(fig.xgrid, grid_line_color = 'black', grid_line_alpha = 0.2, grid_line_dash = [6,4])

        setattrs(fig.yaxis, axis_label_standoff=10)
        setattrs(fig.y_range, start=0, range_padding=0.5)
        setattrs(fig.ygrid, minor_grid_line_color='black', minor_grid_line_alpha=0.05)

        setattrs(fig.legend, orientation='vertical', location='top_right')

        # toolbar
        # tooltips = [(stage,'@{'+stage+'}') for stage in stages]
        spanTags = map(lambda (stage_color,stage): '<div><span style="color:'+stage_color+';">'+stage+': <b>@{'+stage+'}</b></span></div>', zip(stages_palette, stages))
        divContent = reduce(lambda accm,string: accm+string, spanTags)
        tooltips = '<div>'+divContent+'</div>'

        hover = HoverTool(tooltips=tooltips,mode='vline')
        wheelzoom = WheelZoomTool(dimensions='width')
        pan = PanTool(dimensions='width')
        crosshair = CrosshairTool(line_alpha=0.3)

        fig.add_tools(hover,wheelzoom,pan,crosshair)
        fig.toolbar.active_scroll=wheelzoom
        fig.toolbar.active_drag=pan
        fig.toolbar_location=None

    elif plot_switch==2:

        # individual plot dimensions
        plot_width = fig_width; plot_height = int( (float(fig_height) / len(stages)) )

        figs = [] # figure collection

        # draw multiple plots
        for idx in range(0,len(stages)):
            
            # create figure
            if idx == 0:
                fig = figure(x_range=FactorRange(*project_data['x']), 
                             plot_height=plot_height, plot_width=plot_width, tools='',)
                fig.xaxis.visible = True if len(stages) == 1 else False
            if (0<idx) and (idx<len(stages)-1):
                fig = figure(x_range=figs[0].x_range, 
                             plot_height=plot_height, plot_width=plot_width, tools='',)
                fig.xaxis.visible = False
            elif idx == len(stages)-1:
                fig = figure(x_range=figs[0].x_range, 
                             plot_height=plot_height, plot_width=plot_width, tools='',)
                fig.xaxis.visible = True

            # figure attributes
            setattrs(fig.xaxis, axis_line_width=1, major_label_orientation=1)
            setattrs(fig.xgrid, grid_line_color='black', grid_line_alpha=0.2, grid_line_dash=[6,4])
            
            setattrs(fig.y_range, start=0, range_padding=1)
            setattrs(fig.yaxis, axis_line_width=1, axis_label=stages[idx], axis_label_standoff=10, 
                     axis_label_text_font_size='1em', minor_tick_line_alpha=0)
            
            setattrs(fig.legend, orientation="vertical", location="top_right")
            setattrs(fig, outline_line_width=2, outline_line_alpha=0.1, outline_line_color="black")

            # toolbar
            tooltips = [(stages[idx],'@{'+stages[idx]+'}')]
            hover = HoverTool(tooltips=tooltips,mode='vline')
            wheelzoom = WheelZoomTool(dimensions='width')
            pan = PanTool(dimensions='width')
            crosshair = CrosshairTool(line_alpha=0.3)

            fig.add_tools(hover,wheelzoom,pan,crosshair)
            fig.toolbar.active_scroll=wheelzoom
            fig.toolbar.active_drag=pan

            # draw plot
            vbar = fig.vbar(x=dodge('x',0.4,range=fig.x_range), top=stages[idx], 
                     width=0.8, source=project_data, color=stages_palette[idx])
        
            # register into figure collection
            figs.append(fig)

        # assemble mutiple figure(plots) into one
        fig = gridplot([[fig] for fig in figs], sizing_mode='fixed', merge_tools=True, toolbar_location=None)

    return fig

def scan_project_avail_dates(project_name):
    cursor = db[project_name].find()
    df = pandas.DataFrame(list(cursor))
    avail_dates = df[dateReported_col_str].map(lambda unicode_str: str(unicode_str[0:7])).unique().tolist() # take only year and month part of date string
    return avail_dates

def scan_overall_avail_dates(project_names):
    mapped = map(lambda project_name: scan_project_avail_dates(project_name), project_names)
    reduced = reduce(lambda accm,x: accm+x, mapped)
    avail_dates = list(set(reduced)) # set() is essentially unique() operation
    return avail_dates

def build_avail_dates_dict(avail_dates):
    year_month_strs = pandas.Series(avail_dates)
    allDates = year_month_strs.map(lambda year_month_str: DT.strptime(year_month_str, '%Y-%m'))
    allDates_df = pandas.DataFrame({
                    'year':allDates.map(lambda date: str(date.year)),
                    'month':allDates.map(lambda date: str(date.month))
                  })
    years = sorted(allDates_df['year'].unique().tolist())
            
    def get_avail_months(year): return sorted(allDates_df['month'][allDates_df['year']==year].unique().tolist())
        
    avail_dates_dict = dict(map(lambda year: (year, get_avail_months(year)) , years))
    return avail_dates_dict

# helper function for setting multiple attributes
def setattrs(_self, **kwargs): 
    for k,v in kwargs.items(): setattr(_self, k, v)

## Initializations ##

# establish mongo db connection
mongoDB_ip = '192.168.2.134'
mongoDB_port = 27017
mongoClient = MongoClient(mongoDB_ip, mongoDB_port)
# dbs = mongoClient.database_names()
db = mongoClient['lims']
collections = db.collection_names()
collections.remove('system.indexes')

lab_names = ['AMDL', 'TGH']
project_names = map(str, collections)
project_names.remove('Agile_TAT') # temporary exclusion due to data defect in current mongodb
selection_names = project_names[:] # [:] means copy by value (as opposed to copy by reference)
selection_names.insert(0, 'Overall')

current_lab_name = lab_names[0]
current_project_name = selection_names[2]

overall_avail_dates_dict = build_avail_dates_dict(scan_overall_avail_dates(project_names))
overall_current_year = overall_avail_dates_dict.keys()[0] # default year
overall_current_month = overall_avail_dates_dict[overall_current_year][0] # default month

# expected fields to be seen in mongodb tables
stages = ['Rec>Ext', 'Ext>Test', 'Test>Com', 'Com>Rep', 'Rec>Rep']
