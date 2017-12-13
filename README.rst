======================
Clarity LIMS Dashboard
======================

Written by Jone Kim (coop student Sept-Dec 2017)

1.1 Overview
-----------------
- This is a web-browser accessible application. This web applicattion is a data visualzation dashboard that will display interactable charts that are plotted based on the data from UHN research's Clarity LIMS database. Clarity LIMS is a Laboratory Information Management System (hence 'LIMS') where electronic records of standardized/protocolized biochemistry tests performed in UHN are kept and tracked.

- This application is meant to be used within UHN research only, and thus accessbile only within the UHN research intranet.

- From end-user's point of view, the dashboard is a single web page containing multiple interative charts. The currently developed and available charts that can be found in this web page are:

    1. Turn Around Time plot (quite mature)
    2. BCR/ABL Quality Control Levey-Jennings plot (not as mature)

- The source code can be found at:

    https://github.com/Bio-Core/clarity_dash


1.2 Requirements
-----------------

(Note that the requirements written here are not generalized, but are list of partcular instances of what was used during it's initial development by coop student Jone Kim.)

- Linux host VM with (Zhibin will set this up for you):

    - Accessibility from ``Mordor``
    - ``coop2`` user account with ``sudo`` rights
    - port ``8000`` & ``8001`` open

    and have installed the following:

    - Docker
    - git

    App Container (Docker) Environment:

    - Ubuntu
    - Python 2.7
    - Python pip
    - Variety of python pip packages listed inside ``requirements.txt``. Mainly used packages are Flask, Bokeh, Pandas, Numpy, etc.


1.3 Installation
-----------------

Please note that this installation guide written here is not generalized, but is written in instance and from point of view of coop student working on coop student's iMac.

1. At the time of writing, coop student's iMac didn't have direct access to UHN research intranet. Thus if you are working on this iMac, you will need to first email RIS helpdesk (helpdesk@uhnresearch.ca) to obtain OTP keys for remote access into the intranet.

2. Once OTP keys are obtained, from your iMac, go to http://www.uhnresearch.ca/remote, enter your UHN RID and OTP key, and click Launch button for ``Windows 7 - General Desktop``, and open the ``.rdp`` file downloaded.

3. In your remote desktop, download a portable ``PuTTY`` and use it to ``SSH`` into ``mordor``.

4. Once ssh-ed into mordor, login as ``coop2`` (ask Zhibin for the pw).

5. Now ``ssh`` into ``clarity-dash`` (this is Linux CentOS VM, the host environment) by typing:
::

    ssh coop2@clarity-dash

6. Once ssh-ed into the host VM, make and cd into directory:
::

    cd /home/coop2/
    mkdir app
    cd app

7. Use git to clone this repository into vm:
::

    git clone https://github.com/Bio-Core/clarity_dash

8. Build docker image:
::

    sudo docker build -t lims_dashboard .

(``-t lims_dashboard`` option is the label for the built image)


1.4 Execution, Access, Management, Kill
----------------------------------------

**[Execution]** Before one can access the app, app needs execution by launching a docker container in VM:
::

    sudo docker run --name lims_dashboard -p 8000:8000 -p 8001:8001 -v /home/coop2/app/:/home/app/ lims_dashboard

command explained:

- ``--name lims_dashboard`` option is label for the container to be ran;
- ``-p 8000:8000 -p 8001:8001`` options are for port forwarding host->container;
- ``-v /home/coop2/app/:/home/app/`` option is for the volume/directory share point between the host and container.

**[Access]** to access the app as an end-user, use a web broswer to access: 

    http://clarity.uhnresearch.ca:8000/

Or alternatively, one could access the individual bokeh server charts directly for debugging purpose by accessing:

    http://clarity.uhnresearch.ca:8001/

**[Management]** To shell into a running docker container, in VM:
::

    sudo docker exec -it lims_dashboard bash

**[Kill]** To take down and remove the running docker container, in VM:
::

    sudo docker kill lims_dashboard; sudo docker rm lims_dashboard


1.5 Brief Explanation of How the App Works
-------------------------------------------

1.5.1 Platform
================

- The app runs inside a Ubuntu docker container which runs on top of ``clarity-dash`` CentOS VM.

1.5.2 app.py
=============

- Once container is executed, ``app.py`` python flask script will run inside the container.

- This script will prepare bokeh server worker threads by registering each dashboard chart's ``modify_doc()`` function, which are called upon and used to serve the incoming user with interactive plots.

- These dashboard functions registered can be found inside the ``dashboard`` module. As it should be obvious in the line ``from dashboard import TAT, QC``

- The script will wait for user requests. Once receives request to connect to dashboard, it will generate bokeh server document javascripts (these are essentially the charts) and embed into a template html, which is returned to the user's web browser.


1.5.3 dashboard module
=======================

- In both ``TAT`` and ``QC`` scripts of the ``dashboard`` module, the central function that is registered and used by the bokeh server workers is the ``modify_doc()`` function. All the rest of functions in the script are helper functions used by this function.

- Once initialization is done, they set up the controls (dropdown/select menu, buttons, etc) and register callback functions to these controls, which will take appropriate action in refreshing the doc with new content requested via controls.


1.5.4 Understanding the Rest of the Code
==========================================

- Attempt was made to code as self-explanatory as possible, trying to keep the comments as minimal as possible and only where essential.

- However in areas where many abstract data manipulation was taking place (with use of techniques like ``map`` and ``reduce``), making the code self-explanatory was difficult and trying to describe the data in comment could add more confusion. 

- So as for trying understanding these parts of the code I recommend the future developer to open a python console and debug the those parts of the code line by line to see what the content of the data actually looks like.


1.6 Suggestions for Future Co-ops
-----------------------------------

1.6.1 Data Manipulation/Processing
===================================

- When manipulating data, writing long and ugly iteration loops could potentially be avoided and simplified using ``map`` and ``reduce`` techniques. If you're not familiar with it, learning these will introduce you into a entire new world! (Also note that these are also the core techniques used in big-data processing in distributed/parallel computing framework like Apache Hadoop/Spark.)

1.6.2 Fix Bokeh Figure 'blinking'
==================================

- Currently, when you switch dataset on the TAT plot, sometimes the entire figure 'blinks' to reload, and momentarily shrinks and dislocates other HTML elements in the page. In future development, it might be a good idea to find a way to get rid of this 'blinking' issue on the python bokeh application level or may be segregate each plots into a seperate html ``iframes``, etc to have a non-shrinkable frame inside the dashboard page.

1.6.3 Refactoring
===================

- I tried refactoring as much as possible, but there may be features that may be considered for refactoring in the future.
- For example, currently the initialization for mongodb connection is hardcoded in ``TAT.py`` because this is the only module that uses mongodb at this time.  However, if more dashboard plots/modules that use mongodb are to be added in the future, such mongodb connection initialization could be refactored into a seperate single module.

1.6.4 Development Tools
=============================

- Development of this app was done on the ``Windows 7 remote desktop``, using tools such as ``PuTTY`` (or alternatively, I recommend ``CMDer``), ``WinSCP``, ``Sublime Text 3``.

- One can download the repository into this desktop; edit code with Sublime Text; easily transfer (SCP) files over to the VM using WinSCP (will need to configure tunnelling as we need to ssh twice to reach the VM); and launch/kill the dashboard app in VM via PuTTY or CMDer.

- Or if you are more familiar and comfortable with using tools such as Linux ``emacs`` or ``vim``, you can simply use them in your ``PuTTY`` (or ``CMDer``) to edit code inside the VM.

- Don't forget to commit your code as you develop!

1.6.4 Roozbeh's Comments
=========================

- Avoid global variables at all costs (explicitly pass the function variables where they are needed)

- Avoid namespace clashes with variable scopes

- Some data processing functionalities could be implemented easier and more straight-forward with ``Pandas`` module infrastructure, try using the existing infrastructure more, rather than reinventing the wheel.

- We may need to move on from ``Bokeh`` to ``D3.js`` eventually, if a fundamental/critical limitation was to be found with Bokeh. (I think I am seeing the limitations too, and I've been already playing on that level of threshold and pushing Bokeh to its limitations)