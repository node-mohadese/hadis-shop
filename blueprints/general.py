from flask import Blueprint, render_template
from models.product import Product
app = Blueprint("general", __name__)


@app.route('/')
def main():  # put application's c
    products= Product.query.all()
    return render_template('main.html', products=products)


@app.route('/about')
def about():  # put application's code here
    return render_template('about.html')

