"""Baseline à règles : des regex sur le texte extrait, sans modèle.

Point de comparaison pour les modèles. Les règles ont été écrites en connaissant les scénarios de victim-app :
sur ces cas-là elles sont avantagées ; le jeu de robustesse mesure mieux leur portée réelle.
"""

import re
import time
from typing import Sequence

from triage.domain.model import Candidate, Decision

# Signatures classiques par catégorie (une seule regex par catégorie, insensible à la casse).
SIGNATURES = {
    "security_certificate": r"SSLHandshake|Certificate(Expired|NotYetValid)Exception|CertPathValidator|PKIX|"
                            r"401 Unauthorized|403 Forbidden|Access Denied|invalid_token|AccessDeniedException",
    "configuration": r"Could not resolve placeholder|Required key .* not found|Failed to bind properties|"
                     r"No qualifying bean|Missing (required )?(property|environment variable)",
    "capacity": r"Connection is not available|too many clients|RejectedExecutionException|OutOfMemoryError|"
                r"No space left on device|Too many open files|pool (is )?exhausted",
    "dependency": r"SocketTimeoutException|ConnectException|Connection refused|UnknownHostException|Read timed out|"
                  r"HttpServerErrorException|503 Service Unavailable|ConnectTimeout|RedisConnectionFailure|"
                  r"NoRouteToHost",
    "data_quality": r"JsonParseException|UnexpectedEndOfInput|MismatchedInputException|SAXParseException|"
                    r"DateTimeParseException|NumberFormatException|Unparseable|malformed",
    "code_defect": r"NullPointerException|IndexOutOfBoundsException|ClassCastException|IllegalArgumentException|"
                   r"ArithmeticException|ConcurrentModificationException|OptimisticLock|StaleObjectState|"
                   r"DataIntegrityViolation|ConstraintViolation|UnsupportedOperationException",
}
COMPILED = {category: re.compile(pattern, re.IGNORECASE) for category, pattern in SIGNATURES.items()}


class RuleBasedAdapter:
    name = "rules"

    def decide(self, context: str, candidates: Sequence[Candidate], instruction: str) -> Decision:
        start = time.perf_counter()
        hits = {c.id: len(COMPILED[c.id].findall(context)) if c.id in COMPILED else 0 for c in candidates}
        total = sum(hits.values())
        if total == 0:
            probabilities = {c.id: 1 / len(candidates) for c in candidates}
        else:
            probabilities = {cid: count / total for cid, count in hits.items()}
        return Decision(probabilities=probabilities, none_probability=1.0 if total == 0 else 0.0,
                        is_none=total == 0, latency_ms=(time.perf_counter() - start) * 1000, model=self.name)
