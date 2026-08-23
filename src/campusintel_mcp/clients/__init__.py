"""Clients for CampusIntel's authoritative upstream data sources."""

from campusintel_mcp.clients.openalex import OpenAlexClient
from campusintel_mcp.clients.scorecard import CollegeScorecardClient

__all__ = ["CollegeScorecardClient", "OpenAlexClient"]
