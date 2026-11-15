from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import cloudinary

app = Flask(__name__)

app.config["SECRET_KEY"] = "flight_secret_key_123456"  # Cần thiết cho session đăng nhập
app.config["SQLALCHEMY_DATABASE_URI"] = ("mysql+pymysql://root:Kiet1311@127.0.0.1:3306/flightdb?charset=utf8mb4")
app.config["SECRET_KEY"] = "flight_secret_key_123456"
app.config["SQLALCHEMY_DATABASE_URI"] = ("mysql+pymysql://root:Flight123@localhost:3306/flightdb?charset=utf8mb4")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app=app)
login = LoginManager(app=app)

cloudinary.config(cloud_name='i3c1j8ys', api_key='463393967499462', api_secret='VvEuJK0Mxc6yDjBcJlXXU4wu1UM')
