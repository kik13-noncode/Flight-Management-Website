from flask import flash, redirect, request
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from wtforms import ValidationError
from flask_login import current_user, logout_user
from markupsafe import Markup
from wtforms.fields.numeric import FloatField

from flight import app, db
from flight import dao_nhan_vien as dao
from flight.models import Airport, Flight, Seat, TicketClass, UserRoleEnum
from flight.models_nhan_vien import FareClass, IntermediateStop

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
        return redirect("/")

    def is_accessible(self) -> bool:
        return current_user.is_authenticated

class RegulationView(BaseAuthenticatedView):
    """Trang gom các quy định dạng số: bay, sân bay trung gian, thời gian bán/đặt vé, số sân bay."""

    @expose("/", methods=["GET", "POST"])
    def index(self):
        errors, values = [], dao.get_all_rules()      #lấy các quy định mặc định từ csdl, báo lỗi nếu rỗng
        if request.method == "POST":
            clean, errors = dao.validate_rules(request.form)
            values.update({k: request.form.get(k, v) for k, v in values.items()})  # cập nhật value từ người dung nhập,
                                                # nếu lỗi giữ nguyên k nếu không có giá trị thì giữ giá trị cũ v
            if not errors:
                try:
                    dao.save_rules(clean)
                    flash("Đã cập nhật quy định. Các chức năng đặt vé, bán vé, lập lịch áp dụng ngay.", "success")
                    return redirect(request.url)
                except dao.SaleError as e:
                    errors = e.errors
        return self.render(
            "admin/regulations.html", values=values, errors=errors,
            labels={k: v[1] for k, v in dao.DEFAULT_RULES.items()}, #lấy phần tử thứ 2 trong quy định mặc định làm label tiếng việt cho input
            airport_count=Airport.query.count(),
        )


class AirportView(AuthenticatedView):
    """Quản lý sân bay; tổng số sân bay bị giới hạn bởi quy định max_airports."""
    column_list = ["id", "name", "city"]
    column_labels = {"id": "Mã sân bay", "name": "Tên sân bay", "city": "Tỉnh/Thành"}
    column_searchable_list = ["id", "name", "city"]
    form_columns = ["id", "name", "city"]
    can_export = True

    def on_form_prefill(self, form, id):
        form.id.render_kw = {"readonly": True}   # không đổi mã khi sửa (khóa chính, được tham chiếu)

    def on_model_change(self, form, model, is_created):
        if is_created:
            limit = dao.get_rule("max_airports")
            # loại chính bản ghi đang thêm (đã nằm trong session) khỏi phép đếm
            if Airport.query.filter(Airport.id != model.id).count() >= limit:
                raise ValidationError(f"Đã đạt số sân bay tối đa theo quy định ({limit}). "
                                      "Hãy tăng quy định trước khi thêm sân bay.")

    def delete_model(self, model):
        used = (Flight.query.filter((Flight.from_airport_id == model.id)
                                    | (Flight.to_airport_id == model.id)).count()
                + IntermediateStop.query.filter_by(airport_id=model.id).count())
        if used:
            flash(f"Không thể xóa sân bay {model.name}: đang được dùng trong {used} chuyến bay/điểm dừng.", "error")
            return False
        return super().delete_model(model)


class FareClassView(AuthenticatedView):
    """Quản lý số lượng hạng vé và bảng đơn giá vé mặc định."""
    column_list = ["rank", "name", "prefix", "default_price", "is_active"]
    column_labels = {"rank": "Thứ hạng", "name": "Tên hạng vé", "prefix": "Tiền tố ghế",
                     "default_price": "Đơn giá mặc định (VNĐ)", "is_active": "Đang áp dụng"}
    column_default_sort = "rank"
    column_editable_list = ["default_price", "is_active"]
    form_columns = ["name", "prefix", "rank", "default_price", "is_active"]
    form_overrides = {"default_price": FloatField}

    def on_form_prefill(self, form, id):
        # Tên và tiền tố gắn với ghế đã tạo (Seat.seat_type), không cho đổi khi sửa
        form.name.render_kw = {"readonly": True}
        form.prefix.render_kw = {"readonly": True}

    def on_model_change(self, form, model, is_created):
        if model.default_price is None or model.default_price < 0:
            raise ValidationError("Đơn giá phải là số không âm.")
        if model.rank is None or model.rank < 1:
            raise ValidationError("Thứ hạng phải >= 1.")
        model.name = (model.name or "").strip()
        model.prefix = (model.prefix or "").strip().upper()
        if not model.name or not model.prefix:
            raise ValidationError("Tên hạng vé và tiền tố ghế không được để trống.")

    def delete_model(self, model):
        used = Seat.query.filter_by(seat_type=model.name).count()
        if used:
            flash(f"Không thể xóa hạng {model.name}: đã có {used} ghế thuộc hạng này. "
                  "Hãy bỏ chọn \"Đang áp dụng\" để ngừng dùng cho lịch bay mới.", "error")
            return False
        return super().delete_model(model)


def format_price(view, context, model, name):
    if model.price is None:
        return ""
    return Markup(f"{model.price:.0f}". replace(",", "."))



admin.add_view(FlightView(Flight, db.session, name="Chuyến bay"))
admin.add_view(AuthenticatedView(TicketClass, db.session, name="Hạng vé"))
admin.add_view(AirportView(Airport, db.session, name="Sân bay"))
admin.add_view(FareClassView(FareClass, db.session, name="Hạng vé & đơn giá"))
admin.add_view(RegulationView(name="Quy định", endpoint="regulations"))
admin.add_view(StatsView(name="Thống kê"))
admin.add_view(LogoutView(name="Đăng xuất"))