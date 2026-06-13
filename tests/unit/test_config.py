import os
import pytest
from sentry_adapter.config import load_config, Config


def _write_yaml(tmp_path, content):
    f = tmp_path / "adapter.yaml"
    f.write_text(content)
    return str(f)


def test_load_minimal_config(tmp_path):
    path = _write_yaml(tmp_path, """
sentry:
  auth_token: tok-123
  organization: my-org
auth:
  keys:
    - id: k1
      key: sk-abc
""")
    cfg = load_config(path)
    assert cfg.sentry.organization == "my-org"
    assert cfg.sentry.auth_token == "tok-123"
    assert cfg.auth.keys[0].id == "k1"
    assert cfg.server.port == 8090
    assert cfg.sanitizer.entities == ["EMAIL_ADDRESS", "IP_ADDRESS"]
    assert cfg.audit.type == "stdout"


def test_env_interpolation(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "secret-xyz")
    path = _write_yaml(tmp_path, """
sentry:
  auth_token: ${MY_TOKEN}
  organization: acme
auth:
  keys:
    - id: k1
      key: sk-1
""")
    cfg = load_config(path)
    assert cfg.sentry.auth_token == "secret-xyz"


def test_env_interpolation_missing_var(tmp_path):
    path = _write_yaml(tmp_path, """
sentry:
  auth_token: ${MISSING_VAR}
  organization: acme
auth:
  keys:
    - id: k1
      key: sk-1
""")
    with pytest.raises(ValueError, match="MISSING_VAR"):
        load_config(path)


def test_file_audit_config(tmp_path):
    path = _write_yaml(tmp_path, """
sentry:
  auth_token: tok
  organization: acme
auth:
  keys:
    - id: k1
      key: sk-1
audit:
  type: file
  path: /tmp/audit.jsonl
""")
    cfg = load_config(path)
    assert cfg.audit.type == "file"
    assert cfg.audit.path == "/tmp/audit.jsonl"
