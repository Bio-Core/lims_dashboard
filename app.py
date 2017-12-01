from flask import Flask, render_template
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.util.string import encode_utf8
from bokeh.embed import server_document
from bokeh.server.server import Server
from dashboard import TAT, QC

app = Flask(__name__)

# IP of container-running host and container's internal flask app host (localhost)
host_ip = 'clarity.uhnresearch.ca' #'192.168.2.10' #'142.1.33.237'
container_app_host = '0.0.0.0'

# host->container forwarded flask app server ports
host_dashboard_port = 8000
container_dashboard_port = 8000

# host->container forwarded bokeh server ports
host_bokehServer_port = 8001
container_bokehServer_port = 8001

# application handlers and url substrings
TAT_app = Application(FunctionHandler(TAT.modify_doc))
TAT_app_url = 'TAT'
QC_app = Application(FunctionHandler(QC.modify_doc))
QC_app_url = 'QC'

# start Bokeh Server Threads
def bokehServer_worker():
    server = Server({'/'+TAT_app_url: TAT_app, 
                     '/'+QC_app_url: QC_app }, 
                    port=container_bokehServer_port, 
                    # following defines through which URLs the user is allowed to connect to these apps
                    allow_websocket_origin=[host_ip+':'+str(host_dashboard_port), host_ip+':'+str(host_bokehServer_port)])
    server.start()
    server.io_loop.start()

from threading import Thread
Thread(target=bokehServer_worker).start()

# generate dashboard content upon http connection
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
