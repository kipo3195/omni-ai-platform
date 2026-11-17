import os
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import app.bootstrap as bootstrap


def test_application_lifespan_starts_and_stops_execution_service(
    monkeypatch,
):
    datasource_url = os.getenv("TEST_DATASOURCE_URL")
    username = os.getenv("TEST_DATASOURCE_USERNAME")
    password = os.getenv("TEST_DATASOURCE_PASSWORD")
    if not datasource_url or not username:
        pytest.skip("MariaDB integration test datasource is not configured")

    monkeypatch.setattr(
        bootstrap,
        "settings",
        replace(
            bootstrap.settings,
            datasource_url=datasource_url,
            datasource_username=username,
            datasource_password=password or "",
            returned_message_callback_base_url="",
        ),
    )

    with TestClient(bootstrap.create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
