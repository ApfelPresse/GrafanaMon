FROM python:3.8-slim

WORKDIR /app
ADD ./app /app

RUN pip3 install -r requirements.txt

CMD [ "python3", "main.py" ]