from abc import ABC, abstractmethod
from .models import SanitizerResult


class BaseSanitizer(ABC):
    @abstractmethod
    async def clean(self, text: str) -> SanitizerResult:
        ...
