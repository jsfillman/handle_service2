FROM kbase/sdkbase2:python
MAINTAINER KBase Developer
# -----------------------------------------
# In this section, you can install any system dependencies required
# to run your App.  For instance, you could place an apt-get update or
# install line here, a git checkout to download code, or run any other
# installation scripts.

# RUN apt-get update

# install mongodb
RUN sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2930ADAE8CAF5059EE73BB4B58712A2291FA4AD5 \
    && echo "deb http://repo.mongodb.org/apt/debian stretch/mongodb-org/3.6 main" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.6.list  \
    && sudo apt-get update \
    && sudo apt-get install -y mongodb-org=3.6.11 mongodb-org-server=3.6.11 mongodb-org-shell=3.6.11 mongodb-org-mongos=3.6.11 mongodb-org-tools=3.6.11 \
    && sudo apt-get install -y mongodb

RUN echo "mongodb-org hold" | sudo dpkg --set-selections \
    && echo "mongodb-org-server hold" | sudo dpkg --set-selections \
    && echo "mongodb-org-shell hold" | sudo dpkg --set-selections \
    && echo "mongodb-org-mongos hold" | sudo dpkg --set-selections \
    && echo "mongodb-org-tools hold" | sudo dpkg --set-selections

RUN pip install mysql-connector
RUN pip install pymongo
RUN pip install mock
RUN pip install cachetools

RUN pip install coverage && \
    pip install pathos


# -----------------------------------------

COPY ./ /kb/module
RUN mkdir -p /kb/module/work
RUN chmod -R a+rw /kb/module

WORKDIR /kb/module

RUN make all

ENTRYPOINT [ "./scripts/entrypoint.sh" ]

CMD [ ]
