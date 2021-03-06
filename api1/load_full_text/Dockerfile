FROM alpine:3.12

# This hack is widely applied to avoid python printing issues in docker containers.
# See: https://github.com/Docker-Hub-frolvlad/docker-alpine-python3/pull/13
ENV PYTHONUNBUFFERED=1
ENV PROXY_HOST=127.0.0.1

RUN echo "**** install Python ****" && \
    apk add --no-cache python3 && \
    if [ ! -e /usr/bin/python ]; then ln -sf python3 /usr/bin/python ; fi && \
    \
    echo "**** install pip ****" && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools wheel && \
    if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi
	
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
RUN pip install psycopg2

RUN apk add libxml2-dev libxslt-dev python3-dev
RUN pip3 install lxml

RUN apk add libffi-dev

#RUN apk add --no-cache build-essential libpng-dev

RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add postgresql \
    && apk add postgresql-dev \
    && pip install psycopg2 \
    && apk add jpeg-dev zlib-dev libjpeg \
    && pip install Pillow \
    && apk del build-deps

RUN apk add build-base
RUN pip install cython

RUN pip install cryptography==2.8 news-please pymongo fake-headers requests graphitesender schedule tqdm cchardet

RUN pip cache purge

WORKDIR /app
ADD ./app /app

RUN pip3 install -r requirements.txt

CMD [ "python3", "main.py" ]
