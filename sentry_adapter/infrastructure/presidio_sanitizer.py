import re
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from sentry_adapter.domain.models import SanitizerResult
from sentry_adapter.domain.sanitizer import BaseSanitizer

_SECRET_PATTERNS = [
    (r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", "BEARER_TOKEN"),
    (r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,40}\b", "GITHUB_TOKEN"),
    (r"\b(AKIA|ASIA)[0-9A-Z]{16}\b", "AWS_ACCESS_KEY"),
    (r"\bey[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b", "JWT"),
]


class PresidioSanitizer(BaseSanitizer):
    def __init__(
        self,
        entities: list[str],
        secrets_regex: bool = True,
        nlp_model: str = "en_core_web_lg",
    ):
        provider = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": nlp_model}],
        })
        self._analyzer = AnalyzerEngine(nlp_engine=provider.create_engine())
        self._anonymizer = AnonymizerEngine()
        self._entities = entities
        self._use_secrets = secrets_regex

    async def clean(self, text: str) -> SanitizerResult:
        if not text:
            return SanitizerResult(text=text, detected=[])

        detected: list[str] = []
        result = text

        presidio_results = self._analyzer.analyze(text=text, entities=self._entities, language="en")
        if presidio_results:
            detected.extend(sorted({r.entity_type for r in presidio_results}))
            anonymized = self._anonymizer.anonymize(text=text, analyzer_results=presidio_results)
            result = anonymized.text

        if self._use_secrets:
            for pattern, label in _SECRET_PATTERNS:
                new_result, count = re.subn(pattern, f"<{label}>", result)
                if count > 0:
                    if label not in detected:
                        detected.append(label)
                    result = new_result

        return SanitizerResult(text=result, detected=detected)
