"""
OAuth types for CAI.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OAuthCredentials:
    """OAuth credentials with token refresh support."""
    
    refresh: str
    access: str
    expires: int  # Unix timestamp in milliseconds
    email: Optional[str] = None
    
    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        """Check if the access token is expired (with buffer)."""
        import time
        return (time.time() * 1000) >= (self.expires - buffer_ms)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "refresh": self.refresh,
            "access": self.access,
            "expires": self.expires,
            "email": self.email,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OAuthCredentials":
        """Create from dictionary."""
        return cls(
            refresh=data.get("refresh", data.get("refresh_token", "")),
            access=data.get("access", data.get("access_token", "")),
            expires=data.get("expires", 0),
            email=data.get("email"),
        )
