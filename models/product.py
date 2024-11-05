
from sqlalchemy import *
from extentions import db

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String, unique=True, nullable=False ,index=True)
    description = db.Column(String, nullable=False, index=True)
    price = db.Column(Integer , nullable=False ,index=True)


