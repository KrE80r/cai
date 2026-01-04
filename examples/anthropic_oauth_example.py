"""
Example: Using Anthropic OAuth with CAI.

This example shows how to use your Claude Pro/Max subscription
instead of an API key for CAI agents.

Setup:
    1. Run `python -m cai.cli_oauth auth anthropic` to authenticate
    2. Run this example

The OAuth flow uses your Claude subscription for inference,
meaning no per-token API costs!
"""

import asyncio

from cai.sdk.agents import (
    Agent,
    Runner,
    AnthropicOAuthProvider,
    get_anthropic_oauth_model,
    configure_anthropic_oauth_env,
)


async def example_with_provider():
    """Example using AnthropicOAuthProvider directly."""
    print("=== Using AnthropicOAuthProvider ===\n")
    
    # Create provider (handles token refresh automatically)
    provider = AnthropicOAuthProvider()
    
    # Create agent with OAuth-backed model
    agent = Agent(
        name="oauth_agent",
        instructions="You are a helpful assistant. Be concise.",
        model=provider.get_model("claude-sonnet-4-20250514"),
    )
    
    # Run the agent
    result = await Runner.run(agent, "What is 2 + 2? Just give the number.")
    print(f"Response: {result.final_output}\n")


async def example_with_convenience_function():
    """Example using get_anthropic_oauth_model convenience function."""
    print("=== Using get_anthropic_oauth_model ===\n")
    
    # Get model directly
    model = get_anthropic_oauth_model("claude-sonnet-4-20250514")
    
    agent = Agent(
        name="convenience_agent",
        instructions="You are a helpful assistant. Be concise.",
        model=model,
    )
    
    result = await Runner.run(agent, "What is the capital of France? Just the city name.")
    print(f"Response: {result.final_output}\n")


async def example_with_env_config():
    """Example using environment variable configuration."""
    print("=== Using Environment Configuration ===\n")
    
    # Configure environment (sets ANTHROPIC_API_KEY from OAuth token)
    if configure_anthropic_oauth_env():
        print("OAuth token configured in environment.")
        
        # Now you can use any code that expects ANTHROPIC_API_KEY
        import os
        print(f"ANTHROPIC_API_KEY is set: {'ANTHROPIC_API_KEY' in os.environ}")
        print(f"Token prefix: {os.environ.get('ANTHROPIC_API_KEY', '')[:20]}...")
    else:
        print("Not authenticated. Run 'cai auth anthropic' first.")


async def example_multi_agent():
    """Example with multiple agents using OAuth."""
    print("=== Multi-Agent with OAuth ===\n")
    
    provider = AnthropicOAuthProvider()
    
    # Use different models for different agents
    planner = Agent(
        name="planner",
        instructions="You create plans. Be brief.",
        model=provider.get_model("claude-sonnet-4-20250514"),  # Faster, cheaper
    )
    
    executor = Agent(
        name="executor", 
        instructions="You execute plans. Be thorough.",
        model=provider.get_model("claude-opus-4-20250514"),  # More capable
        handoffs=[],
    )
    
    # Run planner
    plan_result = await Runner.run(planner, "Plan how to make coffee in 3 steps.")
    print(f"Plan: {plan_result.final_output}\n")


async def main():
    """Run all examples."""
    try:
        await example_with_provider()
        await example_with_convenience_function()
        await example_with_env_config()
        await example_multi_agent()
    except RuntimeError as e:
        if "Not authenticated" in str(e):
            print(f"\n❌ {e}")
            print("\nTo authenticate, run:")
            print("  python -m cai.cli_oauth auth anthropic")
        else:
            raise


if __name__ == "__main__":
    asyncio.run(main())
