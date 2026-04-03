"""Evolution of cooperation via genetic algorithms."""

from cooperation_ga.config import SimulationConfig

__all__ = ["EvolutionEngine", "SimulationConfig"]


def __getattr__(name: str) -> object:
    """Lazily expose heavy imports at package level."""
    if name == "EvolutionEngine":
        from cooperation_ga.evolution import EvolutionEngine

        return EvolutionEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
