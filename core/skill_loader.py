"""Dynamic loader for original day-trader-skill modules."""

import importlib.util
import os
from typing import Any

# Day-trader-skill root directory
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_LOADED_MODULES = {}


def load_skill_module(folder_name: str, script_name: str) -> Any:
    """Load a Python module from a hyphenated skill directory."""
    key = f"{folder_name}/{script_name}"
    if key in _LOADED_MODULES:
        return _LOADED_MODULES[key]

    script_path = os.path.join(REPO_ROOT, folder_name, f"{script_name}.py")
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Skill script not found: {script_path}")

    module_name = f"skill_{folder_name.replace('-', '_')}_{script_name}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {script_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _LOADED_MODULES[key] = mod
    return mod


def get_scanner_mod():
    return load_skill_module("trader-scanner", "scan")


def get_news_mod():
    return load_skill_module("trader-news", "news")


def get_entry_mod():
    return load_skill_module("trader-entry", "entry")


def get_exit_mod():
    return load_skill_module("trader-exit", "exit")


def get_timemachine_mod():
    return load_skill_module("trader-timemachine", "timemachine")


def get_risk_mod():
    return load_skill_module("trader-risk", "check")


def get_budget_mod():
    return load_skill_module("trader-budget", "size")


def get_broker_mod():
    return load_skill_module("trader-broker", "ticket")


def get_alerts_mod():
    return load_skill_module("trader-alerts", "alerts")


def get_analyst_mod():
    return load_skill_module("trader-analyst", "facts")


def get_pelosi_mod():
    return load_skill_module("trader-pelosi", "ptr")
