FROM python:3.11-buster

# set working directory
WORKDIR /app/

COPY setup.py ./
COPY ./pyallsky/ ./pyallsky
COPY ./bin ./bin

RUN python setup.py install

# disable buffering so that logs are rendered to stdout asap
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "/app/bin/allsky_scheduler -v -f -c $CONFIG_FILE"]
