import os
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP

from sentry_adapter.api.auth import AuthMiddleware
from sentry_adapter.api.tools import register_tools
from sentry_adapter.application.sentry_service import SentryService
from sentry_adapter.config import Config, FileAuditConfig, load_config
from sentry_adapter.infrastructure.audit.file_backend import FileAuditBackend
from sentry_adapter.infrastructure.audit.stdout_backend import StdoutAuditBackend
from sentry_adapter.infrastructure.presidio_sanitizer import PresidioSanitizer
from sentry_adapter.infrastructure.sentry_client import SentryClient


def create_app(config_path: str | None = None) -> Any:
    """Factory function — used in tests and by the run() entry point."""
    config_path = config_path or os.environ.get("ADAPTER_CONFIG", "adapter.yaml")
    config = load_config(config_path)
    return _build_app(config)


def _build_app(config: Config) -> Any:
    client = SentryClient(
        base_url=config.sentry.base_url,
        auth_token=config.sentry.auth_token,
        organization=config.sentry.organization,
        timeout=config.sentry.timeout_seconds,
    )
    sanitizer = PresidioSanitizer(
        entities=config.sanitizer.entities,
        secrets_regex=config.sanitizer.secrets_regex,
    )
    audit = (
        FileAuditBackend(path=config.audit.path)
        if isinstance(config.audit, FileAuditConfig)
        else StdoutAuditBackend()
    )
    service = SentryService(
        client=client,
        sanitizer=sanitizer,
        audit=audit,
        log_body=config.audit.body_logging.enabled,
    )

    mcp = FastMCP("sentry-adapter")
    register_tools(mcp, service)

    key_index = {k.key: k for k in config.auth.keys}

    # Get ASGI app from FastMCP and add auth middleware
    # streamable_http_app() is the modern HTTP transport (mcp >= 1.0)
    # Falls back to sse_app() for older versions
    try:
        app = mcp.streamable_http_app()
    except AttributeError:
        app = mcp.sse_app()

    app.add_middleware(AuthMiddleware, key_index=key_index)
    return app


def run() -> None:
    """CLI entry point: sentry-adapter command."""
    config_path = os.environ.get("ADAPTER_CONFIG", "adapter.yaml")
    config = load_config(config_path)
    app = _build_app(config)
    uvicorn.run(app, host=config.server.host, port=config.server.port)
