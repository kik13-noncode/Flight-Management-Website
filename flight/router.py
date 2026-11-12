from flask import render_template, request
from datetime import datetime
from flight import app
from flight.models import Flight

@app.route("/search", methods=["GET"])
def search():
    from_city = request.args.get("from_city")
    to_city = request.args.get("to_city")
    departure_date = request.args.get("departure_date")
    return_date = request.args.get("return_date")

    # Tìm chuyến bay chiều đi
    flights = Flight.query.filter(
        Flight.from_city == from_city,
        Flight.to_city == to_city,
        Flight.departure_date == datetime.strptime(
            departure_date, "%Y-%m-%d"
        ).date()
    ).all()

    # Tìm chuyến bay chiều về nếu có ngày về
    return_flights = []

    if return_date:
        return_flights = Flight.query.filter(
            Flight.from_city == to_city,
            Flight.to_city == from_city,
            Flight.departure_date == datetime.strptime(
                return_date, "%Y-%m-%d"
            ).date()
        ).all()

    return render_template(
        "search.html",
        flights=flights,
        return_flights=return_flights
    )