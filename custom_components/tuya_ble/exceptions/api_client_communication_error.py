"""Communication error raised by the API client."""

from __future__ import annotations

from .api_client_error import TuyaBleApiClientError


class TuyaBleApiClientCommunicationError(
    TuyaBleApiClientError,
):
    """Exception to indicate a communication error."""
