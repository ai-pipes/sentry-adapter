class SentryAuthError(Exception):
    pass


class SentryNotFoundError(Exception):
    def __init__(self, resource_id: str):
        self.resource_id = resource_id
        super().__init__(f"Not found: {resource_id}")


class SentryTimeoutError(Exception):
    pass


class SentryUpstreamError(Exception):
    pass
