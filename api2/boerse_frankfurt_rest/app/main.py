import health_check
import interface
from flasgger import Swagger
from flask import Flask
from flask_graphite import FlaskGraphite
from utils import get_env

app = Flask(__name__)
swagger = Swagger(app)

app.config["FLASK_GRAPHITE_HOST"] = get_env("GRAPHITE_SERVER", "127.0.0.1")
app.config["FLASK_GRAPHITE_PORT"] = 2003

FlaskGraphite(app)

app.register_blueprint(interface.app)
app.register_blueprint(health_check.app)

if __name__ == "__main__":
    app.run()
