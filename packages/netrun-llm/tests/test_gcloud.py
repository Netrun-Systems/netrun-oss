"""
Tests for netrun.llm.gcloud (B4 back-port): Windows-safe gcloud resolver.
"""

import netrun.llm.gcloud as gc
from netrun.llm import gcloud_path


def test_prefers_gcloud_cmd_when_present(monkeypatch):
    """On Windows both `gcloud.cmd` and `gcloud` may resolve; must pick .cmd."""
    def fake_which(name):
        return {
            "gcloud.cmd": r"C:\gcloud\bin\gcloud.cmd",
            "gcloud": r"C:\gcloud\bin\gcloud",
        }.get(name)

    monkeypatch.setattr(gc.shutil, "which", fake_which)
    assert gc.gcloud_path() == r"C:\gcloud\bin\gcloud.cmd"


def test_falls_back_to_plain_gcloud_on_posix(monkeypatch):
    """When only `gcloud` resolves (typical POSIX), return it."""
    def fake_which(name):
        return "/usr/bin/gcloud" if name == "gcloud" else None

    monkeypatch.setattr(gc.shutil, "which", fake_which)
    assert gc.gcloud_path() == "/usr/bin/gcloud"


def test_returns_bare_name_when_not_installed(monkeypatch):
    monkeypatch.setattr(gc.shutil, "which", lambda name: None)
    assert gc.gcloud_path() == "gcloud"


def test_exported_from_package():
    assert gcloud_path is gc.gcloud_path


def test_private_alias_matches():
    assert gc._gcloud_path is gc.gcloud_path
