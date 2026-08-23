"""Domain exceptions translated into useful MCP tool errors."""


class CampusIntelError(Exception):
    """Base error safe to surface to an MCP client."""


class ConfigurationError(CampusIntelError):
    """Raised when a required integration is not configured."""


class UpstreamAPIError(CampusIntelError):
    """Raised when an upstream data provider cannot satisfy a request."""


class NotFoundError(CampusIntelError):
    """Raised when an entity cannot be found."""
