"""
Configurable LLM Provider Abstraction for ProcessMind AI.
Supports OpenAI API with rate limiting and exponential backoff retries,
plus a deterministic local Mock mode for reproducible execution without an API key.
"""

import json
import logging
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, Optional

from backend.config import settings

logger = logging.getLogger("processmind.llm_provider")


class SlidingWindowRateLimiter:
    """Enforces requests-per-minute (RPM) rate limits across LLM provider calls."""

    def __init__(self, max_rpm: int) -> None:
        self.max_rpm = max(1, max_rpm)
        self.timestamps: Deque[float] = deque()

    def acquire(self) -> None:
        now = time.monotonic()
        while self.timestamps and (now - self.timestamps[0]) >= 60.0:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.max_rpm:
            wait_for = max(0.01, 60.0 - (now - self.timestamps[0]))
            logger.warning("LLM rate limit reached (%d RPM). Throttling for %.2fs", self.max_rpm, wait_for)
            time.sleep(min(wait_for, 2.0))
        self.timestamps.append(time.monotonic())


class ConfigurableLLMProvider:
    """
    Enterprise LLM Provider Abstraction.
    - Supports OpenAI Chat Completions with JSON structured responses.
    - Provides deterministic local Mock execution when LLM_PROVIDER='mock' or no API key is set.
    - Includes automatic retry handling with exponential backoff and rate limiting.
    """

    def __init__(self) -> None:
        self.rate_limiter = SlidingWindowRateLimiter(settings.llm_rate_limit_rpm)
        self.max_retries = settings.llm_max_retries
        self.base_delay = settings.llm_retry_base_delay_seconds

    @property
    def active_provider_name(self) -> str:
        return settings.effective_llm_provider

    def execute_with_retry(
        self,
        operation_name: str,
        fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Executes an operation with rate limiting and bounded exponential backoff retries."""
        self.rate_limiter.acquire()
        last_err: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return fn()
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "LLM operation '%s' failed on attempt %d/%d: %s",
                    operation_name,
                    attempt,
                    self.max_retries,
                    str(exc),
                )
                if attempt < self.max_retries:
                    sleep_time = self.base_delay * (2 ** (attempt - 1))
                    time.sleep(sleep_time)

        raise RuntimeError(
            f"LLM operation '{operation_name}' failed after {self.max_retries} attempts: {last_err}"
        ) from last_err

    def invoke_structured_extraction(
        self,
        system_prompt: str,
        user_prompt: str,
        deterministic_fallback_fn: Callable[[], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calls OpenAI API when configured (`LLM_PROVIDER=openai` and `OPENAI_API_KEY` set),
        or executes deterministic rule-guided extraction when running in local mock mode.
        """
        if self.active_provider_name == "mock":
            return self.execute_with_retry("deterministic_mock_extraction", deterministic_fallback_fn)

        def _call_openai() -> Dict[str, Any]:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw_content = response.choices[0].message.content or "{}"
            return json.loads(raw_content)

        try:
            return self.execute_with_retry("openai_structured_extraction", _call_openai)
        except Exception as exc:
            logger.error("OpenAI API call failed (%s); falling back to deterministic engine.", str(exc))
            return deterministic_fallback_fn()


llm_provider = ConfigurableLLMProvider()
