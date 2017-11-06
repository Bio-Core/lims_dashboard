FROM ubuntu

MAINTAINER Jone Kim

RUN apt-get update  --fix-missing
RUN apt-get upgrade --yes
RUN apt-get install -y \
    python python-pip \
    apache2 libapache2-mod-wsgi

RUN mkdir /home/app/
WORKDIR /home/app/

COPY . /home/app/

RUN pip install -r requirements.txt

EXPOSE 5000
EXPOSE 5006

CMD ["python", "/home/app/app.py"]


# docker commands to run:
# docker build -t lims_dashboard .
# docker run --name lims_dashboard -p 5001:5000 -p 5002:5006 lims_dashboard