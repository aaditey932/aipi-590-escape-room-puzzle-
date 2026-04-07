"""LLM-assisted puzzle generation; always validated by brute-force solver."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import urllib.request
from pathlib import Path
from typing import Any

from truth_matrix.constants import SWITCHES
from truth_matrix.validator import validate_puzzle_json

log = logging.getLogger(__name__)

SCHEMA_SNIPPET = """
Puzzle JSON must match this shape (statements use a small AST only):
- {"type": "switch_on", "name": "A"|"B"|"C"|"D"|"E"}
- {"type": "not", "child": <proposition>}
- {"type": "and"|"or", "children": [<proposition>, ...]}
- {"type": "xor", "left": <p>, "right": <p>}
- {"type": "implies", "antecedent": <p>, "consequent": <p>}
- {"type": "same", "a": "A".."E", "b": "A".."E"}
- {"type": "count_eq", "value": 0..5}

The puzzle must have exactly keys A–E in "statements" and "display".
Output a single JSON object, no markdown fences.
"""


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object in model output")
    return json.loads(m.group(0))


def generate_openai(
    *,
    difficulty: int = 2,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    prompt = (
        f"Generate a Truth Matrix puzzle with difficulty about {difficulty}/5. "
        + SCHEMA_SNIPPET
    )
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    return _extract_json_object(content)


def generate_ollama(
    *,
    difficulty: int = 2,
    host: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    host = (host or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
    model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")
    prompt = (
        f"Generate a Truth Matrix puzzle with difficulty about {difficulty}/5. "
        + SCHEMA_SNIPPET
    )
    body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    text = data.get("response", "")
    return _extract_json_object(text)


def generate_validated_puzzle(
    *,
    difficulty: int = 2,
    max_attempts: int = 5,
    backend: str | None = None,
) -> tuple[dict[str, Any], str | None]:
    """
    Try LLM backends until a puzzle passes JSON schema + unique-solution check.
    Returns (puzzle, error_message_if_failed).
    """
    backend = backend or os.environ.get("TRUTH_MATRIX_LLM_BACKEND", "template")
    last_err: str | None = None
    for attempt in range(max_attempts):
        try:
            if backend == "openai":
                raw = generate_openai(difficulty=difficulty)
            elif backend == "ollama":
                raw = generate_ollama(difficulty=difficulty)
            else:
                raw = generate_template(difficulty=difficulty)
            rid = raw.get("id") or f"gen_{attempt}"
            raw["id"] = str(rid)
            if "display" not in raw or "statements" not in raw:
                last_err = "Missing statements/display"
                continue
            vr = validate_puzzle_json(raw, require_unique=True)
            if vr.ok:
                return raw, None
            last_err = vr.error or "validation failed"
            log.info("Attempt %s rejected: %s", attempt, last_err)
        except Exception as e:
            last_err = str(e)
            log.info("Attempt %s error: %s", attempt, e)
    return {}, last_err or "unknown error"


def generate_template(*, difficulty: int = 2) -> dict[str, Any]:
    """Deterministic pool-based generator (no network)."""
    rng = random.Random(difficulty * 7919 + 42)
    pool: list[dict[str, Any]] = [
        {"type": "switch_on", "name": "A"},
        {"type": "switch_on", "name": "B"},
        {"type": "switch_on", "name": "C"},
        {"type": "not", "child": {"type": "switch_on", "name": "A"}},
        {"type": "count_eq", "value": 2},
        {"type": "count_eq", "value": 3},
        {"type": "same", "a": "A", "b": "B"},
        {
            "type": "xor",
            "left": {"type": "switch_on", "name": "C"},
            "right": {"type": "switch_on", "name": "D"},
        },
    ]
    for _ in range(2000):
        stmts = {k: rng.choice(pool) for k in SWITCHES}
        p = {
            "id": f"template_d{difficulty}_{rng.randint(0, 1_000_000)}",
            "title": f"Template puzzle (difficulty {difficulty})",
            "difficulty": difficulty,
            "statements": stmts,
            "display": {k: f"Statement {k}." for k in SWITCHES},
        }
        vr = validate_puzzle_json(p, require_unique=True)
        if vr.ok:
            return p
    raise RuntimeError("Could not sample a unique puzzle; adjust pool or difficulty")


def save_puzzle(puzzle: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(puzzle, f, indent=2)
        f.write("\n")


def hint_llm(
    puzzle: dict[str, Any],
    current: dict[str, bool],
    solution: dict[str, bool],
) -> str | None:
    """Optional short hint via OpenAI or Ollama; falls back to None on error."""
    backend = os.environ.get("TRUTH_MATRIX_HINT_BACKEND", "")
    if backend not in ("openai", "ollama"):
        return None
    summary = {k: current.get(k) for k in SWITCHES}
    sols = {k: solution.get(k) for k in SWITCHES}
    prompt = (
        "Give ONE short hint (max 25 words) for a logic switch puzzle. "
        "Do not state the full solution. "
        f"Puzzle id: {puzzle.get('id')}. Current: {summary}. "
        f"Unique solution (do not quote directly): {sols}."
    )
    try:
        if backend == "openai":
            key = os.environ.get("OPENAI_API_KEY")
            if not key:
                return None
            body = json.dumps(
                {
                    "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        if backend == "ollama":
            host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            model = os.environ.get("OLLAMA_MODEL", "llama3.2")
            body = json.dumps(
                {"model": model, "prompt": prompt, "stream": False}
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{host}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()
    except Exception as e:  # pragma: no cover
        log.debug("hint_llm: %s", e)
    return None
