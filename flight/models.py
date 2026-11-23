import enum
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import Boolean, Column, Date, Enum, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship
from flight import app, db



# 1. ENUM & MODEL USER

class UserRoleEnum(enum.Enum):
    ADMIN = 1
    USER = 2
    EMPLOYEE = 3

class User(db.Model, UserMixin):
    __tablename__ = "user"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    cccd = Column(String(12), unique=True)
    phone = Column(String(10))
    avatar = Column(String(100))
    user_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.USER)

    seats = relationship("Seat", back_populates="user")

    def __str__(self):
        return self.name



# 2. MODEL AIRPORT, FLIGHT, TICKET CLASS & SEAT

class Airport(db.Model):
    __tablename__ = "airport"

    id = Column(String(10), primary_key=True)               # Mã chữ cái đầu: TST, NB, DN...
    name = Column(String(100), nullable=False)              # Tên sân bay (VD: Tân Sơn Nhất)
    city = Column(String(50), nullable=False, unique=True)  # Tên tỉnh/thành (VD: Sài Gòn)

    departing_flights = relationship(
        "Flight", foreign_keys="Flight.from_airport_id", back_populates="from_airport"
    )
    arriving_flights = relationship(
        "Flight", foreign_keys="Flight.to_airport_id", back_populates="to_airport"
    )

    def __str__(self):
        return f"Sân bay {self.name} ({self.city})"


class Flight(db.Model):
    __tablename__ = "flight"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    price = Column(Float, default=0)
    image = Column(String(100))
    from_city = Column(String(50), nullable=False)
    to_city = Column(String(50), nullable=False)
    from_airport_id = Column(String(10), ForeignKey("airport.id"), nullable=True)
    to_airport_id = Column(String(10), ForeignKey("airport.id"), nullable=True)
    transit_1 = Column(String(100), nullable=True)
    transit_2 = Column(String(100), nullable=True)
    departure_date = Column(Date, nullable=False)
    departure = Column(Time, nullable=False)
    arrival = Column(Time, nullable=False)

    from_airport = relationship(
        "Airport", foreign_keys=[from_airport_id], back_populates="departing_flights"
    )
    to_airport = relationship(
        "Airport", foreign_keys=[to_airport_id], back_populates="arriving_flights"
    )
    ticket_classes = relationship(
        "TicketClass", back_populates="flight", cascade="all, delete-orphan"
    )
    seats = relationship(
        "Seat", back_populates="flight", cascade="all, delete-orphan"
    )

    def __str__(self):
        return self.name


class TicketClass(db.Model):
    __tablename__ = "ticket_class"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    price = Column(Float, default=0)
    flight_id = Column(Integer, ForeignKey("flight.id"), nullable=False)

    flight = relationship("Flight", back_populates="ticket_classes")

    def __str__(self):
        return f"{self.name} - {self.flight.name if self.flight else ''}"


