function kiemTraDangNhap(event, isAuthenticated, loginUrl) {
    if (!isAuthenticated) {
        event.preventDefault(); // Chặn không cho submit form
        if (confirm("Bạn cần đăng nhập để chọn hạng vé! Chuyển đến trang đăng nhập ngay?")) {
            window.location.href = loginUrl;
        }
    }
}