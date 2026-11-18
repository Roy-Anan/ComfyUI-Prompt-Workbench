import sqlite3

import rule_store


def _seed_rules(database_path):
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    rule_store.ensure_schema(connection)
    rule_store.upsert_rule(connection, "global", None, "steps", 20)
    rule_store.upsert_rule(
        connection, "checkpoint", "pony.safetensors", "steps", 32,
        provenance="author", confidence="authoritative",
    )
    connection.close()


def test_list_rules_endpoint(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_rules(db)

    response = test_client.get("/api/rules", headers={"Authorization": "Bearer test-session-token"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert {item["rule_key"] for item in items} == {"steps"}

    filtered = test_client.get(
        "/api/rules?level=global",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["items"][0]["scope_key"] == ""


def test_resolve_rules_endpoint_applies_inheritance(client):
    test_client, main = client
    db = main.DATA_ROOT / "database" / "workbench.sqlite3"
    _seed_rules(db)

    response = test_client.get(
        "/api/rules/resolve?level=checkpoint&scope_key=pony.safetensors&keys=steps,clip_skip",
        headers={"Authorization": "Bearer test-session-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fields"]["steps"]["value"] == 32
    assert body["fields"]["steps"]["source_level"] == "checkpoint"
    assert body["unknown"] == ["clip_skip"]


def test_resolve_rules_rejects_empty_keys_and_bad_level(client):
    test_client, _ = client
    headers = {"Authorization": "Bearer test-session-token"}

    bad_keys = test_client.get("/api/rules/resolve?level=global&keys=", headers=headers)
    assert bad_keys.status_code == 400

    bad_level = test_client.get(
        "/api/rules/resolve?level=avatar&keys=steps", headers=headers
    )
    assert bad_level.status_code == 400


def test_upsert_and_delete_rule_via_api(client):
    test_client, main = client
    headers = {"Authorization": "Bearer test-session-token"}

    created = test_client.post(
        "/api/rules",
        headers=headers,
        json={
            "level": "checkpoint",
            "scope_key": "pony.safetensors",
            "rule_key": "steps",
            "value": 32,
            "provenance": "author",
            "confidence": "authoritative",
        },
    )
    assert created.status_code == 200
    assert created.json()["value"] == 32

    listing = test_client.get("/api/rules", headers=headers)
    assert len(listing.json()["items"]) == 1

    removed = test_client.request(
        "DELETE",
        "/api/rules",
        headers=headers,
        json={
            "level": "checkpoint",
            "scope_key": "pony.safetensors",
            "rule_key": "steps",
        },
    )
    assert removed.status_code == 200
    assert removed.json()["removed"] is True

    listing = test_client.get("/api/rules", headers=headers)
    assert listing.json()["items"] == []


def test_upsert_rejects_invalid_rule(client):
    test_client, _ = client
    headers = {"Authorization": "Bearer test-session-token"}

    invalid = test_client.post(
        "/api/rules",
        headers=headers,
        json={"level": "avatar", "rule_key": "steps", "value": 20},
    )
    assert invalid.status_code == 400

    listing = test_client.get("/api/rules", headers=headers)
    assert listing.json()["items"] == []
