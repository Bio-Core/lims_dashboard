from flask import Flask, render_template
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.util.string import encode_utf8
from bokeh.embed import server_document
from bokeh.server.server import Server
from dashboard import (TAT, QC)

app = Flask(__name__)

# IP of container-running host and container's internal flask app host (localhost)
host_ip = '142.1.33.237'
container_app_host = '0.0.0.0'

# host->container forwarded flask app server ports
host_dashboard_port = 5001
container_dashboard_port = 5000

# host->container forwarded bokeh server ports
host_bokehServer_port = 5002
container_bokehServer_port = 5006

# application handlers and urls
TAT_app = Application(FunctionHandler(TAT.modify_doc))
TAT_app_url = 'TAT'
QC_app = Application(FunctionHandler(QC.modify_doc))
QC_app_url = 'QC'

# start Bokeh Server Threads
def bokehServer_worker():
    server = Server({'/'+TAT_app_url: TAT_app, '/'+QC_app_url: QC_app }, port=container_bokehServer_port, allow_websocket_origin=[host_ip+':'+str(host_dashboard_port)])
    server.start()
    server.io_loop.start()

from threading import Thread
Thread(target=bokehServer_worker).start()

# main dashboard content
@app.route('/')
def index():

    # render js & div component
    script1 = server_document('http://'+host_ip+':'+str(host_bokehServer_port)+'/'+TAT_app_url)
    script2 = server_document('http://'+host_ip+':'+str(host_bokehServer_port)+'/'+QC_app_url)

    # render html
    html = encode_utf8(render_template(
        'index.html',
        plot_script1=script1,
        plot_script2=script2,
    ))

    return html

if __name__ == '__main__':
    app.run(debug=True, host=container_app_host, port=container_dashboard_port)


# MISC CODE FRAGS:

# dateRep_series.loc[ dateRep_series.str.match('^2017-01-\d\d') ]
# str = df.iloc[0:5,0:3].to_html()
# str = df.loc[0:5,['SEQUENOM_NUM', 'Date Received']].to_html()
# str = df['Test>Com'].mean().__str__()
# html = df.to_html()