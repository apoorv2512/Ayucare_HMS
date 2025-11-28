from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,timezone
from sqlalchemy.sql import func
import os
from werkzeug.utils import secure_filename
from flask import url_for
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'  # Specify the table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_picture = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(500), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class dailyrecord(db.Model):  # Class name should be singular and in PascalCase
    __tablename__ = 'dailyrecord'  # Table name for health records
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    systolic = db.Column(db.Integer, nullable=True)
    diastolic = db.Column(db.Integer, nullable=True)
    fasting_sugar = db.Column(db.Float, nullable=True)
    bedtime_sugar = db.Column(db.Float, nullable=True)
    record_date = db.Column(db.Date, server_default=func.current_date())  # Automatically set the current date
    record_time = db.Column(db.Time, server_default=func.current_time())
    weight=db.Column(db.Float, nullable=True)
    height=db.Column(db.Float, nullable=True)
    

    # Foreign key relationship to associate records with a specific user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Match table name 'users'
    user = db.relationship('User', backref=db.backref('dailyrecord', lazy=True))  # Use 'User' for relationship



class UserProfile(db.Model):
    __tablename__ = 'user_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, unique=True)  # Foreign key for user authentication model
    
    phone_number = db.Column(db.String(15), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Integer, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<UserProfile {self.first_name} {self.last_name}>'
    

    

     
    
    


