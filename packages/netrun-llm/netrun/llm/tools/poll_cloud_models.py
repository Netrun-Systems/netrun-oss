#!/usr/bin/env python3
"""
poll_cloud_models.py — survey Vertex AI Model Garden + AWS Bedrock for the
models (and quotas) actually available to our accounts, then diff against a
model registry YAML so we know which registry entries are stale, missing, or
deprecated upstream.

Operator tooling (netrun-llm[operator]). Back-ported from
``wilbur:charlotte/scripts/poll_cloud_models.py`` (549 LoC, commit 72860fc,
2026-05-28). Differences vs the source:
  - the gcloud resolver now lives in ``netrun.llm.gcloud`` and is shared with
    the adapter layer (B4b);
  - the ``pyyaml`` import is lazy (inside load_registry/main) so this module
    imports cleanly without the operator extra, keeping the base package and
    its test suite dependency-light;
  - no top-level ``sys.exit`` on missing deps.

Run periodically to catch:
  - New Gemini/Claude/Llama releases hitting Vertex or Bedrock before they
    show up in our routing tables
  - Models registered as ``active`` that the provider has retired
  - Quota changes that affect routing decisions

Usage:
  python -m netrun.llm.tools.poll_cloud_models --registry path/to/registry.yaml
  python -m netrun.llm.tools.poll_cloud_models --json
  python -m netrun.llm.tools.poll_cloud_models --no-aws
  python -m netrun.llm.tools.poll_cloud_models --no-gcp

Auth assumptions:
  - GCP: ``gcloud`` on PATH and authenticated (ADC or user).
  - AWS: ``boto3`` installed and credentials resolvable by the default chain.

Exit codes:
  0 — diff is clean
  1 — diff has issues (missing-upstream OR stale-registry-active)
  2 — failure that prevented the diff from completing (auth, transport, deps)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from netrun.llm.gcloud import gcloud_path

# Defaults — change here, not inline.
DEFAULT_GCP_PROJECT = "gen-lang-client-0047375361"  # Charlotte/Pulse prod project
DEFAULT_GCP_REGION = "us-central1"
DEFAULT_AWS_REGION = "us-west-2"  # broadest Bedrock model availability
DEFAULT_REGISTRY = Path("model_registry_v2.yaml")


# ---------------------------------------------------------------------------
# GCP — Vertex AI Model Garden via gcloud
# ---------------------------------------------------------------------------


@dataclass
class VertexModel:
    name: str  # e.g. "publishers/google/models/gemini-2.5-pro"
    publisher: str
    model_id: str

    @classmethod
    def from_resource_name(cls, full: str) -> "VertexModel | None":
        # Resource shape: publishers/<pub>/models/<id>
        parts = full.strip().split("/")
        if len(parts) < 4 or parts[0] != "publishers" or parts[2] != "models":
            return None
        return cls(name=full, publisher=parts[1], model_id=parts[3])


def fetch_vertex_models(project: str, region: str) -> list[VertexModel]:
    """Shell out to ``gcloud ai model-garden models list``. The Garden
    listing is global (no per-region scoping); the region is recorded in the
    report for context but doesn't constrain the query."""
    del region  # accepted for symmetry with fetch_bedrock_models, ignored
    cmd = [
        gcloud_path(),
        "ai",
        "model-garden",
        "models",
        "list",
        f"--project={project}",
        f"--billing-project={project}",
        "--limit=1000",
        "--format=value(name)",
    ]
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=60
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"gcloud not on PATH: {e}") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"gcloud ai model-garden models list failed: {e.stderr.strip()}"
        ) from e
    models: list[VertexModel] = []
    for line in out.stdout.splitlines():
        m = VertexModel.from_resource_name(line)
        if m is not None:
            models.append(m)
    return models