class Seat(db.Model):
    __tablename__ = "seat"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seat_number = Column(String(10), nullable=False)
    seat_type = Column(String(50), nullable=False)  # Phân loại: Thương gia / Phổ thông
    is_booked = Column(Boolean, default=False)
    flight_id = Column(Integer, ForeignKey("flight.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    flight = relationship("Flight", back_populates="seats")
    user = relationship("User", back_populates="seats")

    def __str__(self):
        return f"{self.seat_number} ({self.flight.name if self.flight else ''})"


# -------------------------------------------------------------
# 3. NẠP DỮ LIỆU MẪU KHI CHẠY FILE
# -------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():

        db.create_all()

        # Nạp đủ 10 sân bay với id là các chữ cái đầu
        airports_data = [
            {"id": "TST", "city": "Sài Gòn", "name": "Tân Sơn Nhất"},
            {"id": "NB", "city": "Hà Nội", "name": "Nội Bài"},
            {"id": "DN", "city": "Đà Nẵng", "name": "Đà Nẵng"},
            {"id": "CR", "city": "Khánh Hòa", "name": "Cam Ranh"},
            {"id": "PQ", "city": "An Giang", "name": "Phú Quốc"},
            {"id": "CB", "city": "Hải Phòng", "name": "Cát Bi"},
            {"id": "PB", "city": "Huế", "name": "Phú Bài"},
            {"id": "V", "city": "Nghệ An", "name": "Vinh"},
            {"id": "CT", "city": "Cần Thơ", "name": "Cần Thơ"},
            {"id": "LK", "city": "Lâm Đồng", "name": "Liên Khương"},
        ]

        airport_map = {}
        for a in airports_data:
            ap = Airport(id=a["id"], city=a["city"], name=a["name"])
            db.session.add(ap)
            airport_map[a["city"]] = ap
        db.session.flush()

        Ticket = [
            {
                "id": 1,
                "name": "VietJet Air",
                "price": "1650000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg",
                "From": "Sài Gòn",
                "To": "Hà Nội",
                "DepartureDate": "2026-11-22",
                "Departure": "20:00",
                "Arrival": "22:00",
            },
            {
                "id": 2,
                "name": "VietNam Airlines",
                "price": "1950000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images.jpg",
                "From": "Sài Gòn",
                "To": "Hà Nội",
                "DepartureDate": "2026-11-23",
                "Departure": "08:00",
                "Arrival": "10:00",
            },
            {
                "id": 3,
                "name": "Jetstar",
                "price": "1250000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_3.jpg",
                "From": "Sài Gòn",
                "To": "Đà Nẵng",
                "DepartureDate": "2026-11-23",
                "Departure": "09:30",
                "Arrival": "11:00",
            },
            {
                "id": 4,
                "name": "Bamboo",
                "price": "1600000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_1.jpg",
                "From": "Hà Nội",
                "To": "Khánh Hòa",
                "DepartureDate": "2026-11-23",
                "Departure": "13:00",
                "Arrival": "15:00",
            },
            {
                "id": 5,
                "name": "VietJet Air",
                "price": "950000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg",
                "From": "Sài Gòn",
                "To": "An Giang",
                "DepartureDate": "2026-11-24",
                "Departure": "07:00",
                "Arrival": "08:00",
            },
            {
                "id": 6,
                "name": "VietNam Airlines",
                "price": "850000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images.jpg",
                "From": "Đà Nẵng",
                "To": "Huế",
                "DepartureDate": "2026-11-24",
                "Departure": "10:00",
                "Arrival": "10:30",
            },
            {
                "id": 7,
                "name": "Bamboo",
                "price": "1850000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_1.jpg",
                "From": "Sài Gòn",
                "To": "Hải Phòng",
                "DepartureDate": "2026-11-24",
                "Departure": "14:00",
                "Arrival": "16:00",
            },
            {
                "id": 8,
                "name": "Jetstar",
                "price": "1550000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_3.jpg",
                "From": "Sài Gòn",
                "To": "Nghệ An",
                "DepartureDate": "2026-11-25",
                "Departure": "07:00",
                "Arrival": "09:00",
            },
            {
                "id": 9,
                "name": "VietNam Airlines",
                "price": "1400000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images.jpg",
                "From": "Hà Nội",
                "To": "Huế",
                "DepartureDate": "2026-11-25",
                "Departure": "16:00",
                "Arrival": "17:30",
            },
            {
                "id": 10,
                "name": "VietJet Air",
                "price": "1550000",
                "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg",
                "From": "Khánh Hòa",
                "To": "Hải Phòng",
                "DepartureDate": "2026-11-26",
                "Departure": "11:00",
                "Arrival": "13:00",
            },
        ]

        for t in Ticket:
            c = Flight(
                name=t["name"],
                price=float(t["price"]),
                image=t["image"],
                from_city=t["From"],
                to_city=t["To"],
                from_airport=airport_map.get(t["From"]),
                to_airport=airport_map.get(t["To"]),
                transit_1=t.get("Transit1"),
                transit_2=t.get("Transit2"),
                departure_date=datetime.strptime(
                    t["DepartureDate"], "%Y-%m-%d"
                ).date(),
                departure=datetime.strptime(t["Departure"], "%H:%M").time(),
                arrival=datetime.strptime(t["Arrival"], "%H:%M").time(),
            )

            c.ticket_classes = [
                TicketClass(
                    name="Thương gia", price=float(t["price"]) * 1.30
                ),
                TicketClass(
                    name="Phổ thông đặc biệt", price=float(t["price"]) * 1.10
                ),
                TicketClass(name="Phổ thông", price=float(t["price"])),
            ]

            # Tạo 10 ghế Thương gia (E1 -> E10) và 20 ghế Phổ thông / Phổ thông đặc biệt (F1 -> F20)
            business_seats = [
                Seat(seat_number=f"E{i}", seat_type="Thương gia", is_booked=False)
                for i in range(1, 11)
            ]
            economy_seats = [
                Seat(seat_number=f"F{i}", seat_type="Phổ thông", is_booked=False)
                for i in range(1, 21)
            ]
            c.seats = business_seats + economy_seats

            db.session.add(c)

        db.session.commit()
