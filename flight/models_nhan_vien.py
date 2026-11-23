from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship

from flight import db
from flight import models  # noqa: F401  (đảm bảo các bảng gốc đã được đăng ký trước)


class IntermediateStop(db.Model):
    """Sân bay trung gian của một chuyến bay (kèm thời gian dừng, ghi chú)."""
    __tablename__ = "intermediate_stop"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flight_id = Column(Integer, ForeignKey("flight.id"), nullable=False)
    stop_order = Column(Integer, nullable=False, default=1)
    airport_id = Column(String(10), ForeignKey("airport.id"), nullable=False)
    stop_minutes = Column(Integer, nullable=False)
    note = Column(String(200))

    flight = relationship(
        "Flight",
        backref=backref("stops", cascade="all, delete-orphan",
                        order_by="IntermediateStop.stop_order"),
    )
    airport = relationship("Airport")


class Invoice(db.Model):
    """Hóa đơn bán vé tại quầy (1 hóa đơn có thể gồm nhiều vé)."""
    __tablename__ = "invoice"

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff_id = Column(Integer, ForeignKey("user.id"))
    channel = Column(String(10), nullable=False, default="COUNTER")
    status = Column(String(20), nullable=False, default="PAID")
    total = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)

    staff = relationship("User", foreign_keys=[staff_id])


class Ticket(db.Model):
    """Vé bán tại quầy: gắn với 1 ghế và thông tin hành khách."""
    __tablename__ = "ticket"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoice.id"), nullable=False)
    flight_id = Column(Integer, ForeignKey("flight.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("seat.id"), nullable=False, unique=True)
    passenger_name = Column(String(100), nullable=False)
    id_number = Column(String(20), nullable=False)   # CMND/CCCD
    phone = Column(String(15), nullable=False)
    price = Column(Float, default=0)

    invoice = relationship(
        "Invoice", backref=backref("tickets", cascade="all, delete-orphan")
    )
    flight = relationship("Flight")
    seat = relationship("Seat")


class Payment(db.Model):
    __tablename__ = "payment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoice.id"), nullable=False)
    method = Column(String(20), nullable=False, default="CASH")
    amount = Column(Float, default=0)
    status = Column(String(20), nullable=False, default="SUCCESS")
    paid_at = Column(DateTime, default=datetime.now)

    invoice = relationship(
        "Invoice", backref=backref("payments", cascade="all, delete-orphan")
    )


class Regulation(db.Model):
    """Quy định hệ thống (admin có thể thay đổi). Giá trị mặc định xem dao_nhan_vien.py."""
    __tablename__ = "regulation"

    rule_key = Column(String(50), primary_key=True)
    value = Column(String(50), nullable=False)
    description = Column(String(200))
