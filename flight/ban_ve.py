"""UC02 - Nhân viên bán vé tại quầy.

/staff/ban-ve                 : tra cứu chuyến bay còn mở bán (trước giờ bay 4h)
/staff/ban-ve/<flight_id>     : chọn hạng vé, ghế, nhập thông tin hành khách, thu tiền
/staff/ve/<invoice_id>        : xuất vé cho khách
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from flight import db
from flight import dao_nhan_vien as dao
from flight.models import Flight
from flight.models_nhan_vien import Invoice
from flight.staff_utils import staff_required

ban_ve_bp = Blueprint("ban_ve", __name__, url_prefix="/staff")


@ban_ve_bp.route("/ban-ve")
@staff_required
def search_view():
    args = {
        "from_city": request.args.get("from_city", ""),
        "to_city": request.args.get("to_city", ""),
        "departure_date": request.args.get("departure_date", ""),
        "name": request.args.get("name", ""),
    }
    rows, closed_count = dao.search_sellable_flights(**args)
    return render_template(
        "staff/ban_ve.html", rows=rows, closed_count=closed_count,
        cities=sorted({a.city for a in dao.load_airports()}), args=args,
        sell_hours=dao.get_rule("sell_before_hours"),
    )


def _render_seats(flight, errors=None, selected=None, prefill=None):
    return render_template(
        "staff/ban_ve_chon_ghe.html", flight=flight, seat_map=dao.get_seat_map(flight),
        errors=errors or [], selected=selected or [], prefill=prefill or {},
    )


@ban_ve_bp.route("/ban-ve/<int:flight_id>", methods=["GET", "POST"])
@staff_required
def sell_view(flight_id):
    flight = db.session.get(Flight, flight_id)
    if flight is None:
        abort(404)

    # Ngoại lệ 2.1: chuyến bay trước 4h không còn mở bán thì đóng bán vé
    if not dao.is_open_for_sale(flight):
        flash(f"Chuyến bay {flight.name} đã đóng bán "
              f"(chỉ bán trước giờ khởi hành {dao.get_rule('sell_before_hours')} giờ).", "warning")
        return redirect(url_for("ban_ve.search_view"))

    if request.method == "GET":
        return _render_seats(flight)

    # POST: nhân viên xác nhận thu tiền và xuất vé
    selected, passengers, prefill = [], {}, {}
    for raw in request.form.getlist("seat_id"):
        if raw.isdigit():
            sid = int(raw)
            selected.append(sid)
            passengers[sid] = {
                "name": request.form.get(f"name_{sid}", ""),
                "id_number": request.form.get(f"id_number_{sid}", ""),
                "phone": request.form.get(f"phone_{sid}", ""),
            }
            prefill[str(sid)] = passengers[sid]

    try:
        invoice = dao.create_sale(current_user.id, flight_id, passengers)
    except dao.SaleError as e:
        return _render_seats(flight, errors=e.errors, selected=selected, prefill=prefill)

    flash("Bán vé thành công.", "success")
    return redirect(url_for("ban_ve.ticket_view", invoice_id=invoice.id))


@ban_ve_bp.route("/ve/<int:invoice_id>")
@staff_required
def ticket_view(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        abort(404)
    return render_template("staff/ve.html", invoice=invoice)
