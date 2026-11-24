"""Phân quyền cho khu vực nhân viên (/staff/...)."""
from functools import wraps

from flask import abort, redirect, request, url_for
from flask_login import current_user

from flight.models import UserRoleEnum


def is_staff(user):
    return user.is_authenticated and user.user_role in (UserRoleEnum.EMPLOYEE, UserRoleEnum.ADMIN)


def staff_required(view):
    """Chỉ cho nhân viên (hoặc admin) vào. Chưa đăng nhập thì chuyển sang trang đăng nhập."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login_view", next=request.full_path))
        if not is_staff(current_user):
            abort(403)
        return view(*args, **kwargs)

    return wrapper
