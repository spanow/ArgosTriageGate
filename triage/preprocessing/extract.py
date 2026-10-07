"""Extraction d'incident : d'un bloc de log brut à un résumé compact.

Garde le niveau, le logger, le message, la chaîne d'exceptions jusqu'à la cause racine et quelques frames
applicatives. Retire horodatages, ids de requête, frames de framework et proxies générés. Normalise e-mails,
UUID, IP, dates et grands nombres.
"""

import re
from dataclasses import dataclass, field

MAX_FRAMES = 5           # frames applicatives gardées par événement
MAX_DETAILS = 8         # lignes de détail (suite d'un message multi-lignes) par événement
MAX_LINE = 300           # au-delà, une ligne est tronquée

# Frames considérées comme « framework » : JDK, Spring, serveurs, drivers, bibliothèques courantes.
FRAMEWORK_PREFIXES = (
    "java.", "javax.", "jdk.", "sun.", "com.sun.", "jakarta.", "org.springframework.", "org.apache.", "org.hibernate.",
    "com.zaxxer.", "tools.jackson.", "com.fasterxml.", "org.h2.", "org.postgresql.", "io.netty.", "io.lettuce.",
    "software.amazon.", "liquibase.", "reactor.", "kotlin.", "io.micrometer.", "org.xml.", "org.slf4j.", "ch.qos.",
)

HEADER = re.compile(
    r"^\d{4}-\d\d-\d\dT\S+\s+(?P<level>TRACE|DEBUG|INFO|WARN|ERROR)\s+"
    r"(?:\[req=[^\]]*\]\s+)?(?:\d+\s+---\s+)?(?:\[[^\]]*\]\s+)*(?P<logger>\S+)\s+:\s?(?P<message>.*)$")
EXCEPTION = re.compile(
    r"^(?:Caused by:\s+)?(?P<type>(?:[a-z_$][\w$]*\.)+[A-Z][\w$]*?(?:Exception|Error|Throwable)[\w$]*)"
    r"(?:[:;]\s*(?P<message>.*))?$")
FRAME = re.compile(r"^\s+at\s+(?:[\w.$-]+/)?(?P<method>[\w.$<>]+)\((?P<location>[^)]*)\)")
OMITTED = re.compile(r"^\s+\.\.\. \d+ (?:more|common frames omitted)")

NORMALIZERS = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "<EMAIL>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<UUID>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<IP>"),
    (re.compile(r"\b\d{4}-\d\d-\d\d(?:T[\d:.]+(?:[+-]\d\d:\d\d|Z)?)?\b"), "<DATE>"),
    # Identifiants longs. Les codes courts ont un sens et restent : HTTP 403, SQLState 23505, 588 ms.
    (re.compile(r"\b\d{6,}\b"), "<NUM>"),
]
DECORATION = re.compile(r"^[*=\-_#~]{3,}$")  # bannières (*****) sans information


def normalize(text: str) -> str:
    for pattern, replacement in NORMALIZERS:
        text = pattern.sub(replacement, text)
    return text


@dataclass
class ExceptionInfo:
    type: str
    message: str = ""


@dataclass
class Event:
    level: str | None
    logger: str | None
    message: str
    chain: list[ExceptionInfo] = field(default_factory=list)
    frames: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        head = f"{self.level} {self.logger}: {self.message}" if self.level else self.message
        lines = [head]
        for position, exception in enumerate(self.chain):
            prefix = "Exception" if position == 0 else "Caused by"
            lines.append(f"{prefix}: {exception.type}: {exception.message}".rstrip(": "))
        lines += [f"  {detail}" for detail in self.details]
        lines += [f"  at {frame}" for frame in self.frames]
        return "\n".join(_clip(normalize(line)) for line in lines)


@dataclass
class Incident:
    events: list[Event]

    @property
    def root_cause(self) -> ExceptionInfo | None:
        """La dernière exception de la chaîne du dernier événement qui en a une."""
        for event in reversed(self.events):
            if event.chain:
                return event.chain[-1]
        return None

    def to_text(self) -> str:
        texts: list[str] = []
        for event in self.events:
            text = event.to_text()
            if text not in texts:  # des événements identiques n'apportent rien
                texts.append(text)
        return "\n".join(texts)


def extract(raw: str) -> Incident:
    events: list[Event] = []
    for line in raw.splitlines():
        header = HEADER.match(line)
        if header:
            events.append(Event(header["level"], header["logger"], header["message"].strip()))
        elif not line.strip():
            continue
        elif not events:
            events.append(Event(None, None, line.strip()))  # texte qui n'est pas un log structuré
        else:
            _add_line(events[-1], line)
    return Incident(events)


def _add_line(event: Event, line: str) -> None:
    if OMITTED.match(line):
        return
    frame = FRAME.match(line)
    if frame:
        method = frame["method"]
        generated = "$$" in method or frame["location"] == "<generated>"
        if not generated and not method.startswith(FRAMEWORK_PREFIXES) and method not in event.frames \
                and len(event.frames) < MAX_FRAMES:
            event.frames.append(method)
        return
    exception = EXCEPTION.match(line.strip())
    if exception:
        info = ExceptionInfo(exception["type"], (exception["message"] or "").strip())
        if not event.chain or event.chain[-1] != info:  # une cause répétée telle quelle n'apporte rien
            event.chain.append(info)
        return
    detail = line.strip()
    if not DECORATION.match(detail) and detail not in event.details and len(event.details) < MAX_DETAILS:
        event.details.append(detail)


def _clip(line: str) -> str:
    return line if len(line) <= MAX_LINE else line[:MAX_LINE] + "…"
