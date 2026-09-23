"""
Netrun LLM - Windows-safe gcloud binary resolver (B4 back-port).

On Windows the ``gcloud`` entry on PATH is a bash shim that Python's
``subprocess`` cannot invoke directly without ``shell=True``; the real
executable is ``gcloud.cmd``. gcloud-authenticated LLM fallbacks (Vertex
token minting, model-garden polling) fail on Windows unless the resolver
prefers ``gcloud.cmd``.

Back-ported from ``wilbur:charlotte/scripts/poll_cloud_models.py::_gcloud_path``.
"""

import shutil

_GCLOUD_CANDIDATES = ("gcloud.cmd", "gcloud")


def gcloud_path() -> str:
    """Resolve the gcloud binary, preferring ``gcloud.cmd`` on Windows.

    Returns the first candidate found on PATH. Falls back to the bare
    ``"gcloud"`` string so ``subprocess`` raises a clear FileNotFoundError
    when gcloud is not installed at all.
    """
    for candidate in _GCLOUD_CANDIDATES:
        found = shutil.which(candidate)
        if found:
            return found
    return "gcloud"


# Back-compat alias matching the original private name in the source script.
_gcloud_path = gcloud_path
