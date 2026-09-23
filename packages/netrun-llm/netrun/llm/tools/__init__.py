"""
Netrun LLM - Operator tooling (B4 back-port).

Optional operator-facing utilities. Install with:

    pip install 'netrun-llm[operator]'

Modules here may require heavy/cloud SDK dependencies (pyyaml, boto3) and are
NOT imported by ``netrun.llm`` at package import time — the base package stays
dependency-light and importable without the operator extra.
"""
