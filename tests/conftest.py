"""All automated checks are offline; API contracts use explicit mock sessions."""
import pytest
import requests


@pytest.fixture(autouse=True)
def block_live_requests(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('A test attempted a live HTTP request; use a mocked response.')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)
