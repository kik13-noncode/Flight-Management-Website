import re
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from flight import db
from flight.models import Airport, Flight, Seat, TicketClass
from flight.models_nhan_vien import (FareClass, IntermediateStop, Invoice, Payment,
                                     Regulation, Ticket)

DEFAULT_IMAGE = "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg"

# (tên hạng = Seat.seat_type, tiền tố số ghế) - chỉ dùng làm dự phòng khi bảng fare_class còn trống.
# Danh sách hạng vé thật lấy từ CSDL qua get_seat_types().
SEAT_TYPES = [("Thương gia", "E"), ("Phổ thông", "F")]

# ---------------------------------------------------------------------
# QUY ĐỊNH (admin được phép thay đổi)
# ---------------------------------------------------------------------
DEFAULT_RULES = {
    "max_airports": (10, "Số sân bay tối đa của hệ thống"),
    "min_flight_minutes": (30, "Thời gian bay tối thiểu (phút)"),
    "max_stops": (2, "Số sân bay trung gian tối đa"),
    "min_stop_minutes": (20, "Thời gian dừng tối thiểu tại sân bay trung gian (phút)"),
    "max_stop_minutes": (30, "Thời gian dừng tối đa tại sân bay trung gian (phút)"),
    "sell_before_hours": (4, "Chỉ bán vé tại quầy trước giờ khởi hành (giờ)"),
    "book_before_hours": (12, "Chỉ cho khách đặt vé online trước giờ khởi hành (giờ)"),
}

# Hạng vé và đơn giá mặc định ban đầu: (tên, tiền tố ghế, thứ hạng, đơn giá)
DEFAULT_FARE_CLASSES = [
    ("Thương gia", "E", 1, 2400000),
    ("Phổ thông", "F", 2, 1500000),
]


def get_rule(key):
    r = db.session.get(Regulation, key)
    if r is not None:
        try:
            return int(r.value)
        except ValueError:
            pass
    return DEFAULT_RULES[key][0]


def get_all_rules():
    """{rule_key: giá trị hiện hành} - luôn đọc từ MySQL (bảng regulation)."""
    return {k: get_rule(k) for k in DEFAULT_RULES}


def ensure_default_rules():
    """Tạo các quy định / hạng vé mặc định còn thiếu (không ghi đè giá trị admin đã đổi)."""
    for key, (value, desc) in DEFAULT_RULES.items():
        if db.session.get(Regulation, key) is None:
            db.session.add(Regulation(rule_key=key, value=str(value), description=desc))
    if FareClass.query.count() == 0:
        for name, prefix, rank, price in DEFAULT_FARE_CLASSES:
            db.session.add(FareClass(name=name, prefix=prefix, rank=rank,
                                     default_price=price, is_active=True))
    db.session.commit()


def validate_rules(form):
    """Kiểm tra form thay đổi quy định của admin. Trả về ({key: int}, [lỗi])."""
    errors, clean = [], {}
    for key, (_, label) in DEFAULT_RULES.items():
        value = _to_int(form.get(key))
        if value is None:
            errors.append(f"{label}: phải là số nguyên.")
        else:
            clean[key] = value
    if errors:
        return clean, errors

    airport_count = Airport.query.count()
    if clean["max_airports"] < max(2, airport_count):
        errors.append(f"Số sân bay tối đa phải >= 2 và không nhỏ hơn số sân bay hiện có ({airport_count}).")
    if clean["min_flight_minutes"] < 1:
        errors.append("Thời gian bay tối thiểu phải >= 1 phút.")
    if clean["max_stops"] < 0:
        errors.append("Số sân bay trung gian tối đa không được âm.")
    if clean["min_stop_minutes"] < 0:
        errors.append("Thời gian dừng tối thiểu không được âm.")
    if clean["max_stop_minutes"] < clean["min_stop_minutes"]:
        errors.append("Thời gian dừng tối đa phải >= thời gian dừng tối thiểu.")
    if clean["sell_before_hours"] < 0:
        errors.append("Thời gian đóng bán vé tại quầy không được âm.")
    if clean["book_before_hours"] < 0:
        errors.append("Thời gian đóng đặt vé online không được âm.")
    return clean, errors


