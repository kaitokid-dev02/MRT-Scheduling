import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app("testing", DATABASE=str(tmp_path / "test.db"))


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(client, app):
    """A client that is already logged in as the administrator."""
    response = client.post(
        "/login",
        data={
            "username": app.config["ADMIN_USERNAME"],
            "password": app.config["ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 302
    return client


@pytest.fixture
def enqueue(client):
    def _enqueue(name="Alice", p_type="REGULAR"):
        response = client.post("/api/enqueue", json={"name": name, "p_type": p_type})
        assert response.status_code == 201, response.get_json()
        return response.get_json()["passenger"]

    return _enqueue


@pytest.fixture
def issue_ticket(client, enqueue):
    """Enqueue → serve → assign. Returns the assign response JSON."""

    def _issue(name="Alice", p_type="REGULAR", start="North Avenue", destination="Guadalupe"):
        enqueue(name, p_type)
        passenger = client.post("/api/serve").get_json()["passenger"]
        response = client.post(
            "/api/assign",
            json={"passenger_id": passenger["id"], "start_station": start, "destination": destination},
        )
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _issue
