"""Queue, serve and assign behaviour through the public JSON API."""


def names(payload, lane):
    return [p["name"] for p in payload[lane]]


def test_priority_is_served_before_regular_and_fifo_within_lane(client, enqueue):
    enqueue("Reg1", "REGULAR")
    enqueue("Sen1", "Senior Citizen")
    enqueue("Reg2", "Regular")
    enqueue("Pwd1", "PWD")

    order = [client.post("/api/serve").get_json()["passenger"]["name"] for _ in range(4)]
    assert order == ["Sen1", "Pwd1", "Reg1", "Reg2"]


def test_serve_on_empty_queue_is_404(client):
    response = client.post("/api/serve")
    assert response.status_code == 404
    assert response.get_json() == {"ok": False, "error": "No passenger to serve."}


def test_queues_endpoint_reports_next_and_lanes(client, enqueue):
    enqueue("Reg", "Regular")
    enqueue("Pri", "Priority")
    data = client.get("/api/queues").get_json()
    assert names(data, "priority_q") == ["Pri"]
    assert names(data, "regular_q") == ["Reg"]
    assert data["next"]["name"] == "Pri"
    assert data["serving"] == []


def test_cancelling_a_serve_keeps_the_passengers_place(client, enqueue):
    # Regression: the original deleted the passenger on serve, so Cancel lost them.
    enqueue("First", "Regular")
    enqueue("Second", "Regular")
    served = client.post("/api/serve").get_json()["passenger"]
    assert served["name"] == "First"
    assert names(client.get("/api/queues").get_json(), "regular_q") == ["Second"]

    assert client.post("/api/return", json={"id": served["id"]}).status_code == 200
    data = client.get("/api/queues").get_json()
    assert names(data, "regular_q") == ["First", "Second"]
    assert data["serving"] == []


def test_return_requires_serving_state(client, enqueue):
    passenger = enqueue("Waiting")
    assert client.post("/api/return", json={"id": passenger["id"]}).status_code == 409


def test_remove_waiting_passenger(client, enqueue):
    passenger = enqueue("Gone")
    assert client.post("/api/remove", json={"id": passenger["id"]}).status_code == 200
    assert client.get("/api/queues").get_json()["next"] is None
    assert client.post("/api/remove", json={"id": passenger["id"]}).status_code == 409
    assert client.post("/api/remove", json={"id": 9999}).status_code == 404
    assert client.post("/api/remove", json={"id": "abc"}).status_code == 400


def test_enqueue_validation(client):
    assert client.post("/api/enqueue", json={"name": "", "p_type": "Regular"}).status_code == 400
    assert client.post("/api/enqueue", json={"name": "X", "p_type": "VIP"}).status_code == 400
    assert client.post("/api/enqueue", json={"p_type": "Regular"}).status_code == 400


def test_names_are_stored_verbatim_and_escaped_by_templates(client, enqueue):
    enqueue("<script>alert(1)</script>")
    # API returns data as-is (JSON); the frontend uses textContent, templates autoescape.
    assert client.get("/api/queues").get_json()["next"]["name"] == "<script>alert(1)</script>"


# ---- assign ---------------------------------------------------------------


def test_full_flow_issues_ticket_and_logs_it(client, issue_ticket):
    result = issue_ticket("Maria", "Senior Citizen", "North Avenue", "Baclaran")
    assert result["ok"] is True
    assert result["route_path"][0] == "North Avenue" and result["route_path"][-1] == "Baclaran"
    assert result["total_time"] > 0
    assert result["fare"] == 55
    assert result["train_number"].endswith("-1")  # auto-selected next train

    ticket = client.get(result["ticket_url"])
    assert ticket.status_code == 200
    assert b"Maria" in ticket.data and b"Baclaran" in ticket.data

    # served passenger is no longer in any queue
    data = client.get("/api/queues").get_json()
    assert data["next"] is None and data["serving"] == []


def test_assign_with_explicit_train(client, enqueue):
    enqueue("Ana")
    p = client.post("/api/serve").get_json()["passenger"]
    response = client.post(
        "/api/assign",
        json={"passenger_id": p["id"], "destination": "Boni", "train_number": "MRT Line 3-2"},
    )
    assert response.status_code == 201
    assert response.get_json()["train_number"] == "MRT Line 3-2"


def test_assign_rejections(client, enqueue):
    waiting = enqueue("NotServed")
    base = {"passenger_id": waiting["id"], "destination": "Boni"}
    assert client.post("/api/assign", json=base).status_code == 409  # not being served

    client.post("/api/serve")  # NotServed is now 'serving'
    assert client.post("/api/assign", json={**base, "destination": "Atlantis"}).status_code == 400
    assert client.post("/api/assign", json={**base, "destination": ""}).status_code == 400
    assert client.post("/api/assign", json={**base, "destination": "North Avenue"}).status_code == 400
    assert client.post("/api/assign", json={**base, "train_number": "Bogus-1"}).status_code == 400
    assert client.post("/api/assign", json={"passenger_id": 9999, "destination": "Boni"}).status_code == 404

    # still servable after all those failed attempts
    assert client.post("/api/assign", json=base).status_code == 201


def test_cannot_assign_twice(client, issue_ticket):
    result = issue_ticket()
    again = client.post(
        "/api/assign", json={"passenger_id": 1, "destination": "Boni", "start_station": "North Avenue"}
    )
    assert result["ok"] and again.status_code == 409


def test_route_preview(client):
    data = client.get("/api/route?start=North+Avenue&destination=Guadalupe").get_json()
    assert data["total_time"] == 18
    assert data["train_line"] == "MRT Line 3"
    assert [t["train_number"] for t in data["trains"]] == ["MRT Line 3-1", "MRT Line 3-2", "MRT Line 3-3"]
    assert client.get("/api/route?start=North+Avenue&destination=Nowhere").status_code == 400
    assert client.get("/api/route?start=Boni&destination=Boni").status_code == 400


def test_dashboard_and_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/healthz").get_json() == {"status": "ok"}
    assert client.get("/does-not-exist").status_code == 404
    assert client.get("/api/does-not-exist").get_json()["ok"] is False


def test_form_fallback_enqueue(client):
    response = client.post("/", data={"name": "NoJS", "p_type": "PWD"}, follow_redirects=True)
    assert response.status_code == 200 and b"NoJS added" in response.data
    assert client.get("/api/queues").get_json()["priority_q"][0]["name"] == "NoJS"
