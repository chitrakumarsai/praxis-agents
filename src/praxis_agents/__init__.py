"""praxis-agents: apply Markdown engineering standards to AI coding agents."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("praxis-agents")
except PackageNotFoundError:  # running from a source checkout without install
    __version__ = "0.0.0"

__all__ = ["__version__"]