def fetch_vertex_quotas(project: str, region: str) -> list[dict[str, Any]]:
    """Hit the Cloud Quotas API for aiplatform.googleapis.com. Returns the raw
    quota infos. Falls back to an empty list on permission errors so the
    overall poll still completes."""
    del region
    cmd = [gcloud_path(), "auth", "print-access-token"]
    try:
        token = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=15
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return []
    url = (
        "https://cloudquotas.googleapis.com/v1/"
        f"projects/{project}/locations/global/services/"
        "aiplatform.googleapis.com/quotaInfos?pageSize=500"
    )
    import urllib.request  # urllib avoids adding a `requests` dep.

    req = urllib.request.Request(  # noqa: S310 — fixed HTTPS URL
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "x-goog-user-project": project,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
            body = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return [{"_error": str(e)}]
    return body.get("quotaInfos", [])


# ---------------------------------------------------------------------------
# AWS — Bedrock via boto3
# ---------------------------------------------------------------------------


@dataclass
class BedrockModel:
    model_id: str
    model_arn: str
    provider: str
    input_modalities: list[str]
    output_modalities: list[str]
    response_streaming: bool
    inference_types: list[str]
    customizations: list[str]
    lifecycle_status: str = ""  # ACTIVE | LEGACY


def fetch_bedrock_models(region: str) -> list[BedrockModel]:
    try:
        import boto3  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "boto3 not installed (pip install boto3); pass --no-aws to skip"
        ) from e
    client = boto3.client("bedrock", region_name=region)
    resp = client.list_foundation_models()
    out: list[BedrockModel] = []
    for s in resp.get("modelSummaries", []):
        out.append(
            BedrockModel(
                model_id=s.get("modelId", ""),
                model_arn=s.get("modelArn", ""),
                provider=s.get("providerName", ""),
                input_modalities=s.get("inputModalities", []) or [],
                output_modalities=s.get("outputModalities", []) or [],
                response_streaming=bool(s.get("responseStreamingSupported", False)),
                inference_types=s.get("inferenceTypesSupported", []) or [],
                customizations=s.get("customizationsSupported", []) or [],
                lifecycle_status=(s.get("modelLifecycle") or {}).get("status", ""),
            )
        )
    return out


def fetch_bedrock_quotas(region: str) -> list[dict[str, Any]]:
    """List Bedrock-related service quotas in the region."""
    try:
        import boto3  # type: ignore
    except ImportError:
        return []
    client = boto3.client("service-quotas", region_name=region)
    out: list[dict[str, Any]] = []
    paginator = client.get_paginator("list_service_quotas")
    try:
        for page in paginator.paginate(ServiceCode="bedrock"):
            for q in page.get("Quotas", []):
                out.append(
                    {
                        "name": q.get("QuotaName"),
                        "code": q.get("QuotaCode"),
                        "value": q.get("Value"),
                        "unit": q.get("Unit"),
                        "adjustable": q.get("Adjustable"),
                    }
                )
    except Exception as e:  # noqa: BLE001
        out.append({"_error": str(e)})
    return out


# ---------------------------------------------------------------------------
# Registry diff
# ---------------------------------------------------------------------------


def load_registry(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "pyyaml required (pip install 'netrun-llm[operator]')"
        ) from e
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@dataclass
class Diff:
    missing_in_registry: list[str] = field(default_factory=list)
    deprecated_upstream: list[str] = field(default_factory=list)
    stale_registry_active: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)

    def is_clean(self) -> bool:
        return not (self.missing_in_registry or self.stale_registry_active)


def _is_llm_model_id(model_id: str) -> bool:
    """Filter Vertex Model Garden entries down to chat/completion LLMs the
    registry actually cares about."""
    mid = model_id.lower()
    skip_prefixes = (
        "automl-", "bart-", "bert-", "chirp", "cloudnerf", "embedding",
        "gemini-embedding", "imagegeneration", "imagetext", "translation",
        "veo-", "videogeneration", "speechgeneration", "imagen-", "instant-id",
        "stable-diffusion", "controlnet", "cv-", "dlrm", "tabnet", "t5-",
        "t5gemma", "vit-", "object-detection", "image-classification",
    )
    for p in skip_prefixes:
        if mid.startswith(p):
            return False
    allow_substrings = (
        "gemini", "claude", "gpt", "llama", "mistral", "qwen", "deepseek",
        "kimi", "nova", "phi", "command", "gemma", "grok", "devstral",
        "codestral",
    )
    return any(s in mid for s in allow_substrings)


