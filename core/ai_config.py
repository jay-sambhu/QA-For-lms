"""
Multi-AI Provider Configuration & Dynamic Engine Router for JASUSS (Powered by Nexus)
Supports Google Gemini, OpenAI, Anthropic Claude, DeepSeek, and Local LLM endpoints.

Admin-entered provider settings are persisted to a JSON file (AI_CONFIG_PATH,
default <repo>/user_data/ai_provider_config.json) so the API and the worker
see the same configuration and it survives a restart. The process
environment is never modified: GEMINI_API_KEY in the environment is the
owner's trial key and must not be overwritten by whatever an admin pastes
into the AI Providers tab.
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[1]


class AIProviderMeta(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    models: List[str]
    default_model: str
    env_key_name: str
    requires_endpoint: bool = False
    default_endpoint: Optional[str] = None
    is_configured: bool = False

# Registry of supported AI Provider Platforms
AI_PROVIDERS_REGISTRY: Dict[str, AIProviderMeta] = {
    "gemini": AIProviderMeta(
        id="gemini",
        name="Google Gemini AI",
        description="High-speed reasoning, multi-modal analysis, and native structured schema parsing.",
        icon="SiGoogle",
        # Google retires Gemini names often; keep this list to models that are
        # live today, and keep it in sync with GEMINI_FALLBACK_MODELS.
        models=["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash", "gemini-3-flash-preview"],
        default_model="gemini-3.8-flash",
        env_key_name="GEMINI_API_KEY",
        requires_endpoint=False,
    ),
    "openai": AIProviderMeta(
        id="openai",
        name="OpenAI GPT & O-Series",
        description="Industry-standard reasoning models for deep code synthesis and defect classification.",
        icon="SiOpenai",
        models=["gpt-4o", "gpt-4o-mini", "o3-mini", "gpt-4-turbo"],
        default_model="gpt-4o",
        env_key_name="OPENAI_API_KEY",
        requires_endpoint=False,
    ),
    "anthropic": AIProviderMeta(
        id="anthropic",
        name="Anthropic Claude",
        description="Superior precision for code analysis, nuanced defect root causes, and QA audits.",
        icon="SiAnthropic",
        models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        default_model="claude-3-5-sonnet-20241022",
        env_key_name="ANTHROPIC_API_KEY",
        requires_endpoint=False,
    ),
    "deepseek": AIProviderMeta(
        id="deepseek",
        name="DeepSeek Reasoning AI",
        description="Cost-effective chain-of-thought reasoning models for intricate software QA triage.",
        icon="TbBrain",
        models=["deepseek-chat", "deepseek-reasoner"],
        default_model="deepseek-chat",
        env_key_name="DEEPSEEK_API_KEY",
        requires_endpoint=True,
        default_endpoint="https://api.deepseek.com/v1",
    ),
    "local_llm": AIProviderMeta(
        id="local_llm",
        name="Ollama / Local vLLM Cluster",
        description="Air-gapped self-hosted local inference with zero telemetry egress for private corporate networks.",
        icon="TbServer2",
        models=["llama3.3", "qwen2.5-coder:32b", "mistral-nemo", "deepseek-r1:14b"],
        default_model="llama3.3",
        env_key_name="LOCAL_LLM_API_KEY",
        requires_endpoint=True,
        default_endpoint="http://localhost:11434/v1",
    ),
}

_DEFAULT_STATE: Dict[str, Any] = {
    "active_provider": "gemini",
    "active_model": "gemini-3.8-flash",
    "temperature": 0.2,
    "max_tokens": 4096,
    "custom_endpoints": {
        "deepseek": "https://api.deepseek.com/v1",
        "local_llm": "http://localhost:11434/v1",
    },
    "custom_keys": {},
}

_STATE_LOCK = threading.Lock()


def _config_path() -> Path:
    raw = (os.environ.get("AI_CONFIG_PATH") or "").strip()
    if raw:
        return Path(raw)
    return ROOT_DIR / "user_data" / "ai_provider_config.json"


def _load_state() -> Dict[str, Any]:
    state = json.loads(json.dumps(_DEFAULT_STATE))
    path = _config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return state
    if not isinstance(saved, dict):
        return state
    for key in ("active_provider", "active_model", "temperature", "max_tokens"):
        if key in saved:
            state[key] = saved[key]
    for key in ("custom_endpoints", "custom_keys"):
        if isinstance(saved.get(key), dict):
            state[key].update({str(k): str(v) for k, v in saved[key].items() if v})
    if state["active_provider"] not in AI_PROVIDERS_REGISTRY:
        state["active_provider"] = _DEFAULT_STATE["active_provider"]
        state["active_model"] = _DEFAULT_STATE["active_model"]
    return state


def _save_state(state: Dict[str, Any]) -> None:
    """Atomic, owner-only write (the file holds API keys)."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".ai_config_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# In-memory runtime active AI configuration state (mirrors the file).
