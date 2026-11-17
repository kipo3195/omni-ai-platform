import pytest

from app.features.returned_message_topics.mariadb_execution_repository import (
    _parse_datasource_url,
    _validate_table_prefix,
)


def test_parses_spring_jdbc_mariadb_datasource_url():
    settings = _parse_datasource_url(
        "jdbc:mariadb://host.docker.internal:3306/ws_ucware",
        "ucware",
        "secret",
    )

    assert settings.host == "host.docker.internal"
    assert settings.port == 3306
    assert settings.database == "ws_ucware"
    assert settings.username == "ucware"
    assert settings.password == "secret"
    assert settings.charset == "utf8mb4"


def test_rejects_non_mariadb_datasource_url():
    with pytest.raises(ValueError, match="DATASOURCE_URL"):
        _parse_datasource_url(
            "jdbc:postgresql://localhost:5432/example",
            "user",
            "secret",
        )


def test_rejects_unsafe_table_prefix():
    with pytest.raises(ValueError, match="table_prefix"):
        _validate_table_prefix("test-prefix;")
