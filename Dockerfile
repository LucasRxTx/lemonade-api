FROM python:3.11-slim as build

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get -y update && apt-get -y install python3-dev tini libpq-dev gcc

RUN addgroup --gid 10001 app \
    && adduser \
    --gid 10001 \
    --uid 10001 \
    --system \
    --no-create-home \
    --disabled-login \
    app

COPY requirements.txt /tmp/

RUN pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    -r /tmp/requirements.txt

# Intentionally not removing libpq-dev or tini.
# libpq-dev has shared object libraries that are required
RUN apt-get -y remove python3-dev gcc && apt-get -y autoremove

COPY . /code
WORKDIR /code/src
RUN chown -R app:app /code
USER app


ENTRYPOINT [ "/usr/bin/tini", "--"]