_RUNTIME_AI_STATE: Dict[str, Any] = _load_state()


def _refresh_state() -> Dict[str, Any]:
    """Re-read the file so a change made by another process is visible."""
    global _RUNTIME_AI_STATE
    with _STATE_LOCK:
        _RUNTIME_AI_STATE = _load_state()
        return _RUNTIME_AI_STATE


def get_provider_key(provider_id: str) -> Optional[str]:
    """The admin-configured key for a provider, else the environment's."""
    meta = AI_PROVIDERS_REGISTRY.get(provider_id)
    if meta is None:
        return None
    state = _refresh_state()
    custom = (state["custom_keys"].get(provider_id) or "").strip()
    if custom:
        return custom
    env_val = (os.environ.get(meta.env_key_name) or "").strip()
    return env_val or None


def get_ai_providers_state() -> Dict[str, Any]:
    """Return complete list of providers with configuration and active status."""
    state = _refresh_state()
    providers_list = []
    for pid, pmeta in AI_PROVIDERS_REGISTRY.items():
        # Check if environment or custom key exists
        env_val = state["custom_keys"].get(pid) or os.environ.get(pmeta.env_key_name)
        is_conf = bool(env_val and len(str(env_val).strip()) > 3)

        # Mask key for safety
        masked_key = ""
        if is_conf and env_val:
            key_str = str(env_val).strip()
            masked_key = f"{key_str[:4]}...{key_str[-4:]}" if len(key_str) >= 8 else "****"

        p_dict = pmeta.model_dump()
        p_dict["is_configured"] = is_conf
        p_dict["masked_key"] = masked_key
        p_dict["key_source"] = "admin" if state["custom_keys"].get(pid) else ("env" if is_conf else None)
        p_dict["current_endpoint"] = state["custom_endpoints"].get(pid, pmeta.default_endpoint)
        providers_list.append(p_dict)

    return {
        "active_provider": state["active_provider"],
        "active_model": state["active_model"],
        "temperature": state["temperature"],
        "max_tokens": state["max_tokens"],
        "providers": providers_list,
    }


def update_ai_provider_config(
    provider_id: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Update and persist the active provider, model, API keys, or custom endpoint."""
    if provider_id not in AI_PROVIDERS_REGISTRY:
        raise ValueError(f"Unknown AI provider: {provider_id}")

    with _STATE_LOCK:
        state = _load_state()
        state["active_provider"] = provider_id

        if model:
            state["active_model"] = model
        else:
            state["active_model"] = AI_PROVIDERS_REGISTRY[provider_id].default_model

        if api_key and api_key.strip():
            state["custom_keys"][provider_id] = api_key.strip()

        if endpoint and endpoint.strip():
            state["custom_endpoints"][provider_id] = endpoint.strip()

        if temperature is not None:
            state["temperature"] = max(0.0, min(1.0, float(temperature)))

        if max_tokens is not None:
            state["max_tokens"] = max(256, min(16384, int(max_tokens)))

        _save_state(state)
        global _RUNTIME_AI_STATE
        _RUNTIME_AI_STATE = state

    return get_ai_providers_state()
