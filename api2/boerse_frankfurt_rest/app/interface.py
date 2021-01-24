from flask import Blueprint

app = Blueprint('interface', __name__)


@app.route("/")
def hello():
    return "Hello World from Flask"
