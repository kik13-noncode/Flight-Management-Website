from flask import redirect, render_template, request, jsonify
from flask_login import login_user, logout_user, current_user
from flight import app, dao, login
from flight.models import Flight, TicketClass, UserRoleEnum, Seat
from flight.zalopay import create_zalopay_payment, query_zalopay_order
from flight.ban_ve import ban_ve_bp
from flight.lap_lich import lap_lich_bp
from flight import dao_nhan_vien
import flight.admin  # noqa: F401  (đăng ký trang /admin, gồm cả trang thay đổi quy định)

# Khu vực nhân viên: bán vé, lập lịch chuyến bay
app.register_blueprint(ban_ve_bp)
app.register_blueprint(lap_lich_bp)


@app.route("/")
def index():
    if current_user.is_authenticated:
        logout_user()
    from_city = request.args.get("from_city")
    to_city = request.args.get("to_city")
    departure_date = request.args.get("departure_date")

    tickets = dao.load_flight(
        from_city=from_city,
        to_city=to_city,
        departure_date=departure_date,
    )

    if from_city or to_city or departure_date:
        return render_template("show.html", Ticket=tickets)

    return render_template("index.html", Ticket=tickets)


@app.route("/login", methods=["GET", "POST"])
def login_view():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = dao.check_login(username=username, password=password)
        if user:
            login_user(user)

            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)

            if user.user_role == UserRoleEnum.ADMIN:
                return redirect("/admin")
            if user.user_role == UserRoleEnum.EMPLOYEE:
                return redirect("/staff/ban-ve")
            return redirect("/")
        else:
            msg = "Tên đăng nhập hoặc mật khẩu không chính xác!"

    return render_template("login.html", msg=msg)


@app.route("/register", methods=["GET", "POST"])
def register_view():
    msg = ""
    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        avatar = request.files.get("avatar")
        cccd = request.form.get("cccd")
        phone = request.form.get("phone")
        if password == confirm:
            err = dao.add_user(name=name, username=username, password=password, avatar=avatar, cccd=cccd, phone=phone)
            if not err:
                return redirect("/login")
            else:
                if "Duplicate entry" in err:
                    msg = "Tên đăng nhập hoặc CCCD đã tồn tại trong hệ thống!"
                else:
                    msg = f"Đăng ký không thành công! Chi tiết lỗi: {err}"
        else:
            msg = "Mật khẩu xác nhận không trùng khớp!"

    return render_template("register.html", msg=msg)


@app.route("/logout")
def logout_view():
    logout_user()
    return redirect("/login")


@app.route("/trangchu")
def trangchu():
    return render_template("index.html")


@app.route("/search")
def search():
    return render_template("Search.html", cities=dao.load_cities())


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


@app.route("/chon-hang-ve", methods=["POST"])
def chon_hang_ve():
    if not current_user.is_authenticated:
        return redirect("/login")

    flight_id = request.form.get("flight_id")
    ticket_class_id = request.form.get("ticket_class_id")

    flight = Flight.query.get_or_404(flight_id)
    # Quy định: chỉ đặt vé online trước giờ khởi hành book_before_hours giờ (admin thay đổi được)
    if not dao_nhan_vien.is_open_for_booking(flight):
        return (f"Chuyến bay đã đóng đặt vé online "
                f"(chỉ đặt trước giờ khởi hành {dao_nhan_vien.get_rule('book_before_hours')} giờ).")
    ticket_class = TicketClass.query.filter_by(id=ticket_class_id, flight_id=flight_id).first_or_404()
    seat = dao.find_seat(flight.id, ticket_class.name)

    return render_template("booking.html", flight=flight, ticket_class=ticket_class, seat=seat)


@app.route("/xac-nhan-dat-ve", methods=["POST"])
def xac_nhan_dat_ve():
    if not current_user.is_authenticated:
        return redirect("/login")

    seat_id = request.form.get("seat_id")
    flight_id = request.form.get("flight_id")
    ticket_class_id = request.form.get("ticket_class_id")

    seat = Seat.query.get_or_404(seat_id)
    flight = Flight.query.get_or_404(flight_id)
    ticket_class = TicketClass.query.get_or_404(ticket_class_id)
    if not dao_nhan_vien.is_open_for_booking(flight):
        return (f"Chuyến bay đã đóng đặt vé online "
                f"(chỉ đặt trước giờ khởi hành {dao_nhan_vien.get_rule('book_before_hours')} giờ).")

    return render_template(
        "pay.html",
        flight=flight,
        ticket_class=ticket_class,
        seat=seat,
        msg="Xác nhận thông tin thành công! Vui lòng tiến hành thanh toán."
    )


@app.route("/thanh-toan", methods=["POST"])
def thanh_toan():
    if not current_user.is_authenticated:
        return redirect("/login")

    amount = request.form.get("amount")
    seat_id = request.form.get("seat_id")
    flight_id = request.form.get("flight_id")
    ticket_class_id = request.form.get("ticket_class_id")

    res = create_zalopay_payment(
        amount=amount,
        seat_id=seat_id,
        app_user=current_user.username
    )

    if res.get("return_code") == 1:
        seat = Seat.query.get_or_404(seat_id)
        flight = Flight.query.get_or_404(flight_id)
        ticket_class = TicketClass.query.get_or_404(ticket_class_id)

        return render_template(
            "pay.html",
            flight=flight,
            ticket_class=ticket_class,
            seat=seat,
            qr_code=res.get("qr_code"),
            app_trans_id=res.get("app_trans_id"),
            msg="Đã tạo mã QR ZaloPay! Vui lòng mở app ZaloPay Sandbox để quét mã."
        )

    return f"Lỗi tạo thanh toán ZaloPay: {res.get('return_message')} - {res.get('sub_return_message')}"


@app.route("/kiem-tra-thanh-toan/<app_trans_id>")
def kiem_tra_thanh_toan(app_trans_id):
    if not current_user.is_authenticated:
        return jsonify({"paid": False})

    seat_id = request.args.get("seat_id")
    res = query_zalopay_order(app_trans_id)

    if res.get("return_code") == 1:
        if seat_id:
            seat = Seat.query.get(seat_id)
            if seat and not seat.user_id:
                dao.user_booking(seat_id=seat_id, user_id=current_user.id)
        return jsonify({"paid": True})

    return jsonify({"paid": False})


@app.route("/ve-cua-toi")
def ve_cua_toi():
    if not current_user.is_authenticated:
        return redirect("/login")

    booked_seats = dao.get_user_tickets(current_user.id)
    return render_template("myTickets.html", booked_seats=booked_seats)


if __name__ == "__main__":
    app.run(debug=True)