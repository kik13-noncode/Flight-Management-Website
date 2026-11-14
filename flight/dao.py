from datetime import datetime
from flight import db, app
from flight.models import Flight, TicketClass, User, UserRoleEnum
import cloudinary.uploader
import hashlib


def load_flight(from_city=None, to_city=None, departure_date=None):
    query = Flight.query

    # Lọc điểm đi
    if from_city:
        query = query.filter(Flight.from_city == from_city.strip())

    # Lọc điểm đến
    if to_city:
        query = query.filter(Flight.to_city == to_city.strip())

    # Lọc ngày đi
    if departure_date:
        if isinstance(departure_date, str):
            try:
                departure_date = datetime.strptime(
                    departure_date.strip(), "%Y-%m-%d"
                ).date()
            except ValueError:
                departure_date = None

        if departure_date:
            query = query.filter(Flight.departure_date == departure_date)

    return query.order_by(Flight.name).all()


# -------------------------------------------------------------
# BỔ SUNG CÁC HÀM XỬ LÝ USER CHO ĐĂNG NHẬP / ĐĂNG KÝ
# -------------------------------------------------------------
def check_login(username, password):
    if username and password:
        # Nếu dùng hash MD5 cho password, bạn có thể bỏ comment dòng bên dưới:
        # password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
        return User.query.filter(User.username == username.strip(), User.password == password.strip()).first()
    return None


def get_user_by_id(user_id):
    return User.query.get(int(user_id))


def add_user(name, username, password, avatar=None):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    u = User(name=name.strip(), username=username.strip(), password=password,
             avatar="https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg",
             user_role=UserRoleEnum.USER
             )

    if avatar:
        res = cloudinary.uploader.upload(avatar)
        print(res)
        u.avatar = res['secure_url']

    db.session.add(u)
    db.session.commit()
    return True
