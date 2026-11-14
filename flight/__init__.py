from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config["SECRET_KEY"] = "flight_secret_key_123456"  # Cần thiết cho session đăng nhập
app.config["SQLALCHEMY_DATABASE_URI"] = ("mysql+pymysql://root:Kiet1311@127.0.0.1:3306/flightdb?charset=utf8mb4")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app=app)

# Khởi tạo LoginManager cho hệ thống Đăng nhập
login = LoginManager(app=app)


@login.user_loader
def load_user(user_id):
    from flight import dao

    return dao.get_user_by_id(user_id)