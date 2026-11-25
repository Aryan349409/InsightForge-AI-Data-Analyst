"""Thin provider-agnostic LLM client.

Supports:
  * anthropic  - Claude via the Anthropic API
  * openai     - OpenAI, or ANY OpenAI-compatible server (e.g. Ollama at
                 http://localhost:11434/v1) for a free, fully local setup
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


@dataclass
class LLMClient:
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama"))
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    last_latency: float = 0.0

    def __post_init__(self):
        self.provider = self.provider.lower()
        if self.provider == "anthropic":
            self.model = self.model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
            self.api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        elif self.provider == "ollama":
            self.model = self.model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
            self.api_key = "ollama"
            self.base_url = "http://127.0.0.1:11434/v1"
        elif self.provider == "openai":
            self.model = self.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            self.base_url = self.base_url or os.getenv("OPENAI_BASE_URL")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, user: str, max_tokens: int = 1500,
                 temperature: float = 0.0) -> str:
        if not self.available:
            raise RuntimeError("No API key configured for the selected LLM provider.")
        start = time.perf_counter()
        if self.provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            resp = client.messages.create(
                model=self.model, max_tokens=max_tokens, temperature=temperature,
                system=system, messages=[{"role": "user", "content": user}],
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        else:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            resp = client.chat.completions.create(
                model=self.model, max_tokens=max_tokens, temperature=temperature,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
            )
            text = resp.choices[0].message.content or ""
        self.last_latency = time.perf_counter() - start
        return text.strip()
