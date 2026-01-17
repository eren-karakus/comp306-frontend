from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# register routes (imports must happen after app creation)
import routes  # noqa: F401