def save_rules(clean):
    """Ghi các quy định mới vào bảng regulation (1 transaction)."""
    try:
        for key, value in clean.items():
            r = db.session.get(Regulation, key)
            if r is None:
                r = Regulation(rule_key=key, description=DEFAULT_RULES[key][1], value=str(value))
                db.session.add(r)
            else:
                r.value = str(value)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise SaleError("Lỗi CSDL, chưa lưu được quy định. Quy định cũ được giữ nguyên.")


def load_fare_classes(active_only=False):
    q = FareClass.query
    if active_only:
        q = q.filter(FareClass.is_active.is_(True))
    return q.order_by(FareClass.rank, FareClass.id).all()


def get_seat_types(active_only=False):
    """[(tên hạng, tiền tố ghế)] lấy từ bảng fare_class (admin thay đổi được)."""
    rows = load_fare_classes(active_only)
    if rows:
        return [(r.name, r.prefix) for r in rows]
    return [] if active_only and FareClass.query.count() else list(SEAT_TYPES)


def default_price_of(seat_type):
    r = FareClass.query.filter_by(name=seat_type).first()
    return r.default_price if r else None


def load_airports():
    return Airport.query.order_by(Airport.name).all()


# ---------------------------------------------------------------------
# BÁN VÉ
# ---------------------------------------------------------------------
class SaleError(Exception):
    """Lỗi nghiệp vụ. .errors là danh sách thông báo hiển thị cho nhân viên."""

    def __init__(self, errors):
        if isinstance(errors, str):
            errors = [errors]
        self.errors = errors
        super().__init__("; ".join(errors))


def departure_datetime(flight):
    return datetime.combine(flight.departure_date, flight.departure)


def is_open_for_sale(flight, now=None):
    """Chuyến bay còn mở bán tại quầy nếu giờ khởi hành còn cách hiện tại từ sell_before_hours giờ."""
    now = now or datetime.now()
    return departure_datetime(flight) - now >= timedelta(hours=get_rule("sell_before_hours"))


def is_open_for_booking(flight, now=None):
    """Khách đặt vé online chỉ được đặt khi giờ khởi hành còn cách hiện tại từ book_before_hours giờ."""
    now = now or datetime.now()
    return departure_datetime(flight) - now >= timedelta(hours=get_rule("book_before_hours"))


def price_of(flight, seat_type):
    """Giá vé của một loại ghế: lấy từ TicketClass trùng tên, không có thì lấy giá chuyến bay."""
    for tc in flight.ticket_classes:
        if tc.name.strip() == seat_type:
            return tc.price or 0
    return flight.price or 0


def free_seat_counts(flight_ids):
    """Trả về {(flight_id, seat_type): số ghế trống}."""
    if not flight_ids:
        return {}
    rows = (
        db.session.query(Seat.flight_id, Seat.seat_type, func.count(Seat.id))
        .filter(Seat.flight_id.in_(flight_ids), Seat.is_booked.is_(False))
        .group_by(Seat.flight_id, Seat.seat_type)
        .all()
    )
    return {(f, t): n for f, t, n in rows}


