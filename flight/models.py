import enum
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import Column, Date, Enum, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship

import flight
from flight import app, db


# -------------------------------------------------------------
# 1. ENUM & MODEL USER
# -------------------------------------------------------------
class UserRoleEnum(enum.Enum):
    ADMIN = 1
    USER = 2


class User(db.Model, UserMixin):
    __tablename__ = "user"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    avatar = Column(String(200))
    user_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.USER)

    def __str__(self):
        return self.name


# -------------------------------------------------------------
# 2. MODEL FLIGHT & TICKET CLASS
# -------------------------------------------------------------
class Flight(db.Model):
    __tablename__ = "flight"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    price = Column(Float, default=0)
    image = Column(String(100))
    from_city = Column(String(50), nullable=False)
    to_city = Column(String(50), nullable=False)
    departure_date = Column(Date, nullable=False)
    departure = Column(Time, nullable=False)
    arrival = Column(Time, nullable=False)

    ticket_classes = relationship(
        "TicketClass", back_populates="flight", cascade="all, delete-orphan"
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


# -------------------------------------------------------------
# 3. NẠP DỮ LIỆU MẪU KHI CHẠY FILE
# -------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():

        db.create_all()

        import hashlib
        # u = User(name='admin', username='admin', user_role=UserRoleEnum.ADMIN, password=str(hashlib.md5('12345'.encode('utf-8')).hexdigest()))
        # db.session.add(u)

        # Ticket = [
        #     {
        #         "id": 1,
        #         "name": "VietJet Air",
        #         "price": "100000",
        #         "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg",
        #         "From": "SG",
        #         "To": "HN",
        #         "DepartureDate": "2026-11-17",
        #         "Departure": "08:00",
        #         "Arrival": "10:00",
        #     },
        #     {
        #         "id": 2,
        #         "name": "VietNam Airlines",
        #         "price": "100000",
        #         "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images.jpg",
        #         "From": "SG",
        #         "To": "HN",
        #         "DepartureDate": "2026-11-15",
        #         "Departure": "08:00",
        #         "Arrival": "10:00",
        #     },
        #     {
        #         "id": 3,
        #         "name": "jetstar",
        #         "price": "120000",
        #         "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_3.jpg",
        #         "From": "SG",
        #         "To": "HN",
        #         "DepartureDate": "2026-11-15",
        #         "Departure": "08:00",
        #         "Arrival": "10:00",
        #     },
        #     {
        #         "id": 4,
        #         "name": "Bamboo",
        #         "price": "130000",
        #         "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_1.jpg",
        #         "From": "SG",
        #         "To": "HN",
        #         "DepartureDate": "2026-11-16",
        #         "Departure": "08:00",
        #         "Arrival": "10:00",
        #     },
        # ]
        #
        # for t in Ticket:
        #     c = Flight(
        #         name=t["name"],
        #         price=float(t["price"]),
        #         image=t["image"],
        #         from_city=t["From"],
        #         to_city=t["To"],
        #         departure_date=datetime.strptime(
        #             t["DepartureDate"], "%Y-%m-%d"
        #         ).date(),
        #         departure=datetime.strptime(t["Departure"], "%H:%M").time(),
        #         arrival=datetime.strptime(t["Arrival"], "%H:%M").time(),
        #     )
        #
        #     c.ticket_classes = [
        #         TicketClass(
        #             name="Thương gia", price=float(t["price"]) * 1.10
        #         ),
        #         TicketClass(
        #             name="Phổ thông đặc biệt", price=float(t["price"]) * 1.05
        #         ),
        #         TicketClass(name="Phổ thông", price=float(t["price"])),
        #     ]
        #     db.session.add(c)
        #
        # db.session.commit()