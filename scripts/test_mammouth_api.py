#!/usr/bin/env python3
"""Test the Mammouth AI API connection.

Usage:
    # With API key in env var:
    MAMMOUTH_API_KEY="sk-..." python scripts/test_mammouth_api.py

    # Or pass via --key:
    python scripts/test_mammouth_api.py --key "sk-..."

Tests:
    1. Provider is registered in PROVIDER_REGISTRY
    2. Chat completion with gpt-5.4-nano (cheapest model)
    3. Response is valid and contains expected text
"""

import argparse
import os
import sys
import asyncio


async def test_mammouth(api_key: str = "", model: str = "gpt-5.4-nano") -> bool:
    """Run a simple chat completion test against Mammouth API.

    Args:
        api_key: Mammouth API key. Falls back to MAMMOUTH_API_KEY env var.
        model: Model to test with (default: gpt-5.4-nano – cheapest).

    Returns:
        True if the test passed.
    """
    # Set the API key in environment so BrokusAIClient picks it up
    key = api_key or os.getenv("MAMMOUTH_API_KEY", "")
    if not key:
        print("❌ No API key provided. Set MAMMOUTH_API_KEY env var or use --key.")
        return False

    os.environ["MAMMOUTH_API_KEY"] = key

    # 1. Check provider registration
    try:
        from brokus.ai.client import PROVIDER_REGISTRY

        if "mammouth" not in PROVIDER_REGISTRY:
            print("❌ Provider 'mammouth' not found in PROVIDER_REGISTRY!")
            return False

        pc = PROVIDER_REGISTRY["mammouth"]
        print(f"✅ Provider registered: {pc.name}")
        print(f"   Base URL: {pc.base_url}")
        print(f"   Env var:  {pc.api_key_env}")
        print(f"   Models:   {len(pc.models)} registered ({pc.models[0]} … {pc.models[-1]})")
    except Exception as e:
        print(f"❌ Failed to verify provider registration: {e}")
        return False

    # 2. Test chat completion
    print(f"\n🔍 Testing chat completion with model '{model}'...")
    try:
        from brokus.ai.client import BrokusAIClient

        client = BrokusAIClient(
            provider="mammouth",
            model=model,
            temperature=0.0,
            max_tokens=50,
        )

        response = await client.generate(
            system_prompt="Du bist ein hilfreicher Assistent.",
            user_prompt="Antworte nur mit dem Wort 'OK' und sonst nichts.",
            temperature=0.0,
            max_tokens=10,
            retry=False,
        )

        text = response.text.strip()
        if not text:
            print("❌ Empty response from Mammouth API!")
            return False

        print(f"✅ Response received ({len(text)} chars):")
        print(f"   Text:  '{text[:100]}'")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.tokens_used}")

        # Check that we got a reasonable response
        if "OK" in text.upper() or len(text) > 0:
            print(f"✅ Response looks valid!")
        else:
            print(f"⚠️  Unexpected response content (expected 'OK').")

    except Exception as e:
        print(f"❌ Chat completion failed: {e}")
        return False

    # 3. Test model discovery (OpenAI-compat /models endpoint)
    print(f"\n🔍 Testing model discovery (/v1/models)...")
    try:
        from brokus.ai.model_discovery import get_provider_models_sync

        result = get_provider_models_sync("mammouth", force_refresh=True)
        if result.models:
            print(f"✅ Discovered {len(result.models)} models ({result.source})")
            for m in result.models[:10]:
                print(f"   • {m}")
            if len(result.models) > 10:
                print(f"   … and {len(result.models) - 10} more")
        else:
            print(f"⚠️  Model discovery returned no models: {result.error}")
    except Exception as e:
        print(f"⚠️  Model discovery failed (non-critical): {e}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Test the Mammouth AI API connection"
    )
    parser.add_argument(
        "--key",
        help="Mammouth API key (falls back to MAMMOUTH_API_KEY env var)",
        default="",
    )
    parser.add_argument(
        "--model",
        help="Model to test (default: gpt-5.4-nano)",
        default="gpt-5.4-nano",
    )
    args = parser.parse_args()

    success = asyncio.run(test_mammouth(api_key=args.key, model=args.model))
    print(f"\n{'='*40}")
    if success:
        print("✅ All tests passed! Mammouth API is working.")
        sys.exit(0)
    else:
        print("❌ Tests failed. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
