"""
Tests for netrun.llm.tools.poll_cloud_models (B4 operator tooling back-port).

Covers the import-safety (base package importable without operator extra) and
the registry-diff logic, using in-memory fixtures — no cloud calls.
"""

from netrun.llm.tools import poll_cloud_models as poll


def test_module_imports_without_cloud_deps():
    # Importing the module must not require pyyaml/boto3 (lazy imports).
    assert hasattr(poll, "diff_vertex")
    assert hasattr(poll, "diff_bedrock")
    assert callable(poll.main)


class TestVertexModelParsing:
    def test_valid_resource_name(self):
        m = poll.VertexModel.from_resource_name(
            "publishers/google/models/gemini-2.5-pro"
        )
        assert m is not None
        assert m.publisher == "google"
        assert m.model_id == "gemini-2.5-pro"

    def test_invalid_resource_name(self):
        assert poll.VertexModel.from_resource_name("not/a/model") is None


class TestIsLlmModelId:
    def test_allows_known_families(self):
        assert poll._is_llm_model_id("gemini-2.5-pro")
        assert poll._is_llm_model_id("claude-3-5-sonnet")
        assert poll._is_llm_model_id("llama-4-scout")

    def test_skips_non_llm(self):
        assert not poll._is_llm_model_id("imagen-3.0")
        assert not poll._is_llm_model_id("bert-base")
        assert not poll._is_llm_model_id("embedding-001")


class TestDiffVertex:
    def test_matched_and_missing(self):
        registry = {
            "models": {
                "gemini-2.5-pro": {
                    "provider": "vertex",
                    "model_id": "gemini-2.5-pro",
                    "health": {"status": "active"},
                }
            }
        }
        live = [
            poll.VertexModel("p/google/models/gemini-2.5-pro", "google", "gemini-2.5-pro"),
            poll.VertexModel("p/google/models/gemini-3.1-pro", "google", "gemini-3.1-pro"),
        ]
        d = poll.diff_vertex(registry, live)
        assert "gemini-2.5-pro" in d.matched
        assert "vertex:gemini-3.1-pro" in d.missing_in_registry
        assert not d.is_clean()  # new upstream model => drift

    def test_stale_registry_active(self):
        registry = {
            "models": {
                "gemini-1.0-ancient": {
                    "provider": "google",
                    "model_id": "gemini-1.0-ancient",
                    "health": {"status": "active"},
                }
            }
        }
        d = poll.diff_vertex(registry, live=[])
        assert any("gemini-1.0-ancient" in s for s in d.stale_registry_active)
        assert not d.is_clean()

    def test_clean_when_all_matched(self):
        registry = {
            "models": {
                "gemini-2.5-flash": {
                    "provider": "vertex",
                    "model_id": "gemini-2.5-flash",
                    "health": {"status": "active"},
                }
            }
        }
        live = [
            poll.VertexModel(
                "p/google/models/gemini-2.5-flash", "google", "gemini-2.5-flash"
            )
        ]
        d = poll.diff_vertex(registry, live)
        assert d.is_clean()


class TestDiffBedrock:
    def _bedrock(self, model_id, status="ACTIVE"):
        return poll.BedrockModel(
            model_id=model_id,
            model_arn="arn",
            provider="anthropic",
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            response_streaming=True,
            inference_types=["ON_DEMAND"],
            customizations=[],
            lifecycle_status=status,
        )

    def test_legacy_flagged(self):
        registry = {
            "models": {
                "claude-old": {
                    "provider": "anthropic",
                    "model_id": "anthropic.claude-old",
                    "health": {"status": "active"},
                }
            }
        }
        live = [self._bedrock("anthropic.claude-old-v1:0", status="LEGACY")]
        d = poll.diff_bedrock(registry, live)
        assert any("claude-old" in s for s in d.deprecated_upstream)

    def test_missing_active_reported(self):
        d = poll.diff_bedrock(
            {"models": {}}, [self._bedrock("anthropic.claude-new-v1:0")]
        )
        assert any("bedrock:" in s for s in d.missing_in_registry)
        assert not d.is_clean()
