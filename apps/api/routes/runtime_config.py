from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from apps.api.core.config import get_settings
from opentalking.providers.stt.factory import stt_provider_config
from opentalking.providers.tts.factory import tts_provider_config
from opentalking.providers.tts.providers import normalize_tts_provider

router = APIRouter(prefix="/runtime-config", tags=["runtime-config"])

_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
_ALLOWED_TTS_PROVIDERS = {"edge", "dashscope"}
_ALLOWED_STT_PROVIDERS = {"dashscope"}
_RUNTIME_ENV_KEYS = {
    "DASHSCOPE_API_KEY",
    "OPENTALKING_LLM_PROVIDER",
    "OPENTALKING_LLM_BASE_URL",
    "OPENTALKING_LLM_API_KEY",
    "OPENTALKING_LLM_MODEL",
    "OPENTALKING_STT_DEFAULT_PROVIDER",
    "OPENTALKING_STT_ENABLED_PROVIDERS",
    "OPENTALKING_STT_MODEL",
    "OPENTALKING_STT_DASHSCOPE_MODEL",
    "OPENTALKING_STT_DASHSCOPE_API_KEY",
    "OPENTALKING_TTS_PROVIDER",
    "OPENTALKING_TTS_DEFAULT_PROVIDER",
    "OPENTALKING_TTS_ENABLED_PROVIDERS",
    "OPENTALKING_TTS_EDGE_VOICE",
    "OPENTALKING_TTS_VOICE",
    "OPENTALKING_TTS_DASHSCOPE_API_KEY",
    "OPENTALKING_TTS_DASHSCOPE_MODEL",
    "OPENTALKING_TTS_DASHSCOPE_VOICE",
}


class RuntimeConfigPayload(BaseModel):
    llm_base_url: str | None = Field(default=None, max_length=2048)
    llm_api_key: str | None = Field(default=None, max_length=4096)
    llm_model: str | None = Field(default=None, max_length=256)
    tts_provider: str | None = Field(default=None, max_length=64)
    tts_edge_voice: str | None = Field(default=None, max_length=256)
    tts_dashscope_api_key: str | None = Field(default=None, max_length=4096)
    tts_dashscope_model: str | None = Field(default=None, max_length=256)
    tts_dashscope_voice: str | None = Field(default=None, max_length=256)
    stt_provider: str | None = Field(default=None, max_length=64)
    stt_model: str | None = Field(default=None, max_length=256)
    stt_dashscope_api_key: str | None = Field(default=None, max_length=4096)
    sync_dashscope_api_key: bool = True


def _strip(value: str | None) -> str:
    return (value or "").strip()


def _read_env_lines(path: Path) -> tuple[list[str], dict[str, str]]:
    if not path.exists():
        return [], {}
    lines = path.read_text(encoding="utf-8").splitlines()
    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.removeprefix("export ").strip()
        if key:
            values[key] = _unquote_env_value(value.strip())
    return lines, values


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _quote_env_value(value: str) -> str:
    if not value:
        return ""
    if any(ch.isspace() for ch in value) or any(ch in value for ch in ['"', "'", "#"]):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _env_value(values: dict[str, str], key: str, fallback: str = "") -> str:
    return os.environ.get(key, "").strip() or values.get(key, "").strip() or fallback


