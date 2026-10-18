from tests.conftest import register


def test_register_sets_httponly_cookie_and_hides_password(make_client):
    c = make_client()
    r = c.post("/api/auth/register", json={"email": "A@Example.com", "name": "Al", "password": "longenough1"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "a@example.com" and "password" not in body and "password_hash" not in body
    set_cookie = r.headers["set-cookie"].lower()
    assert "httponly" in set_cookie and "samesite=lax" in set_cookie


def test_password_is_stored_hashed(make_client, engine):
    from sqlalchemy import text
    register(make_client())
    with engine.connect() as conn:
        stored = conn.execute(text("select password_hash from users")).scalar()
    assert stored != "correct-horse-1" and stored.startswith("$2")


def test_duplicate_email_rejected(make_client):
    register(make_client())
    r = make_client().post("/api/auth/register", json={"email": "ALICE@example.com", "name": "x", "password": "longenough1"})
    assert r.status_code == 409


def test_register_validation(make_client):
    c = make_client()
    assert c.post("/api/auth/register", json={"email": "nope", "name": "x", "password": "longenough1"}).status_code == 422
    assert c.post("/api/auth/register", json={"email": "a@b.co", "name": "x", "password": "short"}).status_code == 422
    assert c.post("/api/auth/register", json={"email": "a@b.co", "name": "  ", "password": "longenough1"}).status_code == 422
    assert c.post("/api/auth/register", json={"email": "a@b.co", "name": "x", "password": "longenough1",
                                              "timezone": "Mars/Base"}).status_code == 422


def test_login_logout_flow(make_client):
    register(make_client())
    c = make_client()
    assert c.get("/api/auth/me").status_code == 401
    assert c.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever1"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": "alice@example.com", "password": "correct-horse-1"}).status_code == 200
    assert c.get("/api/auth/me").json()["email"] == "alice@example.com"
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_logout_invalidates_the_token_server_side(make_client):
    c = make_client()
    register(c)
    token = c.cookies.get("studyos_session")
    c.post("/api/auth/logout")
    stolen = make_client()
    stolen.cookies.set("studyos_session", token)
    assert stolen.get("/api/auth/me").status_code == 401


def test_every_protected_endpoint_requires_login(make_client):
    c = make_client()
    for method, url in [("get", "/api/subjects"), ("get", "/api/tasks"), ("get", "/api/exams"),
                        ("get", "/api/sessions"), ("get", "/api/dashboard"), ("get", "/api/availability"),
                        ("post", "/api/planner/generate"), ("get", "/api/planner/missed"),
                        ("delete", "/api/tasks/1"), ("patch", "/api/subjects/1")]:
        assert getattr(c, method)(url).status_code == 401, url


def test_update_profile_timezone(client):
    assert client.patch("/api/auth/me", json={"timezone": "Asia/Kolkata"}).json()["timezone"] == "Asia/Kolkata"
    assert client.patch("/api/auth/me", json={"timezone": "bad"}).status_code == 422
