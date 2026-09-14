"""autodraft.backends - optional local-LLM consult layer (Phase 4).

The deterministic core is the only author of numbers. This package only
re-phrases evidence for low-confidence documents so decline reasons are sharper
(honest refusals, never fabricated data). Everything here is optional: with
AUTODRAFT_CONSULT unset (default) the pipeline is byte-for-byte deterministic.
"""
from . import consult, ollama  # noqa: F401