def search_sellable_flights(from_city=None, to_city=None, departure_date=None, name=None):
    """Tìm chuyến bay cho nhân viên: chỉ giữ chuyến còn mở bán và còn ghế trống.

    Trả về (danh sách {flight, types:[{name, price, free}]}, số chuyến bị đóng bán).
    """
    query = Flight.query
    if from_city:
        query = query.filter(Flight.from_city == from_city.strip())
    if to_city:
        query = query.filter(Flight.to_city == to_city.strip())
    if departure_date:
        try:
            d = datetime.strptime(departure_date.strip(), "%Y-%m-%d").date()
            query = query.filter(Flight.departure_date == d)
        except ValueError:
            pass
    if name:
        query = query.filter(Flight.name.like(f"%{name.strip()}%"))

    flights = query.order_by(Flight.departure_date, Flight.departure).all()
    now = datetime.now()
    # Chuyến đã bay rồi thì không hiển thị; chuyến còn dưới 4h thì đếm là "đóng bán"
    upcoming = [f for f in flights if departure_datetime(f) > now]
    open_flights = [f for f in upcoming if is_open_for_sale(f, now)]
    closed_count = len(upcoming) - len(open_flights)

    counts = free_seat_counts([f.id for f in open_flights])
    rows = []
    for f in open_flights:
        types = []
        for seat_type, _ in get_seat_types():
            free = counts.get((f.id, seat_type), 0)
            types.append({"name": seat_type, "price": price_of(f, seat_type), "free": free})
        if any(t["free"] > 0 for t in types):
            rows.append({"flight": f, "types": types})
    return rows, closed_count


def get_seat_map(flight):
    """[{name, price, seats}] theo từng loại ghế, ghế sắp theo số thứ tự (E1, E2, ...)."""
    seats = Seat.query.filter_by(flight_id=flight.id).all()

    def order(seat):
        digits = re.sub(r"\D", "", seat.seat_number)
        return int(digits) if digits else 0

    result = []
    for seat_type, _ in get_seat_types():
        group = sorted([s for s in seats if s.seat_type == seat_type], key=order)
        if group:
            result.append({"name": seat_type, "price": price_of(flight, seat_type),
                           "seats": group})
    return result


_ID_RE = re.compile(r"^(\d{9}|\d{12})$")      # CMND 9 số hoặc CCCD 12 số
_PHONE_RE = re.compile(r"^0\d{9}$")           # số điện thoại 10 số


def validate_passenger(info, label):
    errors = []
    name = (info.get("name") or "").strip()
    id_number = (info.get("id_number") or "").strip()
    phone = (info.get("phone") or "").strip()
    if not name:
        errors.append(f"Ghế {label}: chưa nhập họ tên hành khách.")
    elif len(name) > 100:
        errors.append(f"Ghế {label}: họ tên quá dài.")
    if not _ID_RE.match(id_number):
        errors.append(f"Ghế {label}: CMND/CCCD phải gồm 9 hoặc 12 chữ số.")
    if not _PHONE_RE.match(phone):
        errors.append(f"Ghế {label}: số điện thoại phải gồm 10 chữ số, bắt đầu bằng 0.")
    return errors


def create_sale(staff_id, flight_id, passengers):
    """Bán vé tại quầy: tạo 1 hóa đơn cho nhiều ghế (luồng thay thế 3.2).

    passengers: {seat_id(int): {"name", "id_number", "phone"}}
    Toàn bộ ghi CSDL nằm trong một transaction. Lỗi CSDL -> rollback (ngoại lệ 5.1).
    """
    flight = db.session.get(Flight, flight_id)
    if flight is None:
        raise SaleError("Chuyến bay không tồn tại.")
    if not is_open_for_sale(flight):
        # Ngoại lệ 2.1: chuyến bay trước 4h không còn mở bán
        raise SaleError("Chuyến bay đã đóng bán (chỉ bán trước giờ khởi hành "
                        f"{get_rule('sell_before_hours')} giờ).")
    if not passengers:
        raise SaleError("Chưa chọn ghế nào.")

    try:
        seats = (
            Seat.query.filter(Seat.id.in_(list(passengers)), Seat.flight_id == flight_id)
            .with_for_update()
            .all()
        )
        if len(seats) != len(passengers):
            raise SaleError("Có ghế không thuộc chuyến bay này.")

        errors = []
        for seat in seats:
            if seat.is_booked:
                errors.append(f"Ghế {seat.seat_number} không còn trống, vui lòng chọn ghế khác.")
            errors += validate_passenger(passengers[seat.id], seat.seat_number)
        if errors:
            raise SaleError(errors)

        invoice = Invoice(staff_id=staff_id, channel="COUNTER", status="PAID")
        db.session.add(invoice)
        db.session.flush()

        total = 0
        for seat in seats:
            info = passengers[seat.id]
            price = price_of(flight, seat.seat_type)
            db.session.add(Ticket(
                invoice_id=invoice.id, flight_id=flight_id, seat_id=seat.id,
                passenger_name=info["name"].strip(),
                id_number=info["id_number"].strip(),
                phone=info["phone"].strip(), price=price,
            ))
            seat.is_booked = True   # khách mua tại quầy nên Seat.user_id để trống
            total += price

        invoice.total = total
        db.session.add(Payment(invoice_id=invoice.id, method="CASH",
                               amount=total, status="SUCCESS"))
        db.session.commit()
        return invoice
    except SaleError:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        raise SaleError("Lỗi CSDL, không ghi nhận được vé. Nhân viên hãy ghi lại "
                        "thông tin khách hàng và nhập lại sau.")


