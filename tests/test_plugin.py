"""Consistency checks for the Claude Code plugin and marketplace manifests."""

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESERVED_PREFIXES = ("claude-", "anthropic-", "anthropics-", "cc-plugin-")


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plugin() -> dict[str, Any]:
    return load(".claude-plugin/plugin.json")


@pytest.fixture(scope="module")
def marketplace() -> dict[str, Any]:
    return load(".claude-plugin/marketplace.json")


@pytest.fixture(scope="module")
def mcp() -> dict[str, Any]:
    return load(".mcp.json")


def test_marketplace_has_required_fields(marketplace: dict[str, Any]) -> None:
    assert marketplace["name"]
    assert marketplace["owner"]["name"]
    assert len(marketplace["plugins"]) == 1


def test_entry_name_matches_manifest_name(
    plugin: dict[str, Any], marketplace: dict[str, Any]
) -> None:
    assert marketplace["plugins"][0]["name"] == plugin["name"]


def test_entry_source_is_marketplace_root(marketplace: dict[str, Any]) -> None:
    source = marketplace["plugins"][0]["source"]
    assert source == "./"
    assert ".." not in source


@pytest.mark.parametrize("key", ["name"])
def test_names_are_not_reserved(
    plugin: dict[str, Any], marketplace: dict[str, Any], key: str
) -> None:
    for name in (plugin[key], marketplace[key]):
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name), name
        assert not name.startswith(RESERVED_PREFIXES), name


def test_plugin_version_matches_pyproject(plugin: dict[str, Any]) -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert plugin["version"] == pyproject["project"]["version"]


def test_mcp_server_uses_locked_uv_project_in_plugin_root(mcp: dict[str, Any]) -> None:
    server = mcp["mcpServers"]["local-llm"]
    assert server["command"] == "uv"
    args = server["args"]
    assert "--locked" in args
    assert "--no-dev" in args
    assert args[args.index("--project") + 1] == "${CLAUDE_PLUGIN_ROOT}"
    assert args[-1] == "local-llm-mcp"


def test_mcp_entry_point_exists_in_pyproject(mcp: dict[str, Any]) -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert mcp["mcpServers"]["local-llm"]["args"][-1] in pyproject["project"]["scripts"]


def test_mcp_env_scopes_workspace_to_project_and_keeps_venv_out_of_plugin_root(
    mcp: dict[str, Any],
) -> None:
    env = mcp["mcpServers"]["local-llm"]["env"]
    assert env["LOCAL_LLM_WORKSPACE"] == "${CLAUDE_PROJECT_DIR}"
    assert env["UV_PROJECT_ENVIRONMENT"].startswith("${CLAUDE_PLUGIN_DATA}/")


def test_every_user_config_reference_is_declared(
    plugin: dict[str, Any], mcp: dict[str, Any]
) -> None:
    declared = set(plugin["userConfig"])
    referenced = set(re.findall(r"\$\{user_config\.(\w+)\}", json.dumps(mcp)))
    assert referenced
    assert referenced <= declared


def test_env_vars_in_mcp_are_known_settings(mcp: dict[str, Any]) -> None:
    from pydantic import AliasChoices

    from local_llm.config import Settings

    aliases: set[str] = set()
    for field in Settings.model_fields.values():
        alias = field.validation_alias
        if isinstance(alias, AliasChoices):
            aliases.update(str(choice) for choice in alias.choices)
        elif alias is not None:
            aliases.add(str(alias))
    for name in mcp["mcpServers"]["local-llm"]["env"]:
        assert name in aliases or name == "UV_PROJECT_ENVIRONMENT", name


def test_user_config_defaults_pass_settings_validation(plugin: dict[str, Any]) -> None:
    from local_llm.config import Settings

    cfg = plugin["userConfig"]
    Settings(
        model=cfg["model"]["default"],
        ollama_base_url=cfg["ollama_base_url"]["default"],
        backend=cfg["backend"]["default"],
        openai_base_url=cfg["openai_base_url"]["default"],
        api_key=cfg["api_key"]["default"],
        context_tokens=cfg["context_tokens"]["default"],
        workspace=ROOT,
    )
