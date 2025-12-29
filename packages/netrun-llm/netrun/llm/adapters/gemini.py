"""
Google Gemini API Adapter for netrun-llm package

Provides free-tier Gemini integration with daily quota tracking.
Extracted from Charlotte production architecture.

Features:
    - Free tier support (1,500 requests/day with quota tracking)
    - Multiple model support (Pro, Flash, Experimental)
    - Circuit breaker protection
    - Cost estimation and tracking
    - Automatic quota management

Author: Netrun Systems
Version: 2.0.0
License: MIT
"""

import os
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    from google.api_core import exceptions as google_exceptions
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    GenerationConfig = None

from .base import BaseLLMAdapter, AdapterTier, LLMResponse


# Pricing constants (USD per million tokens, 2025)
PRICING = {
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash-exp": {"input": 0.00, "output": 0.00},  # Experimental (free)
}

# Default model if not specified
DEFAULT_MODEL = "gemini-1.5-flash"

# Default max tokens for responses
DEFAULT_MAX_TOKENS = 2048

# Free tier limits
FREE_TIER_DAILY_LIMIT = 1500  # requests per day
FREE_TIER_QUOTA_FILE = ".gemini_quota.json"


class GeminiAdapter(BaseLLMAdapter):
    """
    Google Gemini API adapter with free tier quota tracking.

    Features:
        - Tier 1 (API) reliability
        - Free tier support (1,500 req/day quota tracking)
        - Circuit breaker protection
        - Cost estimation and tracking
        - Support for gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp

    Environment Variables:
        GEMINI_API_KEY: Google AI API key
        GEMINI_DEFAULT_MODEL: Default model (default: gemini-1.5-flash)
        GEMINI_MAX_TOKENS: Max output tokens (default: 2048)
        GEMINI_TIMEOUT: Request timeout in seconds (default: 30)
        GEMINI_QUOTA_FILE: Quota tracking file path (default: .gemini_quota.json)
        GEMINI_USE_FREE_TIER: Enable quota tracking (default: true)

    Example:
        >>> adapter = GeminiAdapter(use_free_tier=True)
        >>> response = adapter.execute("Explain quantum computing in 3 sentences")
        >>> print(response.content)
        >>> print(f"Quota remaining: {response.metadata['quota_remaining']}")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_free_tier: bool = True,
        model: str = None,
        timeout: int = None,
        quota_file_path: str = None
    ):
        """
        Initialize Gemini adapter.

        Args:
            api_key: Google AI API key (default: from GEMINI_API_KEY env)
            use_free_tier: Use free tier with quota tracking (default: True)
            model: Default model to use (default: gemini-1.5-flash)
            timeout: Request timeout in seconds (default: 30)
            quota_file_path: Custom path for quota tracking file

        Raises:
            ImportError: If google-generativeai SDK not installed
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "Gemini support requires google-generativeai SDK. "
                "Install with: pip install 'netrun-llm[gemini]'"
            )

        super().__init__(
            adapter_name="Gemini-API",
            tier=AdapterTier.API,
            reliability_score=1.0  # API tier has highest reliability
        )

        self.use_free_tier = use_free_tier

        # Load configuration from environment or use defaults
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.default_model = model or os.getenv("GEMINI_DEFAULT_MODEL", DEFAULT_MODEL)
        self.max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        self.timeout = timeout or int(os.getenv("GEMINI_TIMEOUT", "30"))

        # Quota tracking setup
        if quota_file_path:
            self.quota_file = Path(quota_file_path)
        else:
            self.quota_file = Path(os.getenv("GEMINI_QUOTA_FILE", FREE_TIER_QUOTA_FILE))

        # Load or initialize quota data
        self.quota_data = self._load_quota_data()

        # Configure Gemini API
        if self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            self.enabled = False

    def _load_quota_data(self) -> Dict[str, Any]:
        """Load quota tracking data from file"""
        if not self.quota_file.exists():
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "requests_today": 0,
            }

        try:
            with open(self.quota_file, "r") as f:
                data = json.load(f)

            # Reset counter if new day
            current_date = datetime.now().strftime("%Y-%m-%d")
            if data.get("date") != current_date:
                data["date"] = current_date
                data["requests_today"] = 0

            return data
        except (json.JSONDecodeError, IOError):
            # Corrupted file - reset
            return {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "requests_today": 0,
            }

    def _save_quota_data(self) -> None:
        """Save quota tracking data to file"""
        try:
            with open(self.quota_file, "w") as f:
                json.dump(self.quota_data, f, indent=2)
        except IOError:
            pass  # Quota tracking is optional, don't fail on save errors

    def _check_quota(self) -> bool:
        """Check if quota allows request"""
        if not self.use_free_tier:
            return True  # No quota limits on paid tier

        # Reload quota data (in case multiple processes)
        self.quota_data = self._load_quota_data()

        return self.quota_data["requests_today"] < FREE_TIER_DAILY_LIMIT

    def _increment_quota(self) -> None:
        """Increment quota counter and save"""
        if not self.use_free_tier:
            return

        self.quota_data["requests_today"] += 1
        self._save_quota_data()

    def execute(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> LLMResponse:
        """
        Execute prompt using Gemini API.

        Args:
            prompt: The prompt/instruction to send to Gemini
            context: Optional context with parameters:
                - model (str): Override default model
                - max_tokens (int): Override default max tokens
                - temperature (float): Sampling temperature (0.0-2.0)
                - top_p (float): Nucleus sampling threshold (0.0-1.0)
                - top_k (int): Top-k sampling parameter

        Returns:
            LLMResponse with status, content, cost, latency, and metadata

        Example:
            >>> adapter = GeminiAdapter()
            >>> response = adapter.execute(
            ...     "Write a haiku about AI",
            ...     context={"temperature": 0.7}
            ... )
            >>> print(response.content)
        """
        # Check circuit breaker before attempting request
        if self._check_circuit_breaker():
            return self._create_error_response(
                "Circuit breaker open (too many failures)"
            )

        # Check quota before attempting request
        if not self._check_quota():
            return LLMResponse(
                status="rate_limited",
                error=f"Free tier quota exceeded ({FREE_TIER_DAILY_LIMIT} requests/day). "
                      f"Quota resets at midnight UTC.",
                adapter_name=self.adapter_name,
                metadata={
                    "quota_exceeded": True,
                    "requests_today": self.quota_data["requests_today"],
                    "daily_limit": FREE_TIER_DAILY_LIMIT,
                }
            )

        # Extract context parameters
        context = context or {}
        model = context.get("model", self.default_model)
        max_tokens = context.get("max_tokens", self.max_tokens)
        temperature = context.get("temperature", 1.0)
        top_p = context.get("top_p", 0.95)
        top_k = context.get("top_k", 40)

        # Start timing
        start_time = time.time()

        try:
            # Create model instance
            gemini_model = genai.GenerativeModel(model_name=model)

            # Configure generation parameters
            generation_config = GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_output_tokens=max_tokens
            )

            # Make API request
            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config,
                request_options={"timeout": self.timeout}
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response text
            result_text = response.text

            # Get token usage (if available)
            tokens_input = 0
            tokens_output = 0

            if hasattr(response, "usage_metadata"):
                tokens_input = response.usage_metadata.prompt_token_count or 0
                tokens_output = response.usage_metadata.candidates_token_count or 0

            # Calculate actual cost
            cost_usd = self._calculate_actual_cost(model, tokens_input, tokens_output)

            # Increment quota counter
            self._increment_quota()

            # Record success
            self._record_success(latency_ms, cost_usd)

            return LLMResponse(
                status="success",
                content=result_text,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                adapter_name=self.adapter_name,
                model_used=model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                metadata={
                    "use_free_tier": self.use_free_tier,
                    "requests_today": self.quota_data["requests_today"],
                    "quota_remaining": FREE_TIER_DAILY_LIMIT - self.quota_data["requests_today"]
                        if self.use_free_tier else "unlimited",
                    "finish_reason": response.candidates[0].finish_reason.name
                        if response.candidates else "unknown"
                }
            )

        except google_exceptions.ResourceExhausted as e:
            self._record_failure()
            latency_ms = int((time.time() - start_time) * 1000)

            return self._create_error_response(
                f"Rate limit or quota exceeded: {str(e)}",
                status="rate_limited",
                latency_ms=latency_ms,
                model=model
            )

        except google_exceptions.InvalidArgument as e:
            self._record_failure()
            latency_ms = int((time.time() - start_time) * 1000)

            return self._create_error_response(
                f"Invalid request: {str(e)}",
                latency_ms=latency_ms,
                model=model
            )

        except google_exceptions.Unauthenticated as e:
            self._record_failure()
            latency_ms = int((time.time() - start_time) * 1000)

            return self._create_error_response(
                f"Authentication error: {str(e)}",
                latency_ms=latency_ms,
                model=model
            )

        except Exception as e:
            self._record_failure()
            latency_ms = int((time.time() - start_time) * 1000)

            return self._create_error_response(
                f"Unexpected error: {str(e)}",
                latency_ms=latency_ms,
                model=model
            )

    async def execute_async(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """Async execution - currently wraps sync implementation"""
        return self.execute(prompt, context)

    def estimate_cost(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Estimate cost (in USD) before executing prompt.

        Args:
            prompt: The prompt/instruction
            context: Optional context with 'model' and 'max_tokens'

        Returns:
            Estimated cost in USD (0.0 for free tier)
        """
        if self.use_free_tier:
            return 0.0  # Free tier = no cost

        context = context or {}
        model = context.get("model", self.default_model)
        max_tokens = context.get("max_tokens", self.max_tokens)

        # Simple token estimation: ~4 characters per token
        estimated_input_tokens = len(prompt) / 4
        estimated_output_tokens = max_tokens  # Assume full output

        return self._calculate_actual_cost(model, estimated_input_tokens, estimated_output_tokens)

    def check_availability(self) -> bool:
        """Check if Gemini API is available and healthy"""
        # Check base health (circuit breaker, enabled status)
        if not self.is_healthy():
            return False

        # Check quota availability
        if self.use_free_tier and not self._check_quota():
            return False

        return True

    def get_metadata(self) -> Dict[str, Any]:
        """Return adapter configuration and current status"""
        metadata = {
            "name": self.adapter_name,
            "tier": self.tier.name,
            "reliability_score": self.reliability_score,
            "enabled": self.enabled,
            "default_model": self.default_model,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "use_free_tier": self.use_free_tier,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": self.get_success_rate(),
            "avg_latency_ms": self.get_average_latency(),
            "total_cost_usd": self._total_cost_usd,
            "circuit_breaker_open": self._circuit_breaker_open,
            "supported_models": list(PRICING.keys())
        }

        # Add quota information if using free tier
        if self.use_free_tier:
            metadata["quota"] = {
                "date": self.quota_data["date"],
                "requests_today": self.quota_data["requests_today"],
                "requests_remaining": FREE_TIER_DAILY_LIMIT - self.quota_data["requests_today"],
                "daily_limit": FREE_TIER_DAILY_LIMIT,
                "quota_percentage_used": round(
                    (self.quota_data["requests_today"] / FREE_TIER_DAILY_LIMIT) * 100, 1
                )
            }

        return metadata

    def _calculate_actual_cost(
        self, model: str, input_tokens: float, output_tokens: float
    ) -> float:
        """Calculate actual cost based on token usage and model pricing"""
        if self.use_free_tier:
            return 0.0  # Free tier = no cost

        if model not in PRICING:
            # Unknown model - use gemini-1.5-flash pricing as default
            model = DEFAULT_MODEL

        pricing = PRICING[model]

        # Calculate cost: (tokens / 1,000,000) * price_per_million
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def reset_quota(self) -> None:
        """Reset daily quota counter (for testing or manual reset)"""
        self.quota_data["date"] = datetime.now().strftime("%Y-%m-%d")
        self.quota_data["requests_today"] = 0
        self._save_quota_data()

    def get_quota_status(self) -> Dict[str, Any]:
        """Get current quota status"""
        if not self.use_free_tier:
            return {
                "tier": "paid",
                "quota_type": "unlimited",
                "requests_today": self._success_count
            }

        # Reload quota data to get latest
        self.quota_data = self._load_quota_data()

        return {
            "tier": "free",
            "quota_type": "daily",
            "date": self.quota_data["date"],
            "requests_today": self.quota_data["requests_today"],
            "requests_remaining": FREE_TIER_DAILY_LIMIT - self.quota_data["requests_today"],
            "daily_limit": FREE_TIER_DAILY_LIMIT,
            "quota_percentage_used": round(
                (self.quota_data["requests_today"] / FREE_TIER_DAILY_LIMIT) * 100, 1
            ),
            "quota_exceeded": self.quota_data["requests_today"] >= FREE_TIER_DAILY_LIMIT
        }