# ---------------------------------------------------------------------
# LẬP LỊCH CHUYẾN BAY
# ---------------------------------------------------------------------
def _to_int(text):
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


def _to_float(text):
    try:
        return float(str(text).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def parse_and_validate_schedule(form):
    """Đọc form lập lịch và kiểm tra theo quy định.

    Trả về (data, errors). Nếu errors rỗng thì data đã sẵn sàng cho create_schedule.
    """
    errors = []
    airports = {a.id: a for a in load_airports()}
    min_flight = get_rule("min_flight_minutes")
    max_stops = get_rule("max_stops")
    min_stop = get_rule("min_stop_minutes")
    max_stop = get_rule("max_stop_minutes")

    name = (form.get("name") or "").strip()
    from_id = (form.get("from_airport") or "").strip()
    to_id = (form.get("to_airport") or "").strip()

    if not name:
        errors.append("Chưa nhập mã/tên chuyến bay.")
    elif len(name) > 50:
        errors.append("Mã/tên chuyến bay tối đa 50 ký tự.")

    if from_id not in airports:
        errors.append("Chưa chọn sân bay đi hợp lệ.")
    if to_id not in airports:
        errors.append("Chưa chọn sân bay đến hợp lệ.")
    if from_id and from_id == to_id:
        errors.append("Sân bay đi và sân bay đến phải khác nhau.")

    departure_dt = None
    try:
        departure_dt = datetime.strptime(
            f"{form.get('departure_date', '').strip()} {form.get('departure_time', '').strip()}",
            "%Y-%m-%d %H:%M")
        if departure_dt <= datetime.now():
            errors.append("Thời điểm khởi hành phải ở tương lai.")
    except ValueError:
        errors.append("Ngày hoặc giờ khởi hành không hợp lệ.")

    duration = _to_int(form.get("duration"))
    if duration is None:
        errors.append("Thời gian bay phải là số phút.")
    elif duration < min_flight:
        errors.append(f"Thời gian bay tối thiểu là {min_flight} phút.")

    # Các hạng vé đang áp dụng (admin quy định số lượng hạng vé)
    classes = []
    active_types = get_seat_types(active_only=True)
    if not active_types:
        errors.append("Hệ thống chưa có hạng vé nào đang áp dụng, vui lòng liên hệ quản trị viên.")
    for idx, (seat_type, prefix) in enumerate(active_types, start=1):
        price = _to_float(form.get(f"price_{idx}"))
        seats = _to_int(form.get(f"seats_{idx}"))
        if price is None or price < 0:
            errors.append(f"Hạng {idx} ({seat_type}): giá vé không hợp lệ.")
        if seats is None or seats < 0:
            errors.append(f"Hạng {idx} ({seat_type}): số ghế phải là số nguyên không âm.")
        classes.append({"name": seat_type, "prefix": prefix, "price": price, "seats": seats})
    if classes and all(c["seats"] is not None for c in classes) and sum(c["seats"] for c in classes) <= 0:
        errors.append("Tổng số ghế phải lớn hơn 0.")

    # Sân bay trung gian
    stop_ids = form.getlist("stop_airport")
    stop_minutes = form.getlist("stop_minutes")
    stop_notes = form.getlist("stop_note")
    stops = []
    for i, sid in enumerate(stop_ids):
        sid = sid.strip()
        minutes_text = stop_minutes[i] if i < len(stop_minutes) else ""
        if not sid and not minutes_text.strip():
            continue
        minutes = _to_int(minutes_text)
        if sid not in airports:
            errors.append(f"Sân bay trung gian #{i + 1}: chưa chọn sân bay hợp lệ.")
        elif sid in (from_id, to_id):
            errors.append(f"Sân bay trung gian #{i + 1}: không được trùng sân bay đi hoặc đến.")
        if minutes is None or not (min_stop <= minutes <= max_stop):
            errors.append(f"Sân bay trung gian #{i + 1}: thời gian dừng phải từ "
                          f"{min_stop} đến {max_stop} phút.")
        stops.append({"airport": sid, "minutes": minutes,
                      "note": (stop_notes[i].strip() if i < len(stop_notes) else "")})
    if len(stops) > max_stops:
        errors.append(f"Chỉ được tối đa {max_stops} sân bay trung gian.")
    if len({s["airport"] for s in stops}) != len(stops):
        errors.append("Các sân bay trung gian không được trùng nhau.")

    # Trùng lịch: cùng mã chuyến bay, cùng ngày giờ
    if name and departure_dt:
        dup = Flight.query.filter_by(
            name=name, departure_date=departure_dt.date(), departure=departure_dt.time()
        ).first()
        if dup:
            errors.append("Trùng lịch: đã có chuyến bay cùng mã, ngày và giờ khởi hành.")

    data = {
        "name": name, "from_airport": airports.get(from_id), "to_airport": airports.get(to_id),
        "departure_dt": departure_dt, "duration": duration, "classes": classes,
        "stops": [dict(s, airport_obj=airports.get(s["airport"])) for s in stops],
    }
    return data, errors


def create_schedule(data):
    """Ghi chuyến bay, hạng vé, sân bay trung gian và sinh sẵn các ghế (1 transaction)."""
    try:
        stop_total = sum(s["minutes"] for s in data["stops"])
        arrival_dt = data["departure_dt"] + timedelta(minutes=data["duration"] + stop_total)
        offered = [c for c in data["classes"] if c["seats"] > 0]
        transit = [s["airport_obj"].name for s in data["stops"]]

        flight = Flight(
            name=data["name"], image=DEFAULT_IMAGE,
            from_city=data["from_airport"].city, to_city=data["to_airport"].city,
            from_airport_id=data["from_airport"].id, to_airport_id=data["to_airport"].id,
            transit_1=transit[0] if len(transit) > 0 else None,
            transit_2=transit[1] if len(transit) > 1 else None,
            departure_date=data["departure_dt"].date(),
            departure=data["departure_dt"].time(),
            arrival=arrival_dt.time(),
            price=min(c["price"] for c in offered),
        )
        db.session.add(flight)
        db.session.flush()

        for c in offered:
            db.session.add(TicketClass(name=c["name"], price=c["price"], flight_id=flight.id))
            db.session.add_all([
                Seat(flight_id=flight.id, seat_type=c["name"],
                     seat_number=f"{c['prefix']}{n}", is_booked=False)
                for n in range(1, c["seats"] + 1)
            ])

        for order, s in enumerate(data["stops"], start=1):
            db.session.add(IntermediateStop(
                flight_id=flight.id, stop_order=order, airport_id=s["airport"],
                stop_minutes=s["minutes"], note=s["note"]))

        db.session.commit()
        return flight
    except SQLAlchemyError:
        db.session.rollback()
        raise SaleError("Lỗi CSDL, không lưu được lịch chuyến bay. Dữ liệu cũ được giữ nguyên.")


def recent_flights(limit=10):
    return Flight.query.order_by(Flight.id.desc()).limit(limit).all()