def _write_env_updates(path: Path, updates: dict[str, str]) -> None:
    lines, _ = _read_env_lines(path)
    now = int(time.time())
    if path.exists():
        backup = path.with_name(f"{path.name}.bak.{now}")
        shutil.copy2(path, backup)
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        raw_key, _ = stripped.split("=", 1)
        key = raw_key.removeprefix("export ").strip()
        if key in updates:
            prefix = "export " if raw_key.strip().startswith("export ") else ""
            out.append(f"{prefix}{key}={_quote_env_value(updates[key])}")
            seen.add(key)
        else:
            out.append(line)
    if updates:
        if out and out[-1].strip():
            out.append("")
        for key in sorted(updates):
            if key not in seen:
                out.append(f"{key}={_quote_env_value(updates[key])}")
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _current_payload(settings: Any | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    _, file_values = _read_env_lines(_ENV_PATH)
    tts_provider = (
        _env_value(file_values, "OPENTALKING_TTS_DEFAULT_PROVIDER")
        or _env_value(file_values, "OPENTALKING_TTS_PROVIDER")
        or getattr(settings, "normalized_tts_default_provider", "edge")
        or "edge"
    )
    try:
        tts_provider = normalize_tts_provider(tts_provider, default="edge") or "edge"
    except ValueError:
        tts_provider = "edge"
    if tts_provider not in _ALLOWED_TTS_PROVIDERS:
        tts_provider = "edge"

    stt_provider = (
        _env_value(file_values, "OPENTALKING_STT_DEFAULT_PROVIDER")
        or getattr(settings, "normalized_stt_default_provider", "dashscope")
        or "dashscope"
    )
    if stt_provider not in _ALLOWED_STT_PROVIDERS:
        stt_provider = "dashscope"

    tts_status = tts_provider_config(tts_provider)
    tts_dashscope_status = tts_provider_config("dashscope")
    stt_status = stt_provider_config(stt_provider)
    llm_key = _env_value(file_values, "OPENTALKING_LLM_API_KEY")
    return {
        "llm": {
            "base_url": _env_value(file_values, "OPENTALKING_LLM_BASE_URL", getattr(settings, "llm_base_url", "")),
            "model": _env_value(file_values, "OPENTALKING_LLM_MODEL", getattr(settings, "llm_model", "")),
            "api_key_set": bool(llm_key),
        },
        "tts": {
            "provider": tts_provider,
            "enabled_providers": ["edge", "dashscope"],
            "edge_voice": _env_value(file_values, "OPENTALKING_TTS_EDGE_VOICE", getattr(settings, "tts_edge_voice", "")),
            "dashscope_model": _env_value(
                file_values,
                "OPENTALKING_TTS_DASHSCOPE_MODEL",
                getattr(settings, "tts_dashscope_model", ""),
            ),
            "dashscope_voice": _env_value(
                file_values,
                "OPENTALKING_TTS_DASHSCOPE_VOICE",
                getattr(settings, "tts_dashscope_voice", ""),
            ),
            "api_key_set": bool(tts_status.get("key_set")),
            "dashscope_api_key_set": bool(tts_dashscope_status.get("key_set")),
            "service_url_set": bool(tts_status.get("service_url_set")),
        },
        "stt": {
            "provider": stt_provider,
            "enabled_providers": ["dashscope"],
            "model": _env_value(file_values, "OPENTALKING_STT_MODEL", getattr(settings, "stt_model", "")),
            "api_key_set": bool(stt_status.get("key_set")),
            "service_url_set": bool(stt_status.get("service_url_set")),
        },
    }


def _build_updates(payload: RuntimeConfigPayload) -> dict[str, str]:
    updates: dict[str, str] = {
        "OPENTALKING_LLM_PROVIDER": "openai_compatible",
        "OPENTALKING_TTS_ENABLED_PROVIDERS": "edge,dashscope",
        "OPENTALKING_STT_DEFAULT_PROVIDER": "dashscope",
        "OPENTALKING_STT_ENABLED_PROVIDERS": "dashscope",
    }

    if value := _strip(payload.llm_base_url):
        updates["OPENTALKING_LLM_BASE_URL"] = value.rstrip("/")
    if value := _strip(payload.llm_model):
        updates["OPENTALKING_LLM_MODEL"] = value
    sync_key = ""
    if value := _strip(payload.llm_api_key):
        updates["OPENTALKING_LLM_API_KEY"] = value
        sync_key = value

    tts_provider = _strip(payload.tts_provider) or "edge"
    if tts_provider not in _ALLOWED_TTS_PROVIDERS:
        raise HTTPException(status_code=400, detail="当前镜像只支持 Edge 和 DashScope TTS。")
    updates["OPENTALKING_TTS_PROVIDER"] = tts_provider
    updates["OPENTALKING_TTS_DEFAULT_PROVIDER"] = tts_provider
    if value := _strip(payload.tts_edge_voice):
        updates["OPENTALKING_TTS_EDGE_VOICE"] = value
        if tts_provider == "edge":
            updates["OPENTALKING_TTS_VOICE"] = value
    if value := _strip(payload.tts_dashscope_model):
        updates["OPENTALKING_TTS_DASHSCOPE_MODEL"] = value
    if value := _strip(payload.tts_dashscope_voice):
        updates["OPENTALKING_TTS_DASHSCOPE_VOICE"] = value
        if tts_provider == "dashscope":
            updates["OPENTALKING_TTS_VOICE"] = value
    if value := _strip(payload.tts_dashscope_api_key):
        updates["OPENTALKING_TTS_DASHSCOPE_API_KEY"] = value
        sync_key = sync_key or value

    stt_provider = _strip(payload.stt_provider) or "dashscope"
    if stt_provider not in _ALLOWED_STT_PROVIDERS:
        raise HTTPException(status_code=400, detail="当前镜像只支持 DashScope STT。")
    if value := _strip(payload.stt_model):
        updates["OPENTALKING_STT_MODEL"] = value
        updates["OPENTALKING_STT_DASHSCOPE_MODEL"] = value
    if value := _strip(payload.stt_dashscope_api_key):
        updates["OPENTALKING_STT_DASHSCOPE_API_KEY"] = value
        sync_key = sync_key or value
    if payload.sync_dashscope_api_key and sync_key:
        updates.setdefault("DASHSCOPE_API_KEY", sync_key)
        updates.setdefault("OPENTALKING_LLM_API_KEY", sync_key)
        updates.setdefault("OPENTALKING_TTS_DASHSCOPE_API_KEY", sync_key)
        updates.setdefault("OPENTALKING_STT_DASHSCOPE_API_KEY", sync_key)
    return updates


def _refresh_settings(request: Request) -> Any:
    get_settings.cache_clear()
    settings = get_settings()
    request.app.state.settings = settings
    return settings


def _refresh_live_runners(request: Request, settings: Any) -> int:
    runners = getattr(request.app.state, "session_runners", None)
    if not isinstance(runners, dict):
        return 0
    count = 0
    for runner in list(runners.values()):
        if hasattr(runner, "_llm_base_url"):
            runner._llm_base_url = settings.llm_base_url
            runner._llm_api_key = settings.llm_api_key
            runner._llm_model = settings.llm_model
            runner._llm_client = None
            count += 1
        if hasattr(runner, "llm"):
            from opentalking.providers.llm.openai_compatible.adapter import OpenAICompatibleLLMClient

            runner.llm = OpenAICompatibleLLMClient(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
            )
            count += 1
    return count


@router.get("")
async def get_runtime_config(request: Request) -> dict[str, Any]:
    return _current_payload(getattr(request.app.state, "settings", None))


@router.post("/apply")
async def apply_runtime_config(payload: RuntimeConfigPayload, request: Request) -> dict[str, Any]:
    updates = _build_updates(payload)
    unknown = set(updates) - _RUNTIME_ENV_KEYS
    if unknown:
        raise HTTPException(status_code=400, detail=f"unsupported runtime config keys: {', '.join(sorted(unknown))}")
    _write_env_updates(_ENV_PATH, updates)
    for key, value in updates.items():
        os.environ[key] = value
    settings = _refresh_settings(request)
    refreshed_runners = _refresh_live_runners(request, settings)
    result = _current_payload(settings)
    result["applied"] = True
    result["requires_new_session"] = refreshed_runners == 0
    result["live_runners_refreshed"] = refreshed_runners
    return result
