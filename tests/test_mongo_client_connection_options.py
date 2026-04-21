from __future__ import annotations

from src.db.mongo_client import MongoClientWrapper
from src.config.settings import MongoConfig


class _FakeClient:
    def __init__(self, uri: str, **kwargs):
        self.uri = uri
        self.kwargs = kwargs

    def __getitem__(self, name: str):
        return {"name": name}

    def close(self):
        return None


def test_mongo_client_wrapper_passes_optional_connection_flags(monkeypatch) -> None:
    captured = {}

    def fake_client(uri: str, **kwargs):
        captured["uri"] = uri
        captured["kwargs"] = kwargs
        return _FakeClient(uri, **kwargs)

    monkeypatch.setattr("src.db.mongo_client.MongoClient", fake_client)

    wrapper = MongoClientWrapper(
        MongoConfig(
            active_target="uni",
            uri="mongodb://example:27017",
            database="mercator",
            direct_connection=True,
            tls_allow_invalid_certificates=True,
        )
    )

    db = wrapper.get_database()
    assert db["name"] == "mercator"
    assert captured["kwargs"]["directConnection"] is True
    assert captured["kwargs"]["tlsAllowInvalidCertificates"] is True
