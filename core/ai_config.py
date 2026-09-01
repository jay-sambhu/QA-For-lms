"""
Multi-AI Provider Configuration & Dynamic Engine Router for JASUSS (Powered by Nexus)
Supports Google Gemini, OpenAI, Anthropic Claude, DeepSeek, and Local LLM endpoints.
"""

import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

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
        models=["gemini-2.5-flash", "gemini-1.5-pro", "gemini-3-flash-preview", "gemini-1.5-flash"],
        default_model="gemini-2.5-flash",
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

# In-memory runtime active AI configuration state
_RUNTIME_AI_STATE: Dict[str, Any] = {
    "active_provider": "gemini",
    "active_model": "gemini-2.5-flash",
    "temperature": 0.2,
    "max_tokens": 4096,
    "custom_endpoints": {
        "deepseek": "https://api.deepseek.com/v1",
        "local_llm": "http://localhost:11434/v1",
    },
    "custom_keys": {},
}

def get_ai_providers_state() -> Dict[str, Any]:
    """Return complete list of providers with configuration and active status."""
    providers_list = []
    for pid, pmeta in AI_PROVIDERS_REGISTRY.items():
        # Check if environment or custom key exists
        env_val = os.environ.get(pmeta.env_key_name) or _RUNTIME_AI_STATE["custom_keys"].get(pid)
        is_conf = bool(env_val and len(str(env_val).strip()) > 3)
        
        # Mask key for safety
        masked_key = ""
        if is_conf and env_val:
            key_str = str(env_val).strip()
            masked_key = f"{key_str[:4]}...{key_str[-4:]}" if len(key_str) >= 8 else "****"

        p_dict = pmeta.dict()
        p_dict["is_configured"] = is_conf
        p_dict["masked_key"] = masked_key
        p_dict["current_endpoint"] = _RUNTIME_AI_STATE["custom_endpoints"].get(pid, pmeta.default_endpoint)
        providers_list.append(p_dict)

    return {
        "active_provider": _RUNTIME_AI_STATE["active_provider"],
        "active_model": _RUNTIME_AI_STATE["active_model"],
        "temperature": _RUNTIME_AI_STATE["temperature"],
        "max_tokens": _RUNTIME_AI_STATE["max_tokens"],
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
    """Update runtime active provider, model, API keys, or custom endpoint."""
    if provider_id not in AI_PROVIDERS_REGISTRY:
        raise ValueError(f"Unknown AI provider: {provider_id}")

    _RUNTIME_AI_STATE["active_provider"] = provider_id

    if model:
        _RUNTIME_AI_STATE["active_model"] = model
    else:
        _RUNTIME_AI_STATE["active_model"] = AI_PROVIDERS_REGISTRY[provider_id].default_model

    if api_key and api_key.strip():
        _RUNTIME_AI_STATE["custom_keys"][provider_id] = api_key.strip()
        # Also set in env for compatibility
        os.environ[AI_PROVIDERS_REGISTRY[provider_id].env_key_name] = api_key.strip()

    if endpoint and endpoint.strip():
        _RUNTIME_AI_STATE["custom_endpoints"][provider_id] = endpoint.strip()

    if temperature is not None:
        _RUNTIME_AI_STATE["temperature"] = max(0.0, min(1.0, float(temperature)))

    if max_tokens is not None:
        _RUNTIME_AI_STATE["max_tokens"] = max(256, min(16384, int(max_tokens)))

    return get_ai_providers_state()
