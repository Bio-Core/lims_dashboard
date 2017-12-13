from bokeh.plotting import *
from bokeh.models import HoverTool, CrosshairTool, PanTool, WheelZoomTool, ColumnDataSource, FactorRange, Select, Button, Div, Panel, Tabs
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
from common_functions import setattrs

##====[ Predetermined Parameters ]====##

# MongoDB:
mongoDB_ip = '192.168.2.134'
mongoDB_port = 27017
lims_db_name = 'lims'
lab_names = ['AMDL', 'TGH']

# all expected fields (columns) to be seen in mongodb tables:
sequenom_num = 'SEQUENOM_NUM'
sampleID = 'SAMPLE ID'
date_received = 'Date Received'
date_DNAext = 'DNA Extraction Date'
date_test = 'TEST_DATE'
date_completed = 'Date Completed'
date_reported = 'Date Reported'
rec2ext = 'Rec>Ext'
ext2test = 'Ext>Test'
test2com = 'Test>Com'
com2rep = 'Com>Rep'
rec2rep = 'Rec>Rep'
qcstatus = 'QC status'
failureStep = 'Failure step'
comments = 'Comments'

unnecessary_cols = ['_id'] # list of column names that will be found in tables but are not needed for our app

# sample stages in the lab in appropriate order
stages = [rec2ext, ext2test, test2com, com2rep, rec2rep]
# appropriate column order such that disorganized mongodb table column order can be reordered into this
appropriate_col_order = [sequenom_num, sampleID, 
                         date_received, date_DNAext, date_test, date_completed, date_reported, 
                         rec2ext, ext2test, test2com, com2rep, rec2rep,
                         qcstatus, failureStep, comments]

# plot dimension:
plot_width = 600 # pixels
plot_height = 600 # pixels

# global dataframes:
passed_df = pandas.DataFrame(); qcfailed_df = pandas.DataFrame(); delayed_df = pandas.DataFrame()

