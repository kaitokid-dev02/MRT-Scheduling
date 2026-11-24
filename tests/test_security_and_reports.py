import base64

import pytest

from app import create_app
from app.qr import qr_data_uri
from app.security import is_safe_redirect

# ---- auth -------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/reports", "/reports/export"])
def test_reports_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_clear_logs_requires_login(client):
    assert client.post("/reports/clear").status_code == 302


def test_login_success_and_logout(client, app):
    bad = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401

    ok = client.post(
        "/login",
        data={"username": "admin", "password": app.config["ADMIN_PASSWORD"], "next": "/reports/export"},
    )
    assert ok.status_code == 302 and ok.headers["Location"].endswith("/reports/export")
    assert client.get("/reports").status_code == 200

    client.post("/logout")
    assert client.get("/reports").status_code == 302


@pytest.mark.parametrize(
    "target, safe",
    [("/reports", True), ("/reports?x=1", True), ("//evil.com", False), ("https://evil.com", False),
     ("/\\evil.com", False), ("javascript:alert(1)", False), ("", False), (None, False)],
)  # fmt: skip
def test_open_redirect_guard(target, safe):
    assert is_safe_redirect(target) is safe


def test_login_redirect_ignores_offsite_next(client, app):
    response = client.post(
        "/login",
        data={"username": "admin", "password": app.config["ADMIN_PASSWORD"], "next": "https://evil.com"},
    )
    assert response.headers["Location"].endswith("/reports")


def test_login_is_throttled_after_repeated_failures(client):
    for _ in range(5):
        assert client.post("/login", data={"username": "admin", "password": "x"}).status_code == 401
    assert client.post("/login", data={"username": "admin", "password": "x"}).status_code == 429


# ---- reports ---------------------------------------------------------------


def test_reports_page_empty_and_with_data(admin, issue_ticket):
    empty = admin.get("/reports")
    assert empty.status_code == 200 and b"No transactions" in empty.data

    issue_ticket("Reg One", "Regular")
    issue_ticket("Pri One", "Priority")
    page = admin.get("/reports")
    assert page.status_code == 200
    assert b"Reg One" in page.data and b"Peak hour" in page.data
    assert b"1 priority" in page.data  # lane stats are no longer always zero


def test_csv_export_neutralises_formulas(admin, issue_ticket):
    issue_ticket("=HYPERLINK(\"http://evil\")", "Regular")
    response = admin.get("/reports/export")
    assert response.mimetype == "text/csv"
    text = response.get_data(as_text=True)
    assert "'=HYPERLINK" in text
    assert text.splitlines()[0].startswith("timestamp_iso,name,type")


def test_clear_logs(admin, issue_ticket):
    issue_ticket()
    assert admin.post("/reports/clear").get_json() == {"ok": True, "removed": 1}
    assert b"No transactions" in admin.get("/reports").data


# ---- tickets ---------------------------------------------------------------


def test_ticket_links_are_signed(client, issue_ticket):
    assert client.get("/ticket/1").status_code == 404  # raw sequential ids no longer work
    assert client.get("/ticket/not-a-valid-token").status_code == 404
    url = issue_ticket()["ticket_url"]
    assert client.get(url).status_code == 200
    assert client.get(url[:-3] + "xyz").status_code == 404  # tampered signature


def test_ticket_page_embeds_qr_for_signed_ticket_url(client, issue_ticket, monkeypatch):
    url = issue_ticket()["ticket_url"]
    generated_for = []

    def fake_qr_data_uri(value):
        generated_for.append(value)
        return "data:image/png;base64,iVBORw0KGgo="

    monkeypatch.setattr("app.blueprints.main.qr_data_uri", fake_qr_data_uri)
    response = client.get(url)

    assert response.status_code == 200
    assert generated_for == [f"http://localhost{url}"]
    assert b'data:image/png;base64,iVBORw0KGgo=' in response.data


def test_qr_data_uri_contains_png():
    data_uri = qr_data_uri("https://example.test/ticket/signed-token")
    prefix, encoded = data_uri.split(",", maxsplit=1)

    assert prefix == "data:image/png;base64"
    assert base64.b64decode(encoded).startswith(b"\x89PNG\r\n\x1a\n")


# ---- CSRF & headers --------------------------------------------------------


@pytest.fixture
def csrf_app(tmp_path):
    return create_app("testing", DATABASE=str(tmp_path / "csrf.db"), CSRF_ENABLED=True)


def test_csrf_blocks_posts_without_token(csrf_app):
    client = csrf_app.test_client()
    response = client.post("/api/enqueue", json={"name": "X", "p_type": "Regular"})
    assert response.status_code == 403
    assert response.get_json()["ok"] is False
    assert client.post("/", data={"name": "X", "p_type": "Regular"}).status_code == 403


def test_csrf_accepts_valid_token(csrf_app):
    client = csrf_app.test_client()
    page = client.get("/").get_data(as_text=True)
    token = page.split('name="csrf-token" content="')[1].split('"')[0]
    ok = client.post("/api/enqueue", json={"name": "X", "p_type": "Regular"}, headers={"X-CSRF-Token": token})
    assert ok.status_code == 201
    forged = client.post("/api/enqueue", json={"name": "Y"}, headers={"X-CSRF-Token": "forged"})
    assert forged.status_code == 403


def test_security_headers_present(client):
    headers = client.get("/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "script-src 'self'" in headers["Content-Security-Policy"]


def test_production_refuses_default_secrets(monkeypatch):
    from app.config import ProductionConfig

    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "dev-only-change-me")
    monkeypatch.setattr(ProductionConfig, "ADMIN_PASSWORD_HASH", "")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        create_app("production")
