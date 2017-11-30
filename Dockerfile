FROM ubuntu

MAINTAINER Jone Kim

RUN apt-get update --fix-missing
RUN apt-get upgrade --yes
RUN apt-get install -y \
    python python-dev python-pip curl \
    apache2 libapache2-mod-wsgi

RUN mkdir /home/app/
WORKDIR /home/app/

COPY . /home/app/

RUN pip install -r requirements.txt

EXPOSE 8000
EXPOSE 8001

CMD ["python", "/home/app/app.py"]