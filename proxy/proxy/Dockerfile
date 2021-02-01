FROM stibbons31/alpine-s6-python3:latest

ENV SRC_IP="0.0.0.0"
ENV SRC_PORT=8080
ENV DST_IP="proxy"
ENV DST_PORT=8888

RUN apk add --no-cache g++ python3-dev

RUN pip3 install --no-cache --upgrade pip
RUN pip3 install service_identity twisted

WORKDIR /app
ADD ./app /app

CMD [ "twistd", "-y", "main.py", "-n"]