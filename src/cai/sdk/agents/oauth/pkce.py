"""
PKCE utilities for OAuth flows.
"""

import base64
import hashlib
import secrets


def generate_pkce() -> tuple[str, str]:
    """
    Generate PKCE code verifier and challenge.
    
    Returns:
        Tuple of (verifier, challenge)
    """
    # Generate random verifier (32 bytes -> 43 chars base64url)
    verifier_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")
    
    # Compute SHA-256 challenge
    challenge_bytes = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b"=").decode("ascii")
    
    return verifier, challenge
