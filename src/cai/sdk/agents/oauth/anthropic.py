"""
Anthropic OAuth flow (Claude Pro/Max subscription).

This allows using Claude API with your Pro/Max subscription instead of paying per-token.
Ported from Clawdis/pi-ai TypeScript implementation.
"""

import base64
import json
import os
import time
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlencode

import httpx

from .pkce import generate_pkce
from .types import OAuthCredentials


# Anthropic OAuth constants (from pi-ai)
CLIENT_ID = base64.b64decode("OWQxYzI1MGEtZTYxYi00NGQ5LTg4ZWQtNTk0NGQxOTYyZjVl").decode()
AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"
SCOPES = "org:create_api_key user:profile user:inference"

# Default credentials path
DEFAULT_CREDENTIALS_PATH = Path.home() / ".cai" / "oauth.json"


async def login_anthropic(
    on_auth_url: Callable[[str], None],
    on_prompt_code: Callable[[], str],
) -> OAuthCredentials:
    """
    Login with Anthropic OAuth (device code flow).
    
    This uses your Claude Pro/Max subscription for API access.
    
    Args:
        on_auth_url: Callback to handle the authorization URL (e.g., open browser, print)
        on_prompt_code: Callback to prompt user for the authorization code
        
    Returns:
        OAuth credentials with access and refresh tokens
        
    Example:
        ```python
        import webbrowser
        
        def open_url(url):
            print(f"Open this URL: {url}")
            webbrowser.open(url)
            
        def get_code():
            return input("Paste the code from the browser: ")
            
        creds = await login_anthropic(open_url, get_code)
        ```
    """
    verifier, challenge = generate_pkce()
    
    # Build authorization URL
    auth_params = {
        "code": "true",
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": verifier,
    }
    auth_url = f"{AUTHORIZE_URL}?{urlencode(auth_params)}"
    
    # Notify caller with URL to open
    on_auth_url(auth_url)
    
    # Wait for user to paste authorization code (format: code#state)
    auth_code = on_prompt_code()
    
    # Parse code and state
    if "#" in auth_code:
        code, state = auth_code.split("#", 1)
    else:
        code = auth_code
        state = verifier  # Assume same state if not provided
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "state": state,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
        )
        
        if not response.is_success:
            raise RuntimeError(f"Token exchange failed: {response.text}")
        
        token_data = response.json()
    
    # Calculate expiry time (current time + expires_in seconds - 5 min buffer)
    expires_at = int(time.time() * 1000) + (token_data["expires_in"] * 1000) - (5 * 60 * 1000)
    
    return OAuthCredentials(
        refresh=token_data["refresh_token"],
        access=token_data["access_token"],
        expires=expires_at,
    )


async def refresh_anthropic_token(refresh_token: str) -> OAuthCredentials:
    """
    Refresh Anthropic OAuth token.
    
    Args:
        refresh_token: The refresh token from previous authentication
        
    Returns:
        New OAuth credentials with fresh access token
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/json"},
            json={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": refresh_token,
            },
        )
        
        if not response.is_success:
            raise RuntimeError(f"Anthropic token refresh failed: {response.text}")
        
        data = response.json()
    
    return OAuthCredentials(
        refresh=data.get("refresh_token", refresh_token),
        access=data["access_token"],
        expires=int(time.time() * 1000) + (data["expires_in"] * 1000) - (5 * 60 * 1000),
    )


def load_anthropic_credentials(path: Optional[Path] = None) -> Optional[OAuthCredentials]:
    """
    Load Anthropic OAuth credentials from disk.
    
    Args:
        path: Path to credentials file (default: ~/.cai/oauth.json)
        
    Returns:
        OAuth credentials if found and valid, None otherwise
    """
    creds_path = path or DEFAULT_CREDENTIALS_PATH
    
    if not creds_path.exists():
        # Also check legacy paths
        legacy_paths = [
            Path.home() / ".claude" / "oauth.json",
            Path.home() / ".config" / "claude" / "oauth.json",
            Path.home() / ".config" / "anthropic" / "oauth.json",
            Path.home() / ".clawdis" / "credentials" / "oauth.json",
        ]
        for legacy in legacy_paths:
            if legacy.exists():
                creds_path = legacy
                break
        else:
            return None
    
    try:
        with open(creds_path) as f:
            data = json.load(f)
        
        # Handle both direct format and nested "anthropic" key
        if "anthropic" in data:
            data = data["anthropic"]
        
        if not data.get("refresh") and not data.get("refresh_token"):
            return None
            
        return OAuthCredentials.from_dict(data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def save_anthropic_credentials(
    credentials: OAuthCredentials,
    path: Optional[Path] = None,
) -> None:
    """
    Save Anthropic OAuth credentials to disk.
    
    Args:
        credentials: OAuth credentials to save
        path: Path to credentials file (default: ~/.cai/oauth.json)
    """
    creds_path = path or DEFAULT_CREDENTIALS_PATH
    creds_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    # Store under "anthropic" key for compatibility
    data = {"anthropic": credentials.to_dict()}
    
    with open(creds_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # Secure the file
    os.chmod(creds_path, 0o600)


async def get_valid_anthropic_token(path: Optional[Path] = None) -> Optional[str]:
    """
    Get a valid Anthropic access token, refreshing if necessary.
    
    Args:
        path: Path to credentials file
        
    Returns:
        Valid access token, or None if not authenticated
    """
    creds = load_anthropic_credentials(path)
    if not creds:
        return None
    
    # Refresh if expired
    if creds.is_expired():
        try:
            creds = await refresh_anthropic_token(creds.refresh)
            save_anthropic_credentials(creds, path)
        except Exception:
            return None
    
    return creds.access
