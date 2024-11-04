from flask import Blueprint
app = Blueprint("general", __name__)

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'