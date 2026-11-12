from datetime import datetime
from flask import redirect, render_template, request
from flask_login import login_user, logout_user, current_user

from flight import app, db, dao
# Import admin để Flask nhận diện và khởi tạo trang Admin (/admin)
import flight.admin
from flight.models import Flight, TicketClass, User, UserRoleEnum


@app.route("/")
def index():
    from_city = request.args.get("from_city")
    to_city = request.args.get("to_city")
    departure_date = request.args.get("departure_date")

    # Gọi DAO để query lọc từ MySQL Database
    tickets = dao.load_flight(
        from_city=from_city,
        to_city=to_city,
        departure_date=departure_date,
    )

    # Nếu có tìm kiếm thì trả về show.html, không thì index.html
    if from_city or to_city or departure_date:
        return render_template("show.html", Ticket=tickets)

    return render_template("index.html", Ticket=tickets)


@app.route("/login", methods=["GET", "POST"])
def login_view():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Gọi hàm kiểm tra đăng nhập từ dao
        user = dao.check_login(username=username, password=password)
        if user:
            login_user(user)
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
            # Gọi hàm add_user trong dao để xử lý lưu vào CSDL (hoặc upload Cloudinary)
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
    return redirect("/")


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

    # Lấy trực tiếp chuyến bay và hạng vé từ CSDL
    flight = Flight.query.get_or_404(flight_id)
    ticket_class = TicketClass.query.filter_by(
        id=ticket_class_id, flight_id=flight_id
    ).first_or_404()

    return render_template("booking.html", flight=flight, ticket_class=ticket_class)


if __name__ == "__main__":
    app.run(debug=True)