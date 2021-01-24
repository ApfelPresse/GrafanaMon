import flask
import pymongo
from flask import Blueprint

from utils import get_env

app = Blueprint('health-check', __name__)


@app.route("/health-check")
def hello():
    client = pymongo.MongoClient(f'mongodb://{get_env("MONGO_HOST", "127.0.0.1")}:27017/')
    client.server_info()
    return flask.Response(status=201)
