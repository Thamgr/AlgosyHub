from app.integrations.judges.base import JudgeAdapter
from app.models.enums import ExternalSource

_registry: dict[ExternalSource, JudgeAdapter] = {}


def register(source: ExternalSource, adapter: JudgeAdapter) -> None:
    _registry[source] = adapter


def get(source: ExternalSource) -> JudgeAdapter:
    adapter = _registry.get(source)
    if adapter is None:
        raise KeyError(f"No adapter registered for {source}")
    return adapter
