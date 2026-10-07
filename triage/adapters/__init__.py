"""Adapters du port `DecisionPort`. Chaque adapter n'est importé que lorsqu'on le choisit : un conteneur qui ne fait
tourner que Strands n'a pas besoin de la bibliothèque de Wazn, et inversement."""

ADAPTERS = ("wazn", "strands", "rules")


def create_adapter(name: str, url: str | None = None):
    if name == "rules":
        from triage.adapters.rules import RuleBasedAdapter
        return RuleBasedAdapter()
    if name == "wazn":
        from triage.adapters.wazn import WaznAdapter
        return WaznAdapter(url=url) if url else WaznAdapter()
    if name == "strands":
        from triage.adapters.strands import StrandsAdapter
        return StrandsAdapter(url=url) if url else StrandsAdapter()
    raise ValueError(f"adapter inconnu : {name}")
