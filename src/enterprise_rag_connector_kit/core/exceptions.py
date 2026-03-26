from __future__ import annotations


class GleanIndexingConnectorError(Exception):
    """
    Base exception for the connector.
    """


class ConfigurationError(GleanIndexingConnectorError):
    """
    Raised when application configuration is invalid.
    """


class AdapterError(GleanIndexingConnectorError):
    """
    Raised when a source adapter cannot load or transform source data.
    """


class ValidationError(GleanIndexingConnectorError):
    """
    Raised when a normalized document fails validation.
    """


class GleanApiError(GleanIndexingConnectorError):
    """
    Base exception for Glean API communication failures.
    """


class RetryableGleanApiError(GleanApiError):
    """
    Represents a transient API/network failure that may succeed on retry.
    """


class PermanentGleanApiError(GleanApiError):
    """
    Represents a permanent API failure that should not be retried.
    """
