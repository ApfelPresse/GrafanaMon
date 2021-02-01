FROM python:3.8-slim

ENV PROXY_HOST=127.0.0.1

WORKDIR /app
ADD ./app /app

RUN pip3 install -r requirements.txt

CMD [ "python3", "main.py" ]