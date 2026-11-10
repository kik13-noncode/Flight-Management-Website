from sqlalchemy import Column, String, Float, Integer, Time
from datetime import datetime
import flight
from flight import db, app


class Flight(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    price = Column(Float, default=0)
    image = Column(String(100))
    from_city = Column(String(50), nullable=False)
    to_city = Column(String(50), nullable=False)
    departure = Column(Time, nullable=False)
    arrival = Column(Time, nullable=False)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        Ticket = [{
            "id": 1,
            "name": "VietJet Air",
            "price": "100000",
            "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images_2.jpg",
            "From": "SG",
            "To": "HN",
            "Departure": "08:00",
            "Arrival": "10:00"

        }, {
            "id": 2,
            "name": "VietNam Airlines",
            "price": "100000",
            "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078630/images.jpg",
            "From": "SG",
            "To": "HN",
            "Departure": "08:00",
            "Arrival": "10:00"
        }, {
            "id": 3,
            "name": "jetstar",
            "price": "120000",
            "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_3.jpg",
            "From": "SG",
            "To": "HN",
            "Departure": "08:00",
            "Arrival": "10:00"
        }, {
            "id": 4,
            "name": "Bamboo",
            "price": "130000",
            "image": "https://res.cloudinary.com/i3c1j8ys/image/upload/v1794078629/images_1.jpg",
            "From": "SG",
            "To": "HN",
            "Departure": "08:00",
            "Arrival": "10:00"
        }]

        for t in Ticket:
            c = Flight(
                name=t["name"],
                price=t["price"],
                image=t["image"],
                from_city=t["From"],
                to_city=t["To"],
                departure=datetime.strptime(t["Departure"], "%H:%M").time(),
                arrival=datetime.strptime(t["Arrival"], "%H:%M").time()
            )
            db.session.add(c)

        db.session.commit()
