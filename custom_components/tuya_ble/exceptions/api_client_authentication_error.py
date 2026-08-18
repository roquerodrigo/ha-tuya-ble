"""Authentication error raised by the API client."""

from __future__ import annotations

from .api_client_error import TuyaBleApiClientError


class TuyaBleApiClientAuthenticationError(
    TuyaBleApiClientError,
):
    """Exception to indicate an authentication error."""
