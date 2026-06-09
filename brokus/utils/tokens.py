"""Token counting utility for estimating AI costs."""

import tiktoken


class TokenCounter:
    """Estimates token counts for different models."""

    # Approximate tokens per word (varies by language; German ~1.5-2)
    TOKENS_PER_WORD_GERMAN = 1.8
    TOKENS_PER_WORD_ENGLISH = 1.3

    def __init__(self, model: str = "gpt-4"):
        self.model = model
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        try:
            return len(self.encoding.encode(text))
        except Exception:
            return self.estimate(text)

    def estimate(self, text: str) -> int:
        """Estimate tokens from word count (fallback)."""
        words = len(text.split())
        return int(words * self.TOKENS_PER_WORD_GERMAN)

    def estimate_cost(self, token_count: int, model: str | None = None) -> float:
        """Estimate cost in USD based on model pricing."""
        model = model or self.model
        pricing = {
            "gpt-4o": (0.0025, 0.01),       # input, output per 1K tokens
            "gpt-4-turbo": (0.01, 0.03),
            "claude-sonnet-4-20250514": (0.003, 0.015),
            "claude-3-opus": (0.015, 0.075),
        }
        input_price, output_price = pricing.get(model, (0.003, 0.015))
        return (token_count / 1000) * output_price
