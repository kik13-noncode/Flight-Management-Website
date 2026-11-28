from datetime import datetime, timedelta

from sqlalchemy import func, extract

from flight import db
from flight.models import Airport, Flight, User, UserRoleEnum, Seat
from flight.dao_nhan_vien import get_rule, get_seat_types, Invoice, Ticket
import cloudinary.uploader
import hashlib
from datetime import datetime


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

    # Chỉ hiển thị chuyến bay còn chỗ và cách giờ khởi hành ít nhất book_before_hours giờ (quy định do admin đặt)
    min_time = datetime.now() + timedelta(hours=get_rule("book_before_hours"))
    valid_flights = []
    for f in query.order_by(Flight.name).all():
        flight_datetime = datetime.combine(f.departure_date, f.departure)
        has_seat = Seat.query.filter(
            Seat.flight_id == f.id,
            Seat.is_booked == False
        ).first() is not None

        if flight_datetime >= min_time and has_seat:
            valid_flights.append(f)

    return valid_flights


# -------------------------------------------------------------
# BỔ SUNG CÁC HÀM XỬ LÝ USER CHO ĐĂNG NHẬP / ĐĂNG KÝ
# -------------------------------------------------------------
def check_login(username, password):
    if username and password:
        # Nếu dùng hash MD5 cho password, bạn có thể bỏ comment dòng bên dưới:
        password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
        return User.query.filter(User.username == username.strip(), User.password == password.strip()).first()
    return None


def load_cities():
    """Danh sách tỉnh/thành có sân bay (dùng cho ô chọn điểm đi / điểm đến)."""
    return [c for (c,) in db.session.query(Airport.city).order_by(Airport.city).all()]


def get_user_by_id(user_id):
    return User.query.get(int(user_id))


def add_user(name, username, password, cccd=None, phone=None, avatar=None):
    try:
        password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
        u = User(name=name.strip(), username=username.strip(), password=password,
                 cccd=cccd.strip() if cccd else None,
                 phone=phone.strip() if phone else None,
                 avatar="https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg",
                 user_role=UserRoleEnum.USER
                 )

        if avatar and avatar.filename != "":
            res = cloudinary.uploader.upload(avatar)
            u.avatar = res['secure_url']

        db.session.add(u)
        db.session.commit()
        return None  # Thành công thì không có lỗi
    except Exception as ex:
        db.session.rollback()
        return str(ex)  # Trả về nguyên văn lỗi thật


# -------------------------------------------------------------
# TỰ ĐỘNG TÌM GHẾ TRỐNG & XÁC NHẬN ĐẶT VÉ CHO KHÁCH HÀNG
# -------------------------------------------------------------
def find_seat(flight_id, ticket_class_name):
    # Hạng vé lấy từ bảng fare_class; hạng lạ (vd. "Phổ thông đặc biệt") quy về hạng thấp nhất
    seat_types = [name for name, _ in get_seat_types()]
    name = ticket_class_name.strip()
    target_seat_type = name if name in seat_types else (seat_types[-1] if seat_types else "Phổ thông")

    return Seat.query.filter(
        Seat.flight_id == int(flight_id),
        Seat.seat_type == target_seat_type,
        Seat.is_booked == False
    ).order_by(Seat.id.asc()).first()


def user_booking(seat_id, user_id):
    seat = Seat.query.get(int(seat_id))
    if seat and not seat.is_booked:
        seat.user_id = int(user_id)
        seat.is_booked = True
        db.session.commit()
    return seat

def get_user_tickets(user_id):
    return Seat.query.filter(
        Seat.user_id == int(user_id),
        Seat.is_booked == True
    ).order_by(Seat.id.desc()).all()


# THỐNG KÊ BÁO CÁO
# Số ghế đã bán cho từng chuyến bay
def count_seats_by_flight():
    """Số ghế đã bán theo từng chuyến bay (tương tự count_products_by_cate)."""
    return (db.session.query(Flight.id,Flight.name,func.count(Seat.id))
            .join(Seat, Seat.flight_id == Flight.id, isouter=True)
            .filter(Seat.is_booked == True)
            .group_by(Flight.id).all())


# doanh thu theo từng chuyến bay
def cal_revenue_by_flight(kw = None):
    query = (db.session.query(Flight.id,Flight.name,func.count(Ticket.price)).join(Ticket, Ticket.flight_id == Flight.id).group_by(Flight.id))
    if kw:
        query = query.filter(Flight.name.contains(kw))
    return query.all()

# Doanh thu theo tháng
def cal_revenue_by_time(time='month', year=None):
    if not year:
        year = datetime.now().year
    query = (db.session.query(extract(time, Invoice.created_at),func.sum(Invoice.total))
            .filter(Invoice.status == 'PAID',extract('year', Invoice.created_at) == year)
            .group_by(extract(time, Invoice.created_at))
            .order_by(extract(time, Invoice.created_at)))
    return query.all()

# số vé bán theo hạng ghế
def cal_tickets_by_seat_type():
    return (db.session.query(Seat.seat_type, func.count(Seat.id)).filter(Seat.is_booked == True)
            .group_by(Seat.seat_type).all())
