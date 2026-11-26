import hashlib
from datetime import datetime, timedelta

from flight import app, db
from flight import dao_nhan_vien as dao
from flight import models_nhan_vien  
from flight.models import Airport, Flight, User, UserRoleEnum

# Chỉ dùng khi chưa chạy `python -m flight.models` (bảng sân bay còn trống)
AIRPORTS = [
    ("TSN", "Tân Sơn Nhất", "Sài Gòn"), ("NB", "Nội Bài", "Hà Nội"),
    ("DN", "Đà Nẵng", "Đà Nẵng"), ("CR", "Cam Ranh", "Khánh Hòa"),
    ("PQ", "Phú Quốc", "An Giang"), ("CB", "Cát Bi", "Hải Phòng"),
    ("PB", "Phú Bài", "Huế"), ("V", "Vinh", "Nghệ An"),
    ("CT", "Cần Thơ", "Cần Thơ"), ("LK", "Liên Khương", "Lâm Đồng"),
]


class _Form(dict):
    """Giả lập request.form (chỉ cần get / getlist)."""

    def get(self, key, default=None):
        values = dict.get(self, key)
        return values[0] if values else default

    def getlist(self, key):
        return dict.get(self, key, [])


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def add_user(name, username, password, role):
    if not User.query.filter_by(username=username).first():
        db.session.add(User(
            name=name, username=username, password=md5(password), user_role=role,
            avatar="https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg"))


def add_flight(name, from_id, to_id, in_hours, duration, stops=()):
    if Flight.query.filter_by(name=name).first():
        return
    when = datetime.now() + timedelta(hours=in_hours)
    form = _Form({
        "name": [name], "from_airport": [from_id], "to_airport": [to_id],
        "departure_date": [when.strftime("%Y-%m-%d")],
        "departure_time": [when.strftime("%H:%M")], "duration": [str(duration)],
        "price_1": ["2400000"], "seats_1": ["6"],
        "price_2": ["1500000"], "seats_2": ["24"],
        "stop_airport": [s[0] for s in stops], "stop_minutes": [str(s[1]) for s in stops],
        "stop_note": ["" for _ in stops],
    })
    data, errors = dao.parse_and_validate_schedule(form)
    if errors:
        print("Bỏ qua", name, errors)
        return
    dao.create_schedule(data)


def main():
    with app.app_context():
        db.create_all()
        dao.ensure_default_rules()
        if Airport.query.count() == 0:
            for aid, name, city in AIRPORTS:
                db.session.add(Airport(id=aid, name=name, city=city))
        add_user("Nhân viên", "nhanvien", "12345", UserRoleEnum.EMPLOYEE)
        add_user("Quản trị", "admin", "12345", UserRoleEnum.ADMIN)
        db.session.commit()

        add_flight("NV101", "TSN", "NB", 30, 125)
        add_flight("NV205", "TSN", "NB", 52, 190, stops=[("DN", 25)])
        add_flight("NV311", "NB", "DN", 76, 80)
        add_flight("NV-DONG-BAN", "TSN", "LK", 2, 60)  # còn 2h nên đã đóng bán (demo)
        print("Xong. Đăng nhập bằng nhanvien / 12345")


if __name__ == "__main__":
    main()
