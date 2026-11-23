"""Nhân viên lập lịch chuyến bay: /staff/lap-lich"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from flight import dao_nhan_vien as dao
from flight.staff_utils import staff_required

lap_lich_bp = Blueprint("lap_lich", __name__, url_prefix="/staff")


def _render(form=None, errors=None):
    return render_template(
        "staff/lap_lich.html", airports=dao.load_airports(),
        form=form, errors=errors or [], recent=dao.recent_flights(),
        rules={k: dao.get_rule(k) for k in dao.DEFAULT_RULES},
    )


@lap_lich_bp.route("/lap-lich", methods=["GET", "POST"])
@staff_required
def schedule_view():
    if request.method == "GET":
        return _render()

    data, errors = dao.parse_and_validate_schedule(request.form)
    if errors:
        # Vi phạm quy định: giữ nguyên dữ liệu đã nhập, báo lỗi để nhân viên sửa
        return _render(form=request.form, errors=errors)

    try:
        flight = dao.create_schedule(data)
    except dao.SaleError as e:
        return _render(form=request.form, errors=e.errors)

    flash(f"Đã lập lịch chuyến bay {flight.name} ({flight.from_city} - {flight.to_city}), "
          f"đã tạo {len(flight.seats)} ghế.", "success")
    return redirect(url_for("lap_lich.schedule_view"))
