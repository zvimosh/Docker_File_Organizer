# set base image (host OS)
FROM python:alpine3.14

# set the working directory in the container
WORKDIR /app/

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY src/ .

# copy the content of the local src directory to the working directory
COPY config/ ./config

# command to run on container start
CMD [ "python", "./fileOrganizer.py" ]