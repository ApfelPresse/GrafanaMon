FROM python:3.7

WORKDIR /docker_stats

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .

CMD [ "python", "./main.py" ]