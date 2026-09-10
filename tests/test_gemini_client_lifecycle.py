from app.services import gemini_service


def test_gemini_client_is_cached(monkeypatch):
    created = []

    class FakeClient:
        def close(self):
            pass

    def fake_client_factory(*args, **kwargs):
        instance = FakeClient()
        created.append(instance)
        return instance

    gemini_service._client.cache_clear()
    monkeypatch.setattr(gemini_service.genai, "Client", fake_client_factory)
    monkeypatch.setattr(
        gemini_service.settings,
        "gemini_api_key",
        "test-key",
    )

    first = gemini_service._client()
    second = gemini_service._client()

    assert first is second
    assert len(created) == 1

    gemini_service._client.cache_clear()
