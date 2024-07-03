FROM python:3.11-buster

# set working directory
WORKDIR /app/

COPY setup.py ./
COPY ./pyallsky/ ./pyallsky
COPY ./bin ./bin

RUN python setup.py install

# disable buffering so that logs are rendered to stdout asap
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/bin/allsky_scheduler"]
CMD ["-f", "-c", "/app/allsky_scheduler.conf"]
