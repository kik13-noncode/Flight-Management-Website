function kiemTraDangNhap(event, isAuthenticated, loginUrl) {
    if (!isAuthenticated) {
        event.preventDefault();
        if (confirm("Bạn cần đăng nhập để chọn hạng vé! Chuyển đến trang đăng nhập ngay?")) {
            window.location.href = loginUrl;
        }
    } else {
        event.preventDefault(); // Tạm dừng 1.2s để hiện thông báo tìm ghế
        const form = event.target;

        // Đóng modal chọn hạng vé đang mở
        const currentModalEl = form.closest('.modal');
        if (currentModalEl) {
            const currentModal = bootstrap.Modal.getInstance(currentModalEl);
            if (currentModal) currentModal.hide();
        }

        // Hiện modal loading tìm ghế
        const loadingModalEl = document.getElementById('loadingSeatModal');
        if (loadingModalEl) {
            const loadingModal = new bootstrap.Modal(loadingModalEl);
            loadingModal.show();
        }

        setTimeout(() => {
            form.submit();
        }, 1200);
    }
}

function xuLyThanhToanZaloPay(qrCode, appTransId, seatId) {
    new QRCode(document.getElementById("qrcode"), {
        text: qrCode,
        width: 220,
        height: 220
    });

    const checkInterval = setInterval(() => {
        fetch(`/kiem-tra-thanh-toan/${appTransId}?seat_id=${seatId}`)
            .then(res => res.json())
            .then(data => {
                if (data.paid) {
                    clearInterval(checkInterval);

                    const topAlert = document.getElementById("top-alert");
                    if (topAlert) topAlert.style.display = "none";

                    const paymentBox = document.getElementById("payment-box");
                    paymentBox.className = "text-center border rounded p-4 bg-white";
                    paymentBox.innerHTML = `
                        <h5 class="text-success fw-bold mb-3">Thanh toán thành công!</h5>
                        <a href="/" class="btn btn-success w-100">Xác nhận</a>
                    `;
                }
            });
    }, 2000);
}