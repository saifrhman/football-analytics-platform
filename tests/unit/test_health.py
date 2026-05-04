from football_intelligence.api.main import health


def test_health_endpoint_payload() -> None:
    response = health()
    assert response["status"] == "ok"
