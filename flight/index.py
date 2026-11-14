from datetime import datetime
from flask import redirect, render_template, request
from flask_login import login_user, logout_user, current_user

# 1. Thêm admin vào dòng import này
from flight import app, db, dao, login, admin
from flight.models import Flight, TicketClass, User, UserRoleEnum


@app.route("/")
def index():
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


# 2. Chỉ giữ lại 1 hàm /login duy nhất (xóa hàm login_process bị trùng ở dưới)
@app.route("/login", methods=["GET", "POST"])
def login_view():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Lưu ý: kiểm tra trong dao.py hàm xác thực tên là check_login hay authorize để gọi cho đúng
        user = dao.check_login(username=username, password=password)
        if user:
            login_user(user)

            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)

            if user.user_role == UserRoleEnum.ADMIN:
                return redirect("/admin")
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

        if password == confirm:
            res = dao.add_user(name=name, username=username, password=password, avatar=avatar)
            if res:
                return redirect("/login")
            else:
                msg = "Tên đăng nhập đã tồn tại hoặc có lỗi xảy ra!"
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
    return render_template("Search.html")


@app.route("/chon-hang-ve", methods=["POST"])
def chon_hang_ve():
    flight_id = request.form.get("flight_id")
    ticket_class_id = request.form.get("ticket_class_id")

    flight = Flight.query.get_or_404(flight_id)
    ticket_class = TicketClass.query.filter_by(
        id=ticket_class_id, flight_id=flight_id
    ).first_or_404()

    return render_template("booking.html", flight=flight, ticket_class=ticket_class)


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


if __name__ == "__main__":
    app.run(debug=True)