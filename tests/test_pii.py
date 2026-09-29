from app.pii import scrub_text

def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    out = scrub_text("CCCD 001202012345")
    assert "001202012345" not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    for card in ("4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"):
        out = scrub_text(f"Card {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport() -> None:
    out = scrub_text("Hộ chiếu C1234567")
    assert "C1234567" not in out
    assert "REDACTED_PASSPORT" in out


def test_scrub_vietnamese_address() -> None:
    for address in (
        "Tòa nhà số 12 Nguyễn Trãi, Quận 1",
        "Số 45 Lê Lợi, Phường Bến Nghệ, Quận 1",
        "Khu vực 7 Nguyễn Huệ, Thị xã Thủ Dầu Một",
    ):
        out = scrub_text(address)
        assert "REDACTED_VN_ADDRESS" in out, out


def test_numeric_log_fields_are_not_mangled() -> None:
    line = (
        "latency_ms=1562 ttft_ms=50 tokens_in=24 tokens_out=129 "
        "cost_usd=0.002076 quality_score=0.8"
    )
    assert scrub_text(line) == line


def test_operational_log_line_is_not_mangled() -> None:
    line = (
        "req-26af01a9 request_received service=api level=info "
        "user_id_hash=2a2006df8771 session_id=session-01 feature=qa"
    )
    assert scrub_text(line) == line
