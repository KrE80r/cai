"""
Anthropic OAuth provider for CAI.

Uses Claude Pro/Max subscription via OAuth instead of API key.
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Optional

from .interface import Model, ModelProvider
from .openai_chatcompletions import OpenAIChatCompletionsModel

if TYPE_CHECKING:
    from openai import AsyncOpenAI


class AnthropicOAuthProvider(ModelProvider):
    """
    Anthropic model provider using OAuth tokens (Claude Pro/Max subscription).
    
    This allows using Claude models without an API key by leveraging your
    Claude Pro or Max subscription.
    
    Usage:
        ```python
        from cai.sdk.agents.models import AnthropicOAuthProvider
        from cai.sdk.agents import Agent, Runner
        
        provider = AnthropicOAuthProvider()
        
        agent = Agent(
            name="my_agent",
            model=provider.get_model("claude-sonnet-4-20250514"),
        )
        
        result = await Runner.run(agent, "Hello!")
        ```
    """
    
    def __init__(
        self,
        *,
        credentials_path: Optional[str] = None,
    ) -> None:
        """
        Create a new Anthropic OAuth provider.
        
        Args:
            credentials_path: Path to OAuth credentials file (default: ~/.cai/oauth.json)
        """
        self._credentials_path = credentials_path
        self._client: Optional[AsyncOpenAI] = None
        self._token_lock = asyncio.Lock()
        self._current_token: Optional[str] = None
    
    async def _ensure_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        from ..oauth import get_valid_anthropic_token
        from pathlib import Path
        
        async with self._token_lock:
            path = Path(self._credentials_path) if self._credentials_path else None
            token = await get_valid_anthropic_token(path)
            
            if not token:
                raise RuntimeError(
                    "Not authenticated with Anthropic OAuth. "
                    "Run 'cai auth anthropic' to authenticate."
                )
            
            self._current_token = token
            return token
    
    def _get_client(self) -> "AsyncOpenAI":
        """Get or create the OpenAI client configured for Anthropic."""
        from openai import AsyncOpenAI
        
        if self._client is None:
            # Get token synchronously for initial setup
            # (will be refreshed async when needed)
            from ..oauth import load_anthropic_credentials
            from pathlib import Path
            
            path = Path(self._credentials_path) if self._credentials_path else None
            creds = load_anthropic_credentials(path)
            
            if not creds:
                raise RuntimeError(
                    "Not authenticated with Anthropic OAuth. "
                    "Run 'cai auth anthropic' to authenticate."
                )
            
            self._current_token = creds.access
            
            # Create client pointing to Anthropic API
            self._client = AsyncOpenAI(
                api_key=self._current_token,  # Use OAuth token as API key
                base_url="https://api.anthropic.com/v1",
                default_headers={
                    "anthropic-version": "2024-01-01",
                    "Authorization": f"Bearer {self._current_token}",
                },
            )
        
        return self._client
    
    def get_model(self, model_name: Optional[str] = None) -> Model:
        """
        Get a model instance for the given model name.
        
        Args:
            model_name: Model name (e.g., "claude-sonnet-4-20250514")
                       Defaults to "claude-sonnet-4-20250514"
        
        Returns:
            A Model instance configured for Anthropic OAuth
        """
        if model_name is None:
            model_name = "claude-sonnet-4-20250514"
        
        # Ensure model name has provider prefix for litellm
        if not model_name.startswith("claude/") and not model_name.startswith("anthropic/"):
            model_name = f"claude/{model_name}"
        
        client = self._get_client()
        
        # Use OpenAIChatCompletionsModel which handles Claude via litellm
        return OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=client,
        )


def get_anthropic_oauth_model(
    model_name: str = "claude-sonnet-4-20250514",
    credentials_path: Optional[str] = None,
) -> Model:
    """
    Convenience function to get an Anthropic OAuth model.
    
    Args:
        model_name: Model name (default: claude-sonnet-4-20250514)
        credentials_path: Path to OAuth credentials
        
    Returns:
        A Model instance configured for Anthropic OAuth
        
    Example:
        ```python
        from cai.sdk.agents.models import get_anthropic_oauth_model
        
        model = get_anthropic_oauth_model("claude-opus-4-20250514")
        ```
    """
    provider = AnthropicOAuthProvider(credentials_path=credentials_path)
    return provider.get_model(model_name)


# Environment variable support
def configure_anthropic_oauth_env():
    """
    Configure environment for Anthropic OAuth.
    
    This sets up the ANTHROPIC_API_KEY environment variable with the OAuth token,
    allowing litellm and other tools to use it automatically.
    """
    from ..oauth import load_anthropic_credentials
    
    creds = load_anthropic_credentials()
    if creds and not creds.is_expired():
        os.environ["ANTHROPIC_API_KEY"] = creds.access
        os.environ["ANTHROPIC_OAUTH_TOKEN"] = creds.access
        return True
    return False
