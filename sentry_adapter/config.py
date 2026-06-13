import os
import re
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field


def _interpolate_env(text: str) -> str:
    def replace(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(f"Environment variable '{var_name}' not set")
        return value
    return re.sub(r"\$\{([^}]+)\}", replace, text)


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8090


class SentryConfig(BaseModel):
    base_url: str = "https://sentry.io"
    auth_token: str
    organization: str
    timeout_seconds: int = 10


class AuthKeyConfig(BaseModel):
    id: str
    key: str
    user_id: str | None = None
    team_id: str | None = None


class AuthConfig(BaseModel):
    keys: list[AuthKeyConfig]


class SanitizerConfig(BaseModel):
    entities: list[str] = ["EMAIL_ADDRESS", "IP_ADDRESS"]
    secrets_regex: bool = True


class BodyLoggingConfig(BaseModel):
    enabled: bool = False


class StdoutAuditConfig(BaseModel):
    type: Literal["stdout"] = "stdout"
    body_logging: BodyLoggingConfig = BodyLoggingConfig()


class FileAuditConfig(BaseModel):
    type: Literal["file"]
    path: str
    body_logging: BodyLoggingConfig = BodyLoggingConfig()


AuditConfig = Annotated[
    StdoutAuditConfig | FileAuditConfig,
    Field(discriminator="type"),
]


class Config(BaseModel):
    server: ServerConfig = ServerConfig()
    sentry: SentryConfig
    auth: AuthConfig
    sanitizer: SanitizerConfig = SanitizerConfig()
    audit: AuditConfig = StdoutAuditConfig()


def load_config(path: str) -> Config:
    raw = Path(path).read_text()
    interpolated = _interpolate_env(raw)
    data = yaml.safe_load(interpolated)
    return Config.model_validate(data)
