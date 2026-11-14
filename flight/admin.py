from dataclasses import replace

from flask import redirect
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, logout_user
from markupsafe import Markup
from wtforms.fields.numeric import FloatField

from flight import app, db
from flight.models import Flight, TicketClass, UserRoleEnum

admin = Admin(app=app, name=" OU Airlines Admin")



class AuthenticatedView(ModelView):
    def is_accessible(self) -> bool:
        return (
            current_user.is_authenticated
            and current_user.user_role == UserRoleEnum.ADMIN
        )


class FlightView(AuthenticatedView):
    column_list = [
        "id",
        "name",
        "price",
        "from_city",
        "to_city",
        "departure_date",
        "departure",
        "arrival",
    ]

    column_labels = {
        "id":"Mã",
        "name":"Tên chuyến bay",
        "price":"Giá vé",
        "from_city":"Điểm đi",
        "to_city": "Điểm đến",
        "departure_date": "Ngày khởi hành",
        "departure": "Giờ đi",
        "arrival": "Giờ đến",
    }


    column_searchable_list = ["name", "from_city", "to_city"]
    can_export = True
    edit_modal = True
    column_editable_list = ["name", "price"]
    column_filters = ["id", "name", "price", "from_city", "to_city", "departure_date"]

    form_overrides = {"price": FloatField}
    form_excluded_columns = ['image']

class BaseAuthenticatedView(BaseView):
    def is_accessible(self) -> bool:
        return (
            current_user.is_authenticated
            and current_user.user_role == UserRoleEnum.ADMIN
        )


class StatsView(BaseAuthenticatedView):
    @expose("/")
    def index(self):
        return self.render("admin/stats.html")


class LogoutView(BaseView):
    @expose("/")
    def index(self):
        logout_user()
        return redirect("/admin")

    def is_accessible(self) -> bool:
        return current_user.is_authenticated

def format_price(view, context, model, name):
    if model.price is None:
        return ""
    return Markup(f"{model.price:.0f}", replace(",", "."))

column_formatters = {"price": format_price}

admin.add_view(FlightView(Flight, db.session, name="Chuyến bay"))
admin.add_view(AuthenticatedView(TicketClass, db.session, name="Hạng vé"))
admin.add_view(StatsView(name="Thống kê"))
admin.add_view(LogoutView(name="Đăng xuất"))