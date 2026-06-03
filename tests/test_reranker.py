import sys
import os
import requests
import json
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from core.settings import settings

@pytest.mark.skip(reason="Reranker API needs configured credentials")
def test_reranker():
    url = settings.RERANKER_BASE_URL.replace("/v1", "") + "/v1/rerank"
    api_key = settings.RERANKER_API_KEY.get_secret_value() if settings.RERANKER_API_KEY else "sk-fake-key-for-testing"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.RERANKER_MODEL,
        "query": "差旅住宿",
        "documents": ["今天天气好", "出差报销每天300元"]
    }

    response = requests.post(url, json=payload, headers=headers)
    assert response.status_code in [200, 401] # 401 is expected if fake key
