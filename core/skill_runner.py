"""Thread-safe runner for original day-trader-skill tools with stdout capture."""

import io
import json
import logging
from contextlib import redirect_stdout, redirect_stderr
from typing import List, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def run_skill_argv(mod: Any, argv: List[str]) -> Tuple[int, str, str]:
    """Execute mod.main(argv) while capturing stdout and stderr.

    Returns (exit_code, stdout_str, stderr_str).
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    exit_code = 1
    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exit_code = mod.main(argv)
            if exit_code is None:
                exit_code = 0
    except SystemExit as se:
        exit_code = se.code if isinstance(se.code, int) else (0 if se.code is None else 1)
    except Exception as e:
        logger.error("Exception running %s with argv %s: %s", getattr(mod, "__name__", "skill"), argv, e)
        stderr_buf.write(str(e))
        exit_code = 1

    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


def run_skill_json(mod: Any, argv: List[str]) -> Tuple[int, Optional[Any], str]:
    """Execute mod.main(argv) and parse stdout as JSON.

    Returns (exit_code, parsed_json_or_None, stdout_or_stderr).
    """
    code, stdout_text, stderr_text = run_skill_argv(mod, argv)
    trimmed = stdout_text.strip()
    if not trimmed:
        return code, None, stderr_text.strip() or "No output returned"

    # Attempt to parse json
    try:
        data = json.loads(trimmed)
        return code, data, ""
    except json.JSONDecodeError:
        # Sometimes there may be log lines before JSON; look for first '{' or '['
        first_brace = trimmed.find("{")
        first_bracket = trimmed.find("[")
        start_idx = -1
        if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
            start_idx = first_brace
        elif first_bracket != -1:
            start_idx = first_bracket

        if start_idx != -1:
            try:
                data = json.loads(trimmed[start_idx:])
                return code, data, ""
            except json.JSONDecodeError:
                pass

        return code, None, trimmed
