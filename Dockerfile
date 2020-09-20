FROM ubuntu:20.04

# Folder we're keeping the app in
WORKDIR /app
# Where videos download by default
VOLUME /app/downloads
# It is a very good idea to put this somewhere else
VOLUME /app/db

# To prevent tzdata ruining the build process
ENV TZ=Australia/Melbourne
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Split up these lines so Docker can cache them
RUN apt-get update && \
    apt-get install -y --no-install-recommends \ 
    ffmpeg python3 python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./ 
RUN python3 -m pip install -r requirements.txt

# Copy the rest of the app
COPY . .

ENV APPNAME YDL
ENV ADMINUSER admin
ENV PASSWORD youtube
RUN python3 ./setup.py --appname=${APPNAME} --username=${ADMINUSER} --password=${PASSWORD}

# Need to add in supervisord to make daemon work?

# Port 8080 is exposed, people can adjust which port forwards to this
EXPOSE 8080
CMD ["gunicorn", "--workers 4", "--threads 4", "--bind 0.0.0.0:8080", "wsgi:app"]
# Needed because gunicorn doesn't execute in the correct environment
# CMD ["./startup.sh"]