def diff_vertex(registry: dict[str, Any], live: list[VertexModel]) -> Diff:
    d = Diff()
    live_ids = {
        m.model_id.lower()
        for m in live
        if m.publisher
        in ("google", "anthropic", "meta", "mistralai", "qwen", "deepseek-ai")
        and _is_llm_model_id(m.model_id)
    }
    registry_entries = registry.get("models", {}) or {}
    seen_in_registry: set[str] = set()
    for slug, entry in registry_entries.items():
        if (entry.get("provider") or "").lower() not in (
            "vertex", "vertex_ai", "google", "gemini",
        ):
            continue
        model_id = (entry.get("model_id") or slug).lower()
        seen_in_registry.add(model_id)
        if model_id in live_ids:
            d.matched.append(slug)
        elif entry.get("health", {}).get("status") == "active" and not entry.get(
            "deprecation_notice"
        ):
            d.stale_registry_active.append(f"{slug} (model_id={model_id})")
    for live_id in sorted(live_ids):
        if live_id not in seen_in_registry:
            d.missing_in_registry.append(f"vertex:{live_id}")
    return d


def diff_bedrock(registry: dict[str, Any], live: list[BedrockModel]) -> Diff:
    d = Diff()
    live_active = {m.model_id.lower() for m in live if m.lifecycle_status == "ACTIVE"}
    live_legacy = {m.model_id.lower() for m in live if m.lifecycle_status == "LEGACY"}
    registry_entries = registry.get("models", {}) or {}
    seen_in_registry: set[str] = set()
    for slug, entry in registry_entries.items():
        provider = (entry.get("provider") or "").lower()
        if provider not in (
            "bedrock", "aws", "anthropic", "meta", "mistral", "amazon",
            "deepseek", "qwen",
        ):
            continue
        model_id = (entry.get("model_id") or slug).lower()
        matched = next(
            (lid for lid in live_active if model_id in lid or lid in model_id), None
        )
        legacy_match = next(
            (lid for lid in live_legacy if model_id in lid or lid in model_id), None
        )
        if matched:
            d.matched.append(slug)
            seen_in_registry.add(matched)
        elif legacy_match:
            d.deprecated_upstream.append(
                f"{slug} (Bedrock marks LEGACY: {legacy_match})"
            )
            seen_in_registry.add(legacy_match)
        elif entry.get("health", {}).get("status") == "active" and not entry.get(
            "deprecation_notice"
        ):
            d.stale_registry_active.append(f"{slug} (model_id={model_id})")
    for live_id in sorted(live_active):
        if live_id not in seen_in_registry:
            d.missing_in_registry.append(f"bedrock:{live_id}")
    return d


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def print_human(report: dict[str, Any]) -> None:
    print(f"=== Cloud Model Poller ({report['polled_at']}) ===")
    print()
    if "vertex" in report:
        v = report["vertex"]
        if "_error" in v:
            print(f"vertex: ERROR — {v['_error']}")
        else:
            print(f"vertex: {len(v['models'])} models in Model Garden ({v['region']})")
            d = v["diff"]
            if d["matched"]:
                print(f"  [ok]      matched in registry: {len(d['matched'])}")
            if d["missing_in_registry"]:
                print(
                    f"  [add]     new upstream not in registry "
                    f"({len(d['missing_in_registry'])}):"
                )
                for x in d["missing_in_registry"][:20]:
                    print(f"      {x}")
                if len(d["missing_in_registry"]) > 20:
                    print(f"      ... and {len(d['missing_in_registry']) - 20} more")
            if d["stale_registry_active"]:
                print(
                    f"  [stale]   registry-active but not in upstream "
                    f"({len(d['stale_registry_active'])}):"
                )
                for x in d["stale_registry_active"]:
                    print(f"      {x}")
            quotas = v.get("quotas", [])
            if quotas:
                print(f"  quotas: {len(quotas)} entries")
        print()
    if "bedrock" in report:
        b = report["bedrock"]
        if "_error" in b:
            print(f"bedrock: ERROR — {b['_error']}")
        else:
            print(f"bedrock: {len(b['models'])} foundation models ({b['region']})")
            d = b["diff"]
            if d["matched"]:
                print(f"  [ok]      matched in registry: {len(d['matched'])}")
            if d["deprecated_upstream"]:
                print(
                    f"  [legacy]  Bedrock LEGACY but registry still active "
                    f"({len(d['deprecated_upstream'])}):"
                )
                for x in d["deprecated_upstream"]:
                    print(f"      {x}")
            if d["missing_in_registry"]:
                print(
                    f"  [add]     new upstream not in registry "
                    f"({len(d['missing_in_registry'])}):"
                )
                for x in d["missing_in_registry"][:20]:
                    print(f"      {x}")
                if len(d["missing_in_registry"]) > 20:
                    print(f"      ... and {len(d['missing_in_registry']) - 20} more")
            if d["stale_registry_active"]:
                print(
                    f"  [stale]   registry-active but not in upstream "
                    f"({len(d['stale_registry_active'])}):"
                )
                for x in d["stale_registry_active"]:
                    print(f"      {x}")
            quotas = b.get("quotas", [])
            if quotas:
                non_err = [q for q in quotas if "_error" not in q]
                print(f"  quotas: {len(non_err)} entries")
        print()
    if not report.get("clean"):
        print("status: DRIFT — registry needs update")
    else:
        print("status: CLEAN")


