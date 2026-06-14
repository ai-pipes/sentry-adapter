from contextvars import ContextVar
from sentry_adapter.domain.models import AuthContext

_auth_var: ContextVar[AuthContext] = ContextVar("auth_context")
_request_id_var: ContextVar[str] = ContextVar("request_id")


def get_auth() -> AuthContext:
    return _auth_var.get()


def get_request_id() -> str:
    return _request_id_var.get()


def set_auth(auth: AuthContext, request_id: str) -> None:
    _auth_var.set(auth)
    _request_id_var.set(request_id)
