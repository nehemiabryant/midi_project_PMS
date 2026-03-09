
#Builder Stage
FROM python:3-slim-bullseye As builder

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y libpq-dev gcc

#Create the Virtual Env
RUN python -m venv /opt/venv
#Activate the virtual env
ENV PATH="opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt
#Operational Stage
FROM python:3-slim-bullseye

RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install -y libpq-dev
RUN rm -rf /var/lib/apt/lists/*

#Get the virtual env from builder stage
COPY --from=builder /opt/venv /opt/venv

WORKDIR PYTHONPROJECT
ENV PATH="/opt/venv/bin:$PATH"
ENV CLOUD_APPS CLOUD_RUN
EXPOSE 8080
COPY . .
RUN /opt/venv/bin/pip install gunicorn

CMD . /opt/venv/bin/activate && exec gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 8 --timeout 0 main:app