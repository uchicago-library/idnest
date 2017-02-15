from flask import Flask
from .blueprint import BLUEPRINT

app = Flask(__name__)

#app.config['STORAGE_BACKEND'] = "MONGODB"
#app.config['MONGO_HOST'] = 'localhost'
#app.config['MONGO_PORT'] = 27017
#app.config['MONGO_DB'] = "dev"

app.register_blueprint(BLUEPRINT)
