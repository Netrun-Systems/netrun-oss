"""
Configuration exceptions for netrun-config.

Provides custom exception types for configuration validation and loading errors.
"""

# Optional netrun-errors integration
_use_netrun_errors = False
try:
    from netrun_errors import (
        ServiceUnavailableError as NetrunServiceUnavailableError,
        ValidationError as NetrunValidationError,
    )

    _use_netrun_errors = True
except ImportError:
    pass


class ConfigError(Exception):
    """Base exception for configuration errors."""

    pass


class ValidationError(ConfigError):
    """Exception raised when configuration validation fails."""

    pass


class KeyVaultError(ConfigError):
    """Exception raised when Azure Key Vault operations fail."""

    pass


# Standardized error factory functions
def raise_validation_error(message: str, field: str = None, **kwargs) -> None:
    """
    Raise configuration validation error using netrun-errors if available.

    Args:
        message: Error message
        field: Field name that failed validation
        **kwargs: Additional context for error reporting

    Raises:
        NetrunValidationError if netrun-errors installed, else ValidationError
    """
    context = {"field": field, **kwargs} if field else kwargs

    if _use_netrun_errors:
        raise NetrunValidationError(
            message=message,
            context=context,
            details={"package": "netrun-config", "validation_type": "config"},
        )
    else:
        raise ValidationError(f"{message} (field: {field})" if field else message)


def raise_keyvault_unavailable(vault_url: str, error: Exception, **kwargs) -> None:
    """
    Raise Key Vault unavailable error using netrun-errors if available.

    Args:
        vault_url: Key Vault URL that failed
        error: Original exception
        **kwargs: Additional context for error reporting

    Raises:
        NetrunServiceUnavailableError if netrun-errors installed, else KeyVaultError
    """
    message = f"Azure Key Vault unavailable: {vault_url}"
    context = {"vault_url": vault_url, "original_error": str(error), **kwargs}

    if _use_netrun_errors:
        raise NetrunServiceUnavailableError(
            message=message,
            service_name="Azure Key Vault",
            context=context,
            details={
                "package": "netrun-config",
                "vault_url": vault_url,
                "error_type": type(error).__name__,
            },
        )
    else:
        raise KeyVaultError(f"{message}: {error}")
