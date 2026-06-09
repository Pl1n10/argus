"""HTTP surface: health, job API, ingest, dashboard, auth. Uses TestClient
(no real server, no scheduler). The sweep loop itself is covered in
test_monitor; here we verify the request/response contract and that an ingest
drives state through the real Store."""


def _create(client, **over):
    body = {"name": "nightly", "schedule_kind": "interval", "schedule_expr": "3600",
            "grace_seconds": 600}
    body.update(over)
    return client.post("/api/jobs", json=body)


class TestHealth:
    def test_ok(self, client):
        assert client.get("/health").json() == {"status": "ok"}


class TestJobApi:
    def test_create_returns_ingest_url(self, client):
        r = _create(client)
        assert r.status_code == 201
        body = r.json()
        assert body["ingest_url"].startswith("http://test.local/ingest/")
        assert body["state"] == "new"

    def test_create_rejects_blank_name(self, client):
        assert _create(client, name="").status_code == 400

    def test_create_rejects_bad_schedule(self, client):
        assert _create(client, schedule_expr="nope").status_code == 400

    def test_list_and_get(self, client):
        jid = _create(client).json()["id"]
        assert client.get("/api/jobs").json()[0]["id"] == jid
        assert client.get(f"/api/jobs/{jid}").json()["id"] == jid

    def test_get_missing_404(self, client):
        assert client.get("/api/jobs/999").status_code == 404

    def test_delete(self, client):
        jid = _create(client).json()["id"]
        assert client.delete(f"/api/jobs/{jid}").status_code == 204
        assert client.get(f"/api/jobs/{jid}").status_code == 404


class TestIngest:
    def test_bare_get_marks_up(self, client):
        url = _create(client).json()["ingest_url"].replace("http://test.local", "")
        r = client.get(url)
        assert r.status_code == 200
        assert r.json()["status"] == "success"
        assert r.json()["state"] == "up"

    def test_post_nonzero_exit_marks_failed_and_alerts(self, client, channel):
        url = _create(client).json()["ingest_url"].replace("http://test.local", "")
        r = client.post(url, json={"exit_code": 1})
        assert r.json()["state"] == "failed"
        assert len(channel.sent) == 1

    def test_exit_code_via_query(self, client):
        url = _create(client).json()["ingest_url"].replace("http://test.local", "")
        assert client.get(url + "?exit_code=3").json()["state"] == "failed"

    def test_restic_flavor(self, client):
        url = _create(client).json()["ingest_url"].replace("http://test.local", "")
        r = client.post(url + "?flavor=restic",
                        json={"message_type": "summary", "total_bytes_processed": 999})
        assert r.json()["status"] == "success"

    def test_unknown_token_404(self, client):
        assert client.get("/ingest/deadbeef").status_code == 404

    def test_bad_flavor_body_400(self, client):
        url = _create(client).json()["ingest_url"].replace("http://test.local", "")
        assert client.post(url + "?flavor=borg", json={"nope": 1}).status_code == 400


class TestDashboard:
    def test_empty_renders(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "No jobs yet" in r.text

    def test_lists_job(self, client):
        _create(client, name="my-special-job")
        assert "my-special-job" in client.get("/").text


class TestAuth:
    def test_api_blocked_without_token(self, auth_client):
        assert auth_client.get("/api/jobs").status_code == 401

    def test_api_ok_with_bearer(self, auth_client):
        r = auth_client.get("/api/jobs", headers={"Authorization": "Bearer s3cret"})
        assert r.status_code == 200

    def test_dashboard_blocked_without_token(self, auth_client):
        assert auth_client.get("/").status_code == 401

    def test_dashboard_ok_with_query_token(self, auth_client):
        assert auth_client.get("/?token=s3cret").status_code == 200

    def test_ingest_open_without_admin_token(self, auth_client):
        jid = auth_client.post("/api/jobs",
                               headers={"Authorization": "Bearer s3cret"},
                               json={"name": "n", "schedule_kind": "interval",
                                     "schedule_expr": "3600"}).json()
        url = jid["ingest_url"].replace("http://test.local", "")
        assert auth_client.get(url).status_code == 200  # no admin token needed
