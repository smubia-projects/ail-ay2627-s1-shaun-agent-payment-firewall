"""Thin OpenAI-compatible client. Works with Anthropic, Groq, OpenAI, OpenRouter, Gemini, apiyi, etc.

Default settings: API_KEY, API_BASE_URL, MODEL_NAME (AI Lodge names), else the original LLM_API_KEY,
LLM_BASE_URL, LLM_MODEL. API_BASE_URL defaults to https://api.apiyi.com/v1 when any key is set.
Per-role overrides (so the agent and the intent judge can use different models):
  AGENT_API_KEY / AGENT_BASE_URL / AGENT_MODEL_NAME (or AGENT_MODEL)   -> the agent being protected
  JUDGE_API_KEY / JUDGE_BASE_URL / JUDGE_MODEL_NAME (or JUDGE_MODEL)   -> the firewall's intent judge
Any override not set falls back to the default value.
Optional, per role only (no LLM_* fallback, so it never leaks to another provider):
  AGENT_REASONING_EFFORT=none   e.g. for OpenAI reasoning models, which refuse tool calls on
                                /v1/chat/completions unless reasoning is off"""
import os


NEW_NAMES = {"API_KEY": "API_KEY", "BASE_URL": "API_BASE_URL", "MODEL": "MODEL_NAME"}
DEFAULT_BASE_URL = "https://api.apiyi.com/v1"


def _get(role, name, default=None):
    if role:
        for key in ([f"{role.upper()}_MODEL_NAME"] if name == "MODEL" else []) + [f"{role.upper()}_{name}"]:
            v = os.environ.get(key)
            if v:
                return v
    return os.environ.get(NEW_NAMES[name]) or os.environ.get(f"LLM_{name}") or default


def available(role=None):
    return bool(_get(role, "API_KEY"))


def client(role=None):
    from openai import OpenAI
    return OpenAI(api_key=_get(role, "API_KEY"), base_url=_get(role, "BASE_URL", DEFAULT_BASE_URL))


# Club default for text is deepseek-v4-1-flash-260910. The intent judge keeps Claude Haiku: its thresholds were calibrated on
# Haiku (calibration.json), so another judge model would change the firewall's evaluated verdicts.
DEFAULT_MODEL = "deepseek-v4-1-flash-260910"
DEFAULT_JUDGE_MODEL = "claude-haiku-4-5-20251001"


def model(role=None):
    return _get(role, "MODEL", DEFAULT_JUDGE_MODEL if role == "judge" else DEFAULT_MODEL)


def extra(role):
    """Extra request parameters for one role, e.g. {"reasoning_effort": "none"} from AGENT_REASONING_EFFORT.
    A DeepSeek model gets reasoning_effort "none" unless the role sets one: it thinks first by default, and a live
    attack runs the agent twice for up to AGENT_MAX_STEPS turns inside one request."""
    v = os.environ.get(f"{role.upper()}_REASONING_EFFORT") if role else None
    if not v and "deepseek" in model(role).lower():
        v = "none"
    return {"reasoning_effort": v} if v else {}
