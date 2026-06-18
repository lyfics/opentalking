from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.routes import runtime_config
from opentalking.core.config import get_settings


def _clear_runtime_env(monkeypatch) -> None:
    for key in runtime_config._RUNTIME_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _client(monkeypatch, tmp_path) -> TestClient:
    _clear_runtime_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runtime_config, "_ENV_PATH", tmp_path / ".env")
    get_settings.cache_clear()
    app = FastAPI()
    app.state.settings = get_settings()
    app.include_router(runtime_config.router)
    return TestClient(app)


def test_runtime_config_get_masks_secret_values(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "OPENTALKING_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1",
                "OPENTALKING_LLM_MODEL=qwen-turbo",
                "OPENTALKING_LLM_API_KEY=sk-test-secret",
                "OPENTALKING_TTS_PROVIDER=edge",
                "OPENTALKING_TTS_DEFAULT_PROVIDER=edge",
                "OPENTALKING_TTS_DASHSCOPE_API_KEY=sk-test-secret",
                "OPENTALKING_STT_DEFAULT_PROVIDER=dashscope",
                "OPENTALKING_STT_DASHSCOPE_API_KEY=sk-test-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with _client(monkeypatch, tmp_path) as client:
        response = client.get("/runtime-config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm"]["api_key_set"] is True
    assert payload["tts"]["dashscope_api_key_set"] is True
    assert payload["stt"]["api_key_set"] is True
    assert "sk-test-secret" not in response.text


def test_runtime_config_apply_persists_and_refreshes_settings(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text(
        "OPENTALKING_LLM_MODEL=old-model\n"
        "OPENTALKING_TTS_DEFAULT_PROVIDER=edge\n"
        "OPENTALKING_STT_DEFAULT_PROVIDER=dashscope\n",
        encoding="utf-8",
    )

    with _client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/runtime-config/apply",
            json={
                "llm_base_url": "https://example.test/v1",
                "llm_model": "new-model",
                "llm_api_key": "sk-new-secret",
                "tts_provider": "dashscope",
                "tts_dashscope_model": "qwen3-tts-flash-realtime",
                "tts_dashscope_voice": "Cherry",
                "stt_model": "paraformer-realtime-v2",
                "sync_dashscope_api_key": True,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["applied"] is True
    assert payload["llm"]["model"] == "new-model"
    assert payload["llm"]["api_key_set"] is True
    assert "sk-new-secret" not in response.text
    assert os.environ["OPENTALKING_LLM_MODEL"] == "new-model"
    assert os.environ["OPENTALKING_TTS_DASHSCOPE_API_KEY"] == "sk-new-secret"
    assert os.environ["OPENTALKING_STT_DASHSCOPE_API_KEY"] == "sk-new-secret"
    assert get_settings().llm_model == "new-model"
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "OPENTALKING_LLM_MODEL=new-model" in text
    assert "OPENTALKING_TTS_DEFAULT_PROVIDER=dashscope" in text


def test_runtime_config_rejects_unsupported_provider(monkeypatch, tmp_path) -> None:
    with _client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/runtime-config/apply",
            json={
                "tts_provider": "indextts",
                "stt_provider": "dashscope",
            },
        )

    assert response.status_code == 400