def modify_doc(doc):
    """
    Function to be registered into bokeh application server thread
    """

    # top row controls (dropdown menus):
    lab_select = Select(title='Lab', options=lab_names, value=current_lab_name, width=140)
    plot_select = Select(title='Project', options=selection_names, value=current_plot_select, width=140)

    # these only appear when selected 'AllProject_TAT' project
    allProject_TAT_year_select = Select(title='Year', options=allProject_availDates_dict.keys(), value=allProject_TAT_current_year, width=140)
    allProject_TAT_month_select = Select(title='Month', options=allProject_availDates_dict[allProject_TAT_current_year], value=allProject_TAT_current_month, width=140)

    # bottom row downloadable sheets (buttons)
    dwnld_div = Div(text='Downloadable Datasheet: ', width=180)
    passed_dwnld_bttn = Button(label='Passed', width=80)
    qcfailed_dwnld_bttn = Button(label='QC Failed', width=80)
    delayed_dwnld_bttn = Button(label='Delayed', width=80)

    def refreshDoc_callback(attr, old, new):
        # obtain selected dropdown menu values
        current_lab_name = lab_select.value
        current_plot_select = plot_select.value
        allProject_TAT_current_year = str(allProject_TAT_year_select.value)
        allProject_TAT_current_month = str(allProject_TAT_month_select.value)
        allProject_TAT_month_select.options = allProject_availDates_dict[allProject_TAT_current_year]

        # generate different figure and control panel composition based on dropdown menu selected
        if current_plot_select == 'AllProject_TAT':
            controls = row(children=[lab_select, Spacer(width=20), plot_select, Spacer(width=40), allProject_TAT_year_select, Spacer(width=20), allProject_TAT_month_select])
            fig = plotData_allProject_TAT(prepData_allProject_TAT(allProject_TAT_current_year, allProject_TAT_current_month, project_names))
            downloads = row(Spacer()) # empty space
            
        elif current_plot_select == 'AllProject_failRatio':
            controls = row(children=[lab_select, Spacer(width=20), plot_select])
            fig = plotData_allProject_failRatio(prepData_allProject_failRatio(project_names, allProject_availDates_tuples))
            downloads = row(Div(text='[Note] failed samples := qcfailed samples + delayed samples', width=plot_width)) 
            
        else: # individual project
            controls = row(children=[lab_select, Spacer(width=20), plot_select])
            global passed_df, qcfailed_df, delayed_df
            oneProject_TAT, passed_df, qcfailed_df, delayed_df = prepData_oneProject_TAT(current_plot_select)
            fig = plotData_oneProject_TAT(oneProject_TAT)
            filename_prefix = '['+current_lab_name+']['+current_plot_select+'][entire_history]'
            passed_dwnld_bttn.callback = CustomJS(args=dict(source=ColumnDataSource(
                data={'filename': [filename_prefix+'_passed.csv'], 
                      'csv_str':[passed_df.to_csv(index=False).replace('\\n','\\\n')]})), code=dwnld_csv_js)
            qcfailed_dwnld_bttn.callback = CustomJS(args=dict(source=ColumnDataSource(
                data={'filename': [filename_prefix+'_qcfailed.csv'], 
                      'csv_str':[qcfailed_df.to_csv(index=False).replace('\\n','\\\n')]})), code=dwnld_csv_js)
            delayed_dwnld_bttn.callback = CustomJS(args=dict(source=ColumnDataSource(
                data={'filename': [filename_prefix+'_delayed.csv'], 
                      'csv_str':[delayed_df.to_csv(index=False).replace('\\n','\\\n')]})), code=dwnld_csv_js)
            downloads = row(dwnld_div, passed_dwnld_bttn, Spacer(width=25), qcfailed_dwnld_bttn, Spacer(width=25), delayed_dwnld_bttn)    
        
        doc.clear()
        doc.add_root(column(controls,fig,downloads))

    # javascript used for initiating csv datasheet download
    dwnld_csv_js = """
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

    # register callback function to call upon change detected in dropwdown menu
    lab_select.on_change('value', refreshDoc_callback)
    plot_select.on_change('value', refreshDoc_callback)
    allProject_TAT_year_select.on_change('value', refreshDoc_callback)
    allProject_TAT_month_select.on_change('value', refreshDoc_callback)

    # initialize document by forcing callback once in the beginning
    refreshDoc_callback(None, None, None) 

def prepData_oneProject_TAT(project_name):
    """
    Plots median TAT data in each stage for one project, for its entire history
    """
    
    # load db data into pandas dataframe
    cursor = db[project_name].find()
    df = pandas.DataFrame(list(cursor))
    
    # delete unnecessary df columns and reorder columns into appropriate order
    df = df.drop(unnecessary_cols, axis=1)
    df = df[appropriate_col_order]
    
    # find all range of reported years and months
    dt_series = df[date_reported].map(lambda string: DT.strptime(string, '%Y-%m-%d'))
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
    oneProject_TAT = {}
        
    # y-data:
    nodata_stages = [] # stages with nodata are to be removed from plotting
        
    # calculate medians for all stages, for all years, for all months
    for stage in stages:
        medians = []
        for year in years:
            for month in months:
                logical_idx = dt_series.map(lambda dt: (dt.year == year) & (dt.month == month))
                counts = passed_df.loc[logical_idx, stage] # filter by logical index
                medians.append(counts.median())
        if NP.all(NP.isnan(medians)): # if data found is all nan, exclude this stage from data entries
            nodata_stages.append(stage)
        else:
            oneProject_TAT[stage] = medians
    
    # remove stages that have no data
    [ stages.remove(stage) for stage in nodata_stages ]
    
    # find max median data
    max_median = NP.nanmax([ NP.nanmax(oneProject_TAT[stage]) for stage in stages ])
    
    # x-data:
    years_months = [(str(year), str(month)) for year in years for month in months]
    oneProject_TAT['x'] = years_months
    
    return oneProject_TAT, passed_df, qcfailed_df, delayed_df

def plotData_oneProject_TAT(oneProject_TAT):
    """
    Plots median TAT data prepared in prepData_oneProject_TAT() function.
    """
    return plotData_timeseries(oneProject_TAT, stages, 'Median')

def prepData_allProject_TAT(current_year,current_month,project_names):
    """
    Prepare median TAT data in each stages for all projects in one plot, for a specific year-month
    """
    
    # the target year-month to retrieve data from all projects
    target_x = (current_year, current_month)
    # retrieve all project data, of all history
    oneProject_TAT_datas = map(lambda project_name: (project_name, prepData_oneProject_TAT(project_name)[0]), project_names)
    
    # filter function for the target year-month
    def dateFilter(oneProject_TAT):
        idx = oneProject_TAT['x'].index(target_x)
        data = map(lambda stage: oneProject_TAT[stage][idx], stages)
        return data
    
    # apply date filter for each project
    allProject_TAT_data = dict(map(lambda (project_name, oneProject_TAT): (project_name, dateFilter(oneProject_TAT)), oneProject_TAT_datas))
    allProject_TAT_data['x'] = stages
    
    return allProject_TAT_data

def plotData_allProject_TAT(allProject_TAT_data):
    """
    Plots median TAT data obtained in prepData_allProject_TAT() function
    """

    # color palette
    projects_palette = Category20[20][0:len(stages)]

    # create figure
    fig = figure(x_range=FactorRange(*allProject_TAT_data['x'], range_padding=0.2),
                 plot_width=plot_width, plot_height=plot_height, tools='',
                 x_axis_label='Stages', y_axis_label='Median')

    # plot bar attributes
    bar_thickness = 1.0
    bar_width = ( float(1) / (len(project_names)+1) ) * bar_thickness
    bar_position = NP.array(range(0,len(project_names)))
    bar_position = bar_position - NP.median(bar_position)
    bar_position = bar_position / len(bar_position) / 1.2

    # draw plots
    for idx in range(0,len(project_names)):
        vbar = fig.vbar(x=dodge('x',bar_position[idx],range=fig.x_range), top=project_names[idx],
            width=bar_width, source=allProject_TAT_data, color=projects_palette[idx], legend=value(project_names[idx]))

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

def prepData_allProject_failRatio(project_names, allProject_availDates_tuples):
    """
    Prepare data of percentage of failed samples for entire history of all projects.
    Percentage of failed samples is defined as:
    ((count of QC failed samples in a month + count of delayed samples in a month) / sum count of all samples in a month)
    """
    
    # retrieve all project QC data (passed_df, qcfailed_df, delayed_df), of all history
    oneProject_QC_datas = dict(map(lambda project_name: (project_name, prepData_oneProject_TAT(project_name)[1:]), project_names))
    
    def calc_percent_failures( project_name, (passed_df, qcfailed_df, delayed_df) , allProject_availDates_tuples ):
        def date_filt(df, year, month):
            date_series = df[date_reported].map(lambda date_str: DT.strptime(date_str, '%Y-%m-%d'))
            logical_idx = (date_series.map(lambda date: date.year) == year) & (date_series.map(lambda date: date.month) == month)
            return float(len(df.where(logical_idx).dropna()))
            
        passed_counts = NP.array(map(lambda (year,month): date_filt(passed_df, year, month) , allProject_availDates_tuples))
        qcfailed_counts = NP.array(map(lambda (year,month): date_filt(qcfailed_df, year, month) , allProject_availDates_tuples))
        delayed_counts = NP.array(map(lambda (year,month): date_filt(delayed_df, year, month) , allProject_availDates_tuples))
                    
        total_counts = passed_counts + qcfailed_counts + delayed_counts
        failed_counts = qcfailed_counts + delayed_counts
        percent_failures = map(float, list((failed_counts / total_counts) * 100))
            
        return (project_name, percent_failures)
        
    allProject_failRatio_data = dict(map(lambda project_name: calc_percent_failures(project_name, oneProject_QC_datas[project_name], allProject_availDates_tuples), project_names))
    allProject_failRatio_data['x'] = map(lambda (year,month): (str(year),str(month)) , allProject_availDates_tuples)
    return allProject_failRatio_data

def plotData_allProject_failRatio(allProject_failRatio_data):
    """
    Plots percentage of failed samples data obtained in prepData_allProject_failRatio() function
    """
    return plotData_timeseries(allProject_failRatio_data, project_names, 'Percentage of Failed Samples')
    
def plotData_timeseries(data, component_names, yaxis_label):
    """
    Given a timeseries data of multiple components, plots bar-timeseries plots in two different views 
    ('compact' & 'decomposed'), and combines the two views under a tab UI, and returns this figure.
    """

    # color palettes
    components_palette = Category20[20][0:len(component_names)]

    def make_compact_fig():
        
        # create figure
        fig = figure(x_range=FactorRange(*data['x']), 
                     plot_width=plot_width,plot_height=plot_height, tools='',
                     x_axis_label='Year-Month', y_axis_label=yaxis_label)
        
        # plot bar attributes
        bar_thickness = 0.8
        bar_width = ( float(1) / (len(component_names)+1) ) * bar_thickness
        bar_position = NP.array( range(0,len(component_names)) )
        bar_position = bar_position /float(bar_position[-1]+2)
        bar_position += bar_width / 2
        
        # draw plots
        for idx in range(0,len(component_names)):
            vbar = fig.vbar(x=dodge('x',bar_position[idx],range=fig.x_range), top=component_names[idx], 
                     width=bar_width, source=data, color=components_palette[idx], legend=value(component_names[idx]))
        
        # figure attributes
        setattrs(fig.xaxis, axis_label_standoff=10, major_label_orientation=1)
        setattrs(fig.x_range, range_padding=0.2)
        setattrs(fig.xgrid, grid_line_color = 'black', grid_line_alpha = 0.2, grid_line_dash = [6,4])
        
        setattrs(fig.yaxis, axis_label_standoff=10)
        setattrs(fig.y_range, start=0, range_padding=0.5)
        setattrs(fig.ygrid, minor_grid_line_color='black', minor_grid_line_alpha=0.05)
        
        setattrs(fig.legend, orientation='vertical', location='top_right')
        
        # toolbar
        # tooltips = [(stage,'@{'+stage+'}') for stage in stages]
        spanTags = map(lambda (project_color,project_name): '<div><span style="color:'+project_color+';">'+project_name+': <b>@{'+project_name+'}</b></span></div>', zip(components_palette, component_names))
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
        
        fig_compact = fig
        
        return fig_compact

    def make_decomposed_fig():
            
        # subplots dimensions
        subplot_width = plot_width; 
        subplot_height = int( (float(plot_height) / len(component_names)) )
            
        figs = [] # figure collection
            
        # draw multiple plots
        for idx in range(0,len(component_names)):
                        
            # create figure
            if idx == 0:
                fig = figure(x_range=FactorRange(*data['x']), 
                             plot_height=subplot_height, plot_width=subplot_width, tools='',)
                fig.xaxis.visible = True if len(component_names) == 1 else False
            if (0<idx) and (idx<len(component_names)-1):
                fig = figure(x_range=figs[0].x_range, 
                             plot_height=subplot_height, plot_width=subplot_width, tools='',)
                fig.xaxis.visible = False
            elif idx == len(component_names)-1:
                fig = figure(x_range=figs[0].x_range, 
                             plot_height=subplot_height, plot_width=subplot_width, tools='',)
                fig.xaxis.visible = True
            
            # figure attributes
            setattrs(fig.xaxis, axis_line_width=1, major_label_orientation=1)
            setattrs(fig.x_range, range_padding=0.2)
            setattrs(fig.xgrid, grid_line_color='black', grid_line_alpha=0.2, grid_line_dash=[6,4])
                        
            setattrs(fig.yaxis, axis_line_width=1, axis_label=component_names[idx], axis_label_standoff=10, 
                     axis_label_text_font_size='1em', minor_tick_line_alpha=0)
            setattrs(fig.y_range, start=0, range_padding=1)
                        
            setattrs(fig.legend, orientation="vertical", location="top_right")
            setattrs(fig, outline_line_width=2, outline_line_alpha=0.1, outline_line_color="black")
            
            # toolbar
            tooltips = [(component_names[idx],'@{'+component_names[idx]+'}')]
            hover = HoverTool(tooltips=tooltips,mode='vline')
            wheelzoom = WheelZoomTool(dimensions='width')
            pan = PanTool(dimensions='width')
            crosshair = CrosshairTool(line_alpha=0.3)
            
            fig.add_tools(hover,wheelzoom,pan,crosshair)
            fig.toolbar.active_scroll=wheelzoom
            fig.toolbar.active_drag=pan
            
            # draw plot
            vbar = fig.vbar(x=dodge('x',0.4,range=fig.x_range), top=component_names[idx], 
                     width=0.8, source=data, color=components_palette[idx])
                    
            # register this subplot into figure collection
            figs.append(fig)
            
        # assemble mutiple figure(subplots) into one
        fig_decomposed = gridplot([[fig] for fig in figs], sizing_mode='fixed', merge_tools=True, toolbar_location=None)
                    
        return fig_decomposed

    # function for link/synchronizing the xaxis of compact and decomposed figures
    def link_figure_xaxis(fig_compact, fig_decomposed):
        for row in fig_decomposed.children:
            for subplot in row.children:
                subplot.x_range = fig_compact.x_range
                    
    # make figures and link xaxis
    fig_compact = make_compact_fig()
    fig_decomposed = make_decomposed_fig()
    link_figure_xaxis(fig_compact, fig_decomposed)
            
    # combine the two figures via tab UI
    fig_tabbed = Tabs(tabs=[ Panel(child=fig_compact,title='Compact') , Panel(child=fig_decomposed,title='Decomposed') ])
    return fig_tabbed

def scanDates_allProject(project_names):
    """
    Scans all available unique year-month records for union of all projects.
    """
    availDates_listOfLists = map(lambda project_name: scanDates_oneProject(project_name), project_names)
    reduced = reduce(lambda list1,list2: list1+list2, availDates_listOfLists) # concat all list of list into a single flat list
    availDates_strs = list(set(reduced)) # set() is essentially a unique() operation
    return availDates_strs

def scanDates_oneProject(project_name):
    """
    Scans all available unique year-month records for a specific project.
    """
    cursor = db[project_name].find()
    df = pandas.DataFrame(list(cursor))
    availDates_strs = df[date_reported].map(lambda unicode_str: str(unicode_str[0:7])).unique().tolist() # take only year and month part of date string
    return availDates_strs

def build_availDates_tuples(availDates_strs):
    """
    builds list of tuples of all available year-month records.year-month
    Can use on data returned from either scanDates_oneProject() or scanDates_allProject()
    """
    allDates = map(lambda availDate_str: DT.strptime(availDate_str, '%Y-%m') , availDates_strs)
    availDates_tuples = map(lambda date: (date.year, date.month), allDates)
    return availDates_tuples

def build_availDates_dict(availDates_strs):
    """
    Builds a dictionary of all available year-month records.
    Can use on data returned from either scanDates_oneProject() or scanDates_allProject()
    """
    availDates_series = pandas.Series(availDates_strs)
    allDates = availDates_series.map(lambda availDate_str: DT.strptime(availDate_str, '%Y-%m'))
    allDates_df = pandas.DataFrame({
                    'year':allDates.map(lambda date: str(date.year)),
                    'month':allDates.map(lambda date: str(date.month))
                  })
    years = sorted(allDates_df['year'].unique().tolist())
            
    def get_availMonths(year): return sorted(allDates_df['month'][allDates_df['year']==year].unique().tolist())
        
    availDates_dict = dict(map(lambda year: (year, get_availMonths(year)) , years))
    return availDates_dict

##====[ Initializations ]====##

# establish mongo db connection
mongoClient = MongoClient(mongoDB_ip, mongoDB_port)
# dbs = mongoClient.database_names()
db = mongoClient[lims_db_name]
collections = db.collection_names()

project_names = map(str, collections) # convert unicode to string
project_names.remove('Agile_TAT') # temporary exclusion due to data defect in current mongodb
selection_names = project_names[:] # [:] means copy by value (as opposed to copy by reference)
selection_names.insert(0, 'AllProject_failRatio')
selection_names.insert(0, 'AllProject_TAT')

current_lab_name = lab_names[0]
current_plot_select = selection_names[0]

# get union of all available dates for all project
allProject_availDates_strs = scanDates_allProject(project_names)
allProject_availDates_tuples = build_availDates_tuples(allProject_availDates_strs)
allProject_availDates_dict = build_availDates_dict(allProject_availDates_strs)

allProject_TAT_current_year = allProject_availDates_dict.keys()[0] # default year
allProject_TAT_current_month = allProject_availDates_dict[allProject_TAT_current_year][0] # default month