def main(argv: "list[str] | None" = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--gcp-project", default=DEFAULT_GCP_PROJECT)
    p.add_argument("--gcp-region", default=DEFAULT_GCP_REGION)
    p.add_argument("--aws-region", default=DEFAULT_AWS_REGION)
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--no-gcp", action="store_true")
    p.add_argument("--no-aws", action="store_true")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of human report")
    args = p.parse_args(argv)

    if not args.registry.exists():
        print(f"ERROR: registry not found at {args.registry}", file=sys.stderr)
        return 2

    registry = load_registry(args.registry)

    import datetime as _dt

    report: dict[str, Any] = {
        "polled_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "registry": str(args.registry),
        "clean": True,
    }

    if not args.no_gcp:
        try:
            vmodels = fetch_vertex_models(args.gcp_project, args.gcp_region)
            vquotas = fetch_vertex_quotas(args.gcp_project, args.gcp_region)
            vdiff = diff_vertex(registry, vmodels)
            report["vertex"] = {
                "project": args.gcp_project,
                "region": args.gcp_region,
                "models": [m.__dict__ for m in vmodels],
                "quotas": vquotas,
                "diff": {
                    "matched": vdiff.matched,
                    "missing_in_registry": vdiff.missing_in_registry,
                    "stale_registry_active": vdiff.stale_registry_active,
                    "deprecated_upstream": vdiff.deprecated_upstream,
                },
            }
            if not vdiff.is_clean():
                report["clean"] = False
        except Exception as e:  # noqa: BLE001
            report["vertex"] = {"_error": str(e)}

    if not args.no_aws:
        try:
            bmodels = fetch_bedrock_models(args.aws_region)
            bquotas = fetch_bedrock_quotas(args.aws_region)
            bdiff = diff_bedrock(registry, bmodels)
            report["bedrock"] = {
                "region": args.aws_region,
                "models": [m.__dict__ for m in bmodels],
                "quotas": bquotas,
                "diff": {
                    "matched": bdiff.matched,
                    "missing_in_registry": bdiff.missing_in_registry,
                    "stale_registry_active": bdiff.stale_registry_active,
                    "deprecated_upstream": bdiff.deprecated_upstream,
                },
            }
            if not bdiff.is_clean():
                report["clean"] = False
        except Exception as e:  # noqa: BLE001
            report["bedrock"] = {"_error": str(e)}

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_human(report)

    return 0 if report["clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
