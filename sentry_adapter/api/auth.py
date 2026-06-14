import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from sentry_adapter.api.context import set_auth
from sentry_adapter.config import AuthKeyConfig
from sentry_adapter.domain.models import AuthContext


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, key_index: dict[str, AuthKeyConfig]):
        super().__init__(app)
        self._key_index = key_index

    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("X-API-Key")
        key_config = self._key_index.get(api_key) if api_key else None
        if key_config is None:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        set_auth(
            AuthContext(key_id=key_config.id, user_id=key_config.user_id, team_id=key_config.team_id),
            str(uuid.uuid4()),
        )
        return await call_next(request)
