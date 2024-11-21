from sqlalchemy import *
from extentions import db
from flask_login import UserMixin


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(Integer, primary_key=True)
    username = db.Column(String, unique=True, nullable=False, index=True)
    password = db.Column(String, nullable=False, index=True)
    phone = db.Column(String(11), nullable=False, index=True)
    address = db.Column(String, nullable=False, index=True)
