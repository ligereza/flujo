#!/usr/bin/env python3
"""Build a read-only evidence index for inferential archaeology.

The module keeps extraction deterministic and reserves interpretation for a
later bounded model pass. SQLite FTS5 stores recoverable text evidence. DuckDB
stores relational events for cross-source analysis. Neither source is changed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sqlite3
import statistics
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLAUDE_ROOT = Path.home() / ".claude" / "projects" / "C--IA-flujo"
DEFAULT_CLAUDE_WEB = (
    Path.home() / "claude_sesiones_recuperadas" /
    "claude_web_export_2026-08-11"
)
DEFAULT_CLAUDE_MEMORY = (
    Path.home() / ".claude" / "projects" / "C--IA-flujo" / "memory"
)
DEFAULT_CODEX_ROOT = Path.home() / ".codex" / "sessions"
DEFAULT_OUTPUT = ROOT / "out" / "archaeology"
VSCODE_SOL_MODEL = "gpt-5.6-sol"

RULE_PATH = re.compile(
    r"(^|/)(AGENTS\.md|CLAUDE\.md|SKILL\.md|context/.*\.md|"
    r"docs/.*\.md|\.claude/.*\.md)$",
    re.IGNORECASE,
)
RULE_WORDS = re.compile(
    r"(?i)\b(must|never|always|required|do not|only|prohibited|invariant|"
    r"debe|nunca|siempre|obligad[ao]|regla|no tocar|no crear|solo|"
    r"innegociable|pendiente)\b"
)
FRUSTRATION_PATTERNS = (
    r"\brompiste\b", r"\bfalla(?:do|r)?\b", r"\bfall[oó]\b", r"\bbug\b",
    r"\berror\b", r"\bfrustr", r"\benojo\b", r"\bmolesta\b",
    r"\bte dije\b", r"\bno te dije\b", r"\bno me tomes\b",
    r"\botra vez\b", r"\bno entiendes\b", r"\bcalma\b",
)
DELEGATION_PATTERNS = (
    r"\bdale\b", r"\bhazlo\b", r"\bhaz tu\b", r"\bcontinua\b",
    r"\bte autorizo\b", r"\bsigue\b", r"\bencargate\b", r"\bpushea\b",
    r"\bdej[ae]lo trabajando\b", r"\bautonom", r"\bsolo\b",
)
PAUSE_PATTERNS = (
    r"\bdetente\b", r"\bpara\b", r"\bespera\b", r"\bantes de\b",
    r"\bno hagas\b", r"\bno edites\b", r"\bno toques\b",
)
QUESTION_PATTERNS = (
    r"\?", r"\bcomo\b", r"\bqué\b", r"\bque\b", r"\bcu[aá]l\b",
    r"\bpor qu[eé]\b", r"\bcu[aá]nto\b", r"\bpodr[ií]a\b",
)
IDEA_PATTERNS = (
    r"\bidea\b", r"\bideas\b", r"\bpodr[ií]amos\b",
    r"\bse me ocurre\b", r"\bpropongo\b", r"\bme gustar[ií]a\b",
    r"\bser[ií]a bueno\b", r"\by si\b", r"\bqu[eé] pasar[ií]a si\b",
    r"\bexplor", r"\bwhat if\b", r"\bwe could\b", r"\bi propose\b",
    r"\bi would like\b",
)
PROPOSAL_PATTERNS = (
    r"\bpropondre\b", r"\bpropongo\b", r"\bte propongo\b", r"\bpropuesta\b",
    r"\bimplementare\b", r"\bconstruire\b", r"\bcreare\b", r"\bagregare\b",
    r"\banadire\b", r"\bmejorare\b", r"\bintegrare\b", r"\bdesarrollare\b",
    r"\bpriorizare\b", r"\bhare\b", r"\bvoy a (?:crear|construir|implementar|"
    r"agregar|anadir|mejorar|integrar|priorizar|desarrollar)\b",
    r"\bthe next step\b", r"\bi propose\b", r"\bi will\b", r"\bi'll\b",
    r"\bi am going to\b",
)
OPEN_PROPOSAL_PATTERNS = (
    r"\bpropon mejoras\b", r"\bpropone?\b.*\bmejoras?\b",
    r"\bdame una propuesta\b", r"\bdame propuestas?\b", r"\bque propon(?:es|dr[ií]as)\b",
    r"\bque se te ocurre\b", r"\bideas tu\b", r"\btu propon\b",
    r"\bideas de cualquier tipo\b", r"\badelante.*propon\b",
    r"\bwhat do you propose\b", r"\bpropose improvements\b",
)
APPROVAL_PATTERNS = (
    r"\bdale\b", r"\bhazlo\b", r"\bhaz tu\b", r"\bcontinua\b",
    r"\bte autorizo\b", r"\bsigue\b", r"\badelante\b", r"\bimplementa\b",
    r"\bdo it\b", r"\bgo ahead\b", r"\bproceed\b",
)

CROSS_SOURCE_STOP_WORDS = {
    "ahora", "antes", "aparte", "aspecto", "bueno", "como", "con", "cual",
    "cuando", "debe", "desde", "donde", "esta", "este", "esto", "hace",
    "ideas", "igual", "mas", "mismo", "otra", "para", "podria", "porque",
    "primero", "quiero", "siento", "sobre", "tengo", "tambien", "tema", "todo",
    "vamos", "algo", "aqui", "bien", "cada", "capaz", "creo", "dame", "dentro",
    "deberia", "dejo", "despues", "entiendo", "forma", "funciona", "hacer",
    "mucho", "necesito", "parece", "parte", "podemos", "puede", "seria", "si",
    "siendo", "sin", "tanto", "tiene", "tienen", "tipo", "vamos", "your", "with",
    "that", "this", "from", "there", "would", "could", "about", "into", "have",
    "want", "need", "what", "where", "which", "while", "then", "than", "just",
    "bienvenido", "cualquier", "mejoras", "propon", "tienes", "adelante", "agregar",
    "abordo", "artistica", "contenido", "deje", "trabajamos", "acceso", "explorer",
    "carpeta", "tareas", "desempeno", "retomes", "terminar", "trabajo", "claude",
    "preguntas", "faltan", "manera", "mejor", "presenta", "presentacion", "ejemplo",
    "claro", "directo", "realmente", "realista", "exacto", "importante", "respecto",
    "replantea", "pero", "funcionan", "podrias", "elementos", "todos", "visual",
    "pregunta", "datos", "divida", "debuggin", "buscan", "ende", "areas", "leiste",
    "deptos", "alguna", "quedan", "explicacion", "perdi", "nomas", "dale", "minutos",
}
CROSS_SOURCE_KEEP_SHORT = {
    "aws", "azure", "gpt", "gpu", "hub", "llm", "mak", "rd", "svg", "xio",
}
CROSS_SOURCE_GENERIC_ANCHORS = {
    "mak", "portafolio", "repo", "hub", "research", "tools", "herramientas",
    "idea", "ideas", "win", "github", "archivo", "datos", "contenido",
}
SOL_MUTATING_TOOLS = {
    "copilot_applyPatch", "copilot_createFile", "copilot_deleteFile",
}
CLAUDE_MUTATING_TOOLS = {
    "Edit", "Write", "MultiEdit", "NotebookEdit",
}
CODEX_PATCH_TOOL = "apply_patch"

OUTCOME_ORDER = (
    "implemented_and_current",
    "implemented_but_abandoned",
    "approved_without_verified_execution",
    "user_idea_still_open",
    "agent_proposal_never_adopted",
)

POSSIBILITY_LANES = (
    {
        "lane_id": "micelio",
        "label": "Micelio / research as living substrate",
        "terms": ("micelio", "sustrato", "fructifero", "fructificacion", "materia"),
        "continuation_question": "Does research become a living material circuit, or only a document generator?",
    },
    {
        "lane_id": "cuaderno",
        "label": "Notebook / repo as memory and studio",
        "terms": ("cuaderno", "notebook", "memoria", "sesiones", "archivo", "olvido"),
        "continuation_question": "Can the archive become a working notebook without becoming another instruction layer?",
    },
    {
        "lane_id": "thi_ng",
        "label": "thi.ng / generative archive",
        "terms": ("thi.ng", "generative-art", "generativo", "rstream", "tags", "geometria"),
        "continuation_question": "What should be imported as a generative method rather than copied as an interface?",
    },
    {
        "lane_id": "portfolio_live",
        "label": "Living portfolio / visitor as computation",
        "terms": ("portafolio", "portfolio", "vivo", "visitante", "visita", "gpu", "cpu", "organismo"),
        "continuation_question": "Does the visitor alter the work's metabolism, or only trigger visual decoration?",
    },
    {
        "lane_id": "bounded_autonomy",
        "label": "Bounded autonomy / loops and departments",
        "terms": ("autonomia", "autonomo", "loop", "cron", "agente", "independencia", "capataz", "conductor"),
        "continuation_question": "Which decisions can MAK perform without erasing the human gate?",
    },
    {
        "lane_id": "svg_art",
        "label": "SVG / ASCII as executable artwork",
        "terms": ("svg", "ascii", "readme", "animacion", "frames", "vaso", "liquido", "vector"),
        "continuation_question": "Does the SVG remain an artwork and a readable surface under the runtime constraints?",
    },
    {
        "lane_id": "rd_post",
        "label": "RD / POST evidence into public material",
        "terms": ("post", "chemsex", "drogas", "testeos", "venue", "reactivo", "informe"),
        "continuation_question": "How can evidence become a public post without collapsing distinct identities or claims?",
    },
)
ACTION_PATH_PATTERN = re.compile(
    r"(?i)(?:file:///[^\s)`]+|[a-z]:[\\/][^\s)`]+|/home/mak/[^\s)`]+|"
    r"(?:cultura|src|tests|docs|data|tools|context)/[a-z0-9_./-]+)"
)


def _run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if result.returncode:
        raise RuntimeError("git failed: %s" % result.stderr.strip()[:400])
    return result.stdout


def _strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in text if not unicodedata.combining(char))


def _matches(text: str, patterns: Iterable[str]) -> list[str]:
    folded = _strip_accents(text)
    return [pattern for pattern in patterns if re.search(pattern, folded)]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def validate_interpretation(item: dict, result: dict) -> dict:
    """Apply a deterministic evidence gate after model interpretation.

    A nearby assistant reply is not an implementation artifact, and a removed
    rule line is not proof of why it was removed. The model reading remains
    intact under ``model_status``; ``validated_status`` is the status allowed
    into downstream archaeology.
    """
    checked = dict(result)
    model_status = checked.get("evidence_status")
    checked["model_status"] = model_status
    direct_evidence = bool(item.get("implementation_evidence"))
    if item.get("commit_evidence") and item.get("commit_link_method") not in (
        None, "lexical_subject_overlap_only"
    ):
        direct_evidence = True
    if item.get("kind") == "rule_eliminated_candidate":
        checked["validated_status"] = "insufficient"
        checked["validation_reason"] = "rule_text_change_does_not_explain_cause"
    elif item.get("kind") in ("idea", "agent_proposal") and not direct_evidence:
        checked["validated_status"] = "insufficient"
        checked["validation_reason"] = "no_direct_implementation_evidence_in_packet"
    else:
        checked["validated_status"] = model_status
        checked["validation_reason"] = "accepted_by_packet_evidence"
    return checked


def _iso(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, (int, float)) or (
        isinstance(value, str) and value.isdigit()
    ):
        number = float(value)
        seconds = number / 1000 if number > 100_000_000_000 else number
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return text


def load_turns(claude_root: Path) -> tuple[list[dict], list[str]]:
    """Reuse the established Claude Code extractor and retain its warnings."""
    sys.path.insert(0, str(ROOT / "tools"))
    from conversacion import leer_turnos

    turns, _types, _unknown, warnings = leer_turnos([claude_root])
    return turns, warnings


def load_claude_actions(claude_root: Path) -> tuple[list[dict], list[str]]:
    """Index direct Claude file mutations without adding conversation turns.

    ``conversacion.leer_turnos`` intentionally excludes non-text blocks. This
    companion index reads the same top-level JSONL files and keeps only direct
    file tools, so proposal evidence can distinguish a written file from a
    promise. It does not count prompts, messages, or memory files.
    """
    if not claude_root.exists():
        return [], ["claude_actions_root_missing:%s" % claude_root]
    files = sorted(claude_root.glob("*.jsonl"))
    actions: list[dict] = []
    warnings: list[str] = []
    for source_path in files:
        try:
            records = [json.loads(line) for line in source_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append("claude_actions_unreadable:%s:%s" % (source_path, exc))
            continue
        result_status: dict[str, str] = {}
        for record in records:
            message = record.get("message") if isinstance(record, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                tool_id = str(block.get("tool_use_id") or "")
                if tool_id:
                    result_status[tool_id] = (
                        "error" if block.get("is_error") else "ok"
                    )
        for line_number, record in enumerate(records, 1):
            if not isinstance(record, dict) or record.get("type") != "assistant":
                continue
            message = record.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tool_name = str(block.get("name") or "")
                if tool_name not in CLAUDE_MUTATING_TOOLS:
                    continue
                payload = block.get("input")
                payload = payload if isinstance(payload, dict) else {}
                raw_paths: list[str] = []
                for key in ("file_path", "notebook_path", "path"):
                    value = payload.get(key)
                    if isinstance(value, str) and value.strip():
                        raw_paths.append(value)
                raw_text = " ".join(raw_paths)
                paths = _action_paths(raw_text)
                for raw_path in raw_paths:
                    normalized = raw_path.replace("\\", "/")
                    if normalized not in paths:
                        paths.append(normalized)
                if not paths:
                    warnings.append(
                        "claude_action_without_path:%s:%s:%s" %
                        (source_path.name, line_number, tool_name)
                    )
                    continue
                tool_id = str(block.get("id") or "")
                actions.append({
                    "session_id": record.get("sessionId"),
                    "occurred_at": _iso(record.get("timestamp")),
                    "source_file": str(source_path),
                    "source_line": line_number,
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "paths": paths,
                    "result_status": result_status.get(tool_id, "unverified"),
                    "payload": _json(payload),
                })
    return actions, warnings


def _patch_paths(patch: str) -> list[str]:
    """Extract paths from the standard apply_patch envelope."""
    paths: list[str] = []
    seen: set[str] = set()
    for line in (patch or "").splitlines():
        match = re.match(
            r"^\*\*\*\s+(?:(?:Update|Add|Delete) File|Move to):\s+(.+?)\s*$",
            line,
        )
        if not match:
            continue
        path = match.group(1).strip().replace("\\", "/")
        if path and path not in seen:
            seen.add(path)
            paths.append(path)
    return paths


def load_codex_actions(root: Path, exclude_paths: set[Path] | None = None) -> tuple[list[dict], list[str]]:
    """Index successful or failed direct Codex ``apply_patch`` mutations.

    Codex stores tool calls as ``response_item`` records rather than Claude's
    ``message.content`` blocks. This keeps the action layer separate from the
    textual turn loader and records only explicit patch envelopes; arbitrary
    shell commands are not guessed to be mutations.
    """
    if not root.exists():
        return [], ["codex_actions_root_missing:%s" % root]
    excluded = {path.resolve() for path in (exclude_paths or set())}
    actions: list[dict] = []
    warnings: list[str] = []
    for source_path in sorted(root.rglob("*.jsonl")):
        if source_path.resolve() in excluded:
            continue
        session_id = source_path.stem
        try:
            records = [json.loads(line) for line in source_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append("codex_actions_unreadable:%s:%s" % (source_path, exc))
            continue
        outputs: dict[str, tuple[str, str]] = {}
        for record in records:
            payload = record.get("payload") if isinstance(record, dict) else None
            if not isinstance(payload, dict):
                continue
            if record.get("type") == "session_meta":
                session_id = str(payload.get("session_id") or session_id)
            if record.get("type") != "response_item":
                continue
            if payload.get("type") not in ("custom_tool_call_output", "function_call_output"):
                continue
            call_id = str(payload.get("call_id") or "")
            if call_id:
                output = str(payload.get("output") or "")
                status = "error" if re.search(
                    r"(?i)(?:exit code|return code)\s*:\s*(?!0\b)\d+|error|failed|traceback",
                    output,
                ) else "ok"
                outputs[call_id] = (status, output[:500])
        for line_number, record in enumerate(records, 1):
            if not isinstance(record, dict) or record.get("type") != "response_item":
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("type") != "custom_tool_call" or payload.get("name") != CODEX_PATCH_TOOL:
                continue
            call_id = str(payload.get("call_id") or "")
            patch = payload.get("input")
            if not isinstance(patch, str):
                warnings.append("codex_patch_non_text:%s:%s" % (source_path.name, line_number))
                continue
            paths = _patch_paths(patch)
            if not paths:
                warnings.append("codex_patch_without_path:%s:%s" % (source_path.name, line_number))
                continue
            result_status, output = outputs.get(call_id, ("unverified", ""))
            for path in paths:
                actions.append({
                    "session_id": session_id,
                    "occurred_at": _iso(record.get("timestamp")),
                    "source_file": str(source_path),
                    "source_line": line_number,
                    "tool_id": call_id,
                    "tool_name": CODEX_PATCH_TOOL,
                    "paths": [path],
                    "result_status": result_status,
                    "payload": _json({"patch": patch[:4000], "output": output}),
                })
    return actions, warnings


def _annotate_turn(turn: dict, source: str) -> dict:
    """Attach a stable source label without changing the recovered text."""
    row = dict(turn)
    row["source"] = source
    row["source_turn_id"] = str(turn.get("n", ""))
    return row


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _design_message_text(message: dict) -> str | None:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, dict) and isinstance(content.get("content"), str):
        return content["content"]
    return None


def load_claude_web(path: Path) -> tuple[list[dict], list[str]]:
    """Load recovered Claude web conversations and design chats.

    The generated HTML index and markdown summaries are intentionally not
    treated as chats: they are derivative views and would double-count source
    messages.
    """
    if not path.exists():
        return [], ["claude_web_missing:%s" % path]
    files: list[tuple[Path, str]] = []
    if path.is_dir():
        conversation_path = path / "conversations.json"
        if conversation_path.exists():
            files.append((conversation_path, "claude_web"))
        files.extend((item, "claude_design") for item in sorted((path / "design_chats").glob("*.json")))
    else:
        files.append((path, "claude_web"))
    turns: list[dict] = []
    warnings: list[str] = []
    for source_path, source in files:
        try:
            payload = _read_json(source_path)
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append("claude_web_unreadable:%s:%s" % (source_path, exc))
            continue
        conversations = payload if source == "claude_web" else [payload]
        if not isinstance(conversations, list):
            warnings.append("claude_web_invalid_root:%s" % source_path)
            continue
        for conversation in conversations:
            if not isinstance(conversation, dict):
                continue
            session_id = str(conversation.get("uuid") or source_path.stem)
            messages = conversation.get("chat_messages") if source == "claude_web" else conversation.get("messages")
            for index, message in enumerate(messages or [], 1):
                if not isinstance(message, dict):
                    continue
                sender = message.get("sender") if source == "claude_web" else message.get("role")
                role = ("user" if sender == "human" else "assistant" if sender == "assistant" else sender)
                if role not in ("user", "assistant"):
                    continue
                text = message.get("text") if source == "claude_web" else _design_message_text(message)
                if not isinstance(text, str) or not text.strip():
                    continue
                turns.append({
                    "n": index, "rol": role,
                    "clase": "humano" if role == "user" else "asistente",
                    "via": source, "ts": message.get("created_at"),
                    "sesion": session_id, "rama": None,
                    "archivo": str(source_path), "linea": index,
                    "chars": len(text), "sintetico": False, "texto": text,
                    "source": source,
                    "source_turn_id": str(message.get("uuid") or index),
                })
    return turns, warnings


def load_codex_sessions(root: Path, exclude_paths: set[Path] | None = None) -> tuple[list[dict], list[str]]:
    """Load textual user/assistant events from Codex rollout JSONL files.

    Event messages are used instead of response records so injected developer
    context and duplicated response items do not pollute the corpus.
    """
    if not root.exists():
        return [], ["codex_root_missing:%s" % root]
    turns: list[dict] = []
    warnings: list[str] = []
    excluded = {path.resolve() for path in (exclude_paths or set())}

    def is_machine_message(message: str) -> bool:
        """Reject tool protocol/status text from the conversational corpus."""
        stripped = message.strip()
        return (
            stripped.startswith(("[external_agent_tool_", "<heartbeat>"))
            or stripped in ("<EXTERNAL SESSION IMPORTED>", "No response requested.")
            or stripped.startswith(("API Error:", "You've hit", "You've reached"))
        )

    for path in sorted(root.rglob("*.jsonl")):
        if path.resolve() in excluded:
            continue
        session_id = path.stem
        branch = None
        try:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line_number, line in enumerate(handle, 1):
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        warnings.append("codex_invalid_json:%s:%s" % (path, line_number))
                        continue
                    payload = record.get("payload") or {}
                    if record.get("type") == "session_meta":
                        session_id = str(payload.get("session_id") or session_id)
                        branch = (payload.get("git") or {}).get("branch")
                        continue
                    if record.get("type") != "event_msg":
                        continue
                    event_type = payload.get("type")
                    if event_type not in ("user_message", "agent_message"):
                        continue
                    role = "user" if event_type == "user_message" else "assistant"
                    text = payload.get("message")
                    if not isinstance(text, str) or not text.strip():
                        continue
                    phase = payload.get("phase")
                    if role == "assistant" and (
                        is_machine_message(text) or
                        phase not in (None, "commentary", "final_answer")
                    ):
                        continue
                    turns.append({
                        "n": len(turns) + 1, "rol": role,
                        "clase": "humano" if role == "user" else "asistente",
                        "via": "codex", "ts": record.get("timestamp"),
                        "sesion": session_id, "rama": branch,
                        "archivo": str(path), "linea": line_number,
                        "chars": len(text), "sintetico": False, "texto": text,
                        "source": "codex",
                        "source_turn_id": "%s:%s" % (session_id, line_number),
                    })
        except OSError as exc:
            warnings.append("codex_unreadable:%s:%s" % (path, exc))
    return turns, warnings


def _vscode_set_path(root: Any, path: list[Any], value: Any) -> None:
    """Apply a VS Code chat-session state update at a JSON path."""
    if not path:
        return
    current = root
    for part in path[:-1]:
        try:
            current = current[part]
        except (KeyError, IndexError, TypeError):
            return
    leaf = path[-1]
    try:
        current[leaf] = value
    except (KeyError, IndexError, TypeError):
        return


def _vscode_append_path(root: Any, path: list[Any], value: Any) -> None:
    """Apply a VS Code JSONL append/extend event without interpreting tools."""
    if not path:
        return
    current = root
    try:
        for part in path:
            current = current[part]
    except (KeyError, IndexError, TypeError):
        return
    if not isinstance(current, list):
        return
    if isinstance(value, list):
        current.extend(value)
    else:
        current.append(value)


def _vscode_response_text(response: Any) -> str:
    """Keep assistant markdown chunks, dropping serialized tool protocol."""
    if not isinstance(response, list):
        return ""
    chunks: list[str] = []
    for item in response:
        if not isinstance(item, dict) or "kind" in item:
            continue
        value = item.get("value")
        if isinstance(value, str) and value.strip():
            chunks.append(value)
    return "\n".join(chunks).strip()


def _vscode_reconstruct(path: Path) -> tuple[dict | None, dict[int, int], list[str]]:
    """Reconstruct one VS Code chat session from its append-only JSONL log."""
    state: dict | None = None
    request_lines: dict[int, int] = {}
    warnings: list[str] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    warnings.append("vscode_invalid_json:%s:%s" % (path, line_number))
                    continue
                kind = record.get("kind")
                if kind == 0 and isinstance(record.get("v"), dict):
                    state = record["v"]
                    for index in range(len(state.get("requests") or [])):
                        request_lines[index] = line_number
                elif state is not None and kind == 1 and isinstance(record.get("k"), list):
                    _vscode_set_path(state, record["k"], record.get("v"))
                elif state is not None and kind == 2 and isinstance(record.get("k"), list):
                    key = record["k"]
                    if key == ["requests"] and isinstance(record.get("v"), list):
                        start = len(state.get("requests") or [])
                        _vscode_append_path(state, key, record["v"])
                        for index in range(start, start + len(record["v"])):
                            request_lines[index] = line_number
                    else:
                        _vscode_append_path(state, key, record.get("v"))
    except OSError as exc:
        warnings.append("vscode_unreadable:%s:%s" % (path, exc))
    return state, request_lines, warnings


def load_vscode_sol_sessions(roots: Iterable[Path] | None) -> tuple[list[dict], list[str]]:
    """Load exact user/assistant turns emitted by the VS Code SOL model.

    VS Code stores chat state as JSONL patches rather than one message per line.
    This loader reconstructs only request messages whose recorded model is SOL;
    tool invocations and repository snapshots remain provenance in the source
    file, not conversational turns. Copilot/Codex requests in mixed sessions
    are intentionally excluded to avoid attributing them to SOL.
    """
    if not roots:
        return [], []
    turns: list[dict] = []
    warnings: list[str] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            warnings.append("vscode_root_missing:%s" % root)
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*.jsonl"))
        for path in paths:
            path = path.resolve()
            if path in seen:
                continue
            seen.add(path)
            state, request_lines, session_warnings = _vscode_reconstruct(path)
            warnings.extend(session_warnings)
            if not state:
                continue
            session_id = str(state.get("sessionId") or path.stem)
            for request_index, request in enumerate(state.get("requests") or []):
                if not isinstance(request, dict):
                    continue
                model_id = str(request.get("modelId") or "")
                if VSCODE_SOL_MODEL not in model_id:
                    continue
                message = request.get("message") or {}
                user_text = message.get("text") if isinstance(message, dict) else None
                if not isinstance(user_text, str) or not user_text.strip():
                    continue
                request_id = str(request.get("requestId") or request_index)
                source_line = request_lines.get(request_index, 1)
                base = {
                    "via": "vscode", "sesion": session_id, "rama": None,
                    "archivo": str(path), "linea": source_line,
                    "sintetico": False, "source": "vscode_sol",
                    "model_id": model_id, "request_id": request_id,
                }
                turns.append({
                    **base, "rol": "user", "clase": "humano",
                    "ts": request.get("timestamp"),
                    "source_turn_id": "%s:%s:user" % (request_id, request_index),
                    "texto": user_text, "chars": len(user_text),
                })
                response_text = _vscode_response_text(request.get("response"))
                if response_text:
                    turns.append({
                        **base, "rol": "assistant", "clase": "asistente",
                        "ts": request.get("responseTimestamp") or request.get("timestamp"),
                        "source_turn_id": "%s:%s:assistant" % (request_id, request_index),
                        "texto": response_text, "chars": len(response_text),
                    })
    return turns, warnings


def _vscode_text_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("value", "text", "label"):
            if isinstance(value.get(key), str):
                return value[key]
    return ""


def load_vscode_sol_metrics(
    roots: Iterable[Path] | None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Extract compact request/tool evidence without storing tool dumps."""
    requests: list[dict] = []
    actions: list[dict] = []
    warnings: list[str] = []
    if not roots:
        return requests, actions, warnings
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            warnings.append("vscode_root_missing:%s" % root)
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*.jsonl"))
        for path in paths:
            path = path.resolve()
            if path in seen:
                continue
            seen.add(path)
            state, request_lines, session_warnings = _vscode_reconstruct(path)
            warnings.extend(session_warnings)
            if not state:
                continue
            session_id = str(state.get("sessionId") or path.stem)
            for request_index, request in enumerate(state.get("requests") or []):
                if not isinstance(request, dict):
                    continue
                model_id = str(request.get("modelId") or "")
                if VSCODE_SOL_MODEL not in model_id:
                    continue
                request_id = str(request.get("requestId") or request_index)
                response = request.get("response") or []
                tool_count = 0
                for event_index, item in enumerate(response):
                    if not isinstance(item, dict):
                        continue
                    event_kind = str(item.get("kind") or "")
                    tool_id = str(item.get("toolId") or "")
                    if event_kind == "toolInvocationSerialized" or tool_id:
                        tool_count += 1
                    if not event_kind and not tool_id:
                        continue
                    invocation = _vscode_text_value(item.get("invocationMessage"))
                    past = _vscode_text_value(item.get("pastTenseMessage"))
                    message = invocation or past or _vscode_text_value(
                        item.get("message") or item.get("content")
                    )
                    actions.append({
                        "session_id": session_id, "request_id": request_id,
                        "model_id": model_id,
                        "occurred_at": _iso(request.get("responseTimestamp") or request.get("timestamp")),
                        "source_file": str(path),
                        "source_line": request_lines.get(request_index, 1),
                        "event_index": event_index, "event_kind": event_kind or "event",
                        "tool_id": tool_id, "invocation": invocation,
                        "past_tense": past,
                        "is_complete": int(bool(item.get("isComplete"))),
                        "payload": _json({
                            key: item.get(key) for key in (
                                "kind", "toolId", "toolCallId", "isComplete", "done"
                            ) if key in item
                        }),
                        "message": message,
                    })
                requests.append({
                    "session_id": session_id, "request_id": request_id,
                    "model_id": model_id,
                    "requested_at": _iso(request.get("timestamp")),
                    "responded_at": _iso(request.get("responseTimestamp")),
                    "source_file": str(path),
                    "source_line": request_lines.get(request_index, 1),
                    "prompt_tokens": int(request.get("promptTokens") or 0),
                    "completion_tokens": int(request.get("completionTokens") or 0),
                    "elapsed_ms": int(request.get("elapsedMs") or 0),
                    "response_items": len(response) if isinstance(response, list) else 0,
                    "assistant_chars": len(_vscode_response_text(response)),
                    "tool_invocations": tool_count,
                })
    return requests, actions, warnings


def load_all_turns(claude_root: Path, claude_web: Path | None,
                   codex_root: Path | None,
                   codex_exclude: set[Path] | None = None,
                   vscode_roots: Iterable[Path] | None = None) -> tuple[list[dict], list[str], dict]:
    """Load all available chat sources while retaining source boundaries."""
    code_turns, warnings = load_turns(claude_root)
    turns = [_annotate_turn(turn, "claude_code") for turn in code_turns]
    source_counts = collections.Counter({"claude_code": len(turns)})
    if claude_web:
        web_turns, web_warnings = load_claude_web(claude_web)
        turns.extend(web_turns)
        warnings.extend(web_warnings)
        source_counts["claude_web"] += len(web_turns)
    if codex_root:
        codex_turns, codex_warnings = load_codex_sessions(codex_root, codex_exclude)
        turns.extend(codex_turns)
        warnings.extend(codex_warnings)
        source_counts["codex"] += len(codex_turns)
    if vscode_roots:
        vscode_turns, vscode_warnings = load_vscode_sol_sessions(vscode_roots)
        turns.extend(vscode_turns)
        warnings.extend(vscode_warnings)
        source_counts["vscode_sol"] += len(vscode_turns)
    # The global id is an index for joins; source_turn_id remains recoverable.
    def sort_key(item: dict) -> tuple:
        stamp = _iso(item.get("ts"))
        return (stamp is None, stamp or "", item.get("source", ""),
                str(item.get("source_turn_id", "")))
    turns.sort(key=sort_key)
    for index, turn in enumerate(turns, 1):
        turn["n"] = index
    dedup_counts = deduplicate_turns(turns)
    unique_counts = collections.Counter(
        turn.get("source", "unknown") for turn in turns if not turn["is_duplicate"]
    )
    analysis_counts = collections.Counter(
        turn.get("source", "unknown") for turn in turns
        if not turn["is_duplicate"] and not turn["analysis_exclusion"]
    )
    excluded_counts = collections.Counter(
        turn["analysis_exclusion"] for turn in turns if turn["analysis_exclusion"]
    )
    return turns, warnings, {
        "raw": dict(source_counts), "unique": dict(unique_counts),
        "analysis": dict(analysis_counts),
        "duplicates": dedup_counts.get("duplicates", 0),
        "analysis_excluded": dict(excluded_counts),
    }


def load_mak_activity(path: Path | None) -> tuple[list[dict], list[str]]:
    """Load MAK's append-only activity inventory without treating it as truth."""
    if path is None:
        return [], []
    if not path.exists():
        return [], ["mak_activity_missing:%s" % path]
    rows: list[dict] = []
    warnings: list[str] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    warnings.append("mak_activity_invalid_json:%s" % line_number)
                    continue
                if not isinstance(row, dict) or not row.get("activity_id"):
                    warnings.append("mak_activity_invalid_row:%s" % line_number)
                    continue
                rows.append({
                    "activity_id": str(row.get("activity_id")),
                    "ts": int(row.get("ts", 0) or 0),
                    "kind": str(row.get("kind", "")),
                    "status": str(row.get("status", "")),
                    "trigger": str(row.get("trigger", "")),
                    "caller": str(row.get("caller", "")),
                    "queue": str(row.get("queue", "")),
                    "department": str(row.get("department", "")),
                    "job_id": str(row.get("job_id", "")),
                    "provider": str(row.get("provider", "")),
                    "model": str(row.get("model", "")),
                    "resource": str(row.get("resource", "")),
                    "payload": _json(row),
                })
    except OSError as exc:
        warnings.append("mak_activity_unreadable:%s:%s" % (path, exc))
    return rows, warnings


def load_memories(root: Path | None) -> tuple[list[dict], list[str]]:
    """Load project-scoped Claude memory as a separate exact-text corpus."""
    if root is None:
        return [], []
    if not root.exists():
        return [], ["claude_memory_missing:%s" % root]
    rows: list[dict] = []
    warnings: list[str] = []
    for path in sorted(root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat()
        except OSError as exc:
            warnings.append("claude_memory_unreadable:%s:%s" % (path, exc))
            continue
        frontmatter = text[:1200]
        node_match = re.search(r"(?mi)^\s*node_type:\s*([^\n]+)", frontmatter)
        session_match = re.search(r"(?mi)^\s*originSessionId:\s*([^\n]+)", frontmatter)
        rows.append({
            "path": str(path), "relative_path": str(path.relative_to(root)),
            "node_type": node_match.group(1).strip() if node_match else "unknown",
            "origin_session": session_match.group(1).strip() if session_match else "",
            "modified_at": modified, "chars": len(text), "text": text,
        })
    return rows, warnings


def _dedupe_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _analysis_exclusion(turn: dict) -> str | None:
    if turn.get("sintetico"):
        return "source_marked_synthetic"
    if turn.get("source") in ("claude_code", "codex", "vscode_sol"):
        text = turn.get("texto", "").lstrip()
        if text.startswith((
            "<task-notification", "<environment_context",
            "<turn_aborted", "<in-app-browser-context",
            "<multi_agent_mode", "<command-name",
            "[Request interrupted", "[Terminal ", "Base directory for this skill:",
        )):
            return "protocol_or_injected_context"
        if turn.get("source") == "vscode_sol" and text.startswith("@agent Continue:"):
            return "protocol_or_injected_context"
        if text.startswith("This session is being continued from a previous conversation"):
            return "context_summary"
    return None


def deduplicate_turns(turns: list[dict]) -> dict[str, int]:
    """Mark exact record copies without collapsing repeated ideas over time.

    A cross-source duplicate requires the same role, timestamp, and normalized
    text. Identical wording in two different moments remains two turns. Every
    retained row keeps its fingerprint and duplicate pointer for auditability.
    """
    by_record: dict[str, int] = {}
    by_cross_source: dict[str, int] = {}
    counts = collections.Counter()
    for turn in turns:
        record_key = "\0".join((
            turn.get("source", ""), turn.get("sesion", ""),
            turn.get("source_turn_id", ""), turn.get("rol", ""),
        ))
        record_fingerprint = _digest(record_key)
        occurred_at = _iso(turn.get("ts"))
        text = _dedupe_text(turn.get("texto", ""))
        cross_fingerprint = None
        if occurred_at and text:
            cross_key = "\0".join((turn.get("rol", ""), occurred_at, text))
            cross_fingerprint = _digest(cross_key)
        turn["record_fingerprint"] = record_fingerprint
        turn["cross_source_fingerprint"] = cross_fingerprint
        turn["is_duplicate"] = False
        turn["duplicate_of"] = None
        turn["duplicate_reason"] = None
        turn["analysis_exclusion"] = _analysis_exclusion(turn)
        canonical = by_record.get(record_fingerprint)
        reason = "same_record"
        if canonical is None and cross_fingerprint:
            canonical = by_cross_source.get(cross_fingerprint)
            reason = "same_content_timestamp"
        if canonical is not None:
            turn["is_duplicate"] = True
            turn["duplicate_of"] = canonical
            turn["duplicate_reason"] = reason
            counts["duplicates"] += 1
        else:
            by_record[record_fingerprint] = turn["n"]
            if cross_fingerprint:
                by_cross_source[cross_fingerprint] = turn["n"]
            counts["unique"] += 1
    return dict(counts)


def load_git(repo: Path) -> tuple[list[dict], list[dict]]:
    """Read commit and file events from all refs without mutating the repo."""
    raw = _run_git(repo, [
        "log", "--all", "--date=iso-strict",
        "--format=COMMIT\t%H\t%aI\t%cI\t%an\t%s", "--numstat",
    ])
    commits: dict[str, dict] = {}
    files: list[dict] = []
    current: dict | None = None
    for line in raw.splitlines():
        if line.startswith("COMMIT\t"):
            fields = line.split("\t", 5)
            if len(fields) != 6:
                current = None
                continue
            _, sha, authored, committed, author, subject = fields
            current = {
                "sha": sha, "authored_at": authored, "committed_at": committed,
                "author": author, "subject": subject, "files": 0,
                "insertions": 0, "deletions": 0,
            }
            commits[sha] = current
            continue
        if current is None or not line or line.startswith("-"):  # binary/metadata
            continue
        fields = line.split("\t", 2)
        if len(fields) != 3 or not fields[0].isdigit() or not fields[1].isdigit():
            continue
        additions, deletions, path = fields
        rename_parts = _split_git_rename_path(path)
        normalized_path = rename_parts[1] if rename_parts else path
        hinted_old_path = rename_parts[0] if rename_parts else None
        row = {
            "sha": current["sha"], "path": normalized_path,
            "status": "R" if rename_parts else "?",
            "old_path": hinted_old_path,
            "additions": int(additions), "deletions": int(deletions),
        }
        files.append(row)
        current["files"] += 1
        current["insertions"] += int(additions)
        current["deletions"] += int(deletions)
    statuses = _run_git(repo, [
        "log", "--all", "--format=COMMIT\t%H", "--name-status",
    ])
    status_by_path: dict[tuple[str, str], tuple[str, str | None]] = {}
    status_commit: str | None = None
    for line in statuses.splitlines():
        if line.startswith("COMMIT\t"):
            status_commit = line.split("\t", 1)[1]
            continue
        if not status_commit or not line or line.startswith((" ", "{")):
            continue
        fields = line.split("\t")
        status = fields[0]
        if status.startswith(("R", "C")) and len(fields) >= 3:
            status_by_path[(status_commit, fields[2])] = (status[0], fields[1])
        elif len(fields) >= 2:
            status_by_path[(status_commit, fields[1])] = (status[0], None)
    for row in files:
        status, old_path = status_by_path.get(
            (row["sha"], row["path"]),
            (row.get("status", "?"), row.get("old_path")),
        )
        row["status"] = status
        row["old_path"] = old_path or row.get("old_path")
    return list(commits.values()), files


def _split_git_rename_path(path: str) -> tuple[str, str] | None:
    """Normalize Git's compact rename notation from numstat output."""
    if " => " not in path:
        return None
    if "{" in path and "}" in path:
        start = path.find("{")
        end = path.rfind("}")
        inner = path[start + 1:end]
        if " => " in inner:
            old, new = inner.split(" => ", 1)
            prefix, suffix = path[:start], path[end + 1:]
            return prefix + old + suffix, prefix + new + suffix
    old, new = path.split(" => ", 1)
    return old, new


def _time_bucket(value: str | None, granularity: str) -> str | None:
    stamp = _iso(value)
    if not stamp:
        return None
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError:
        return None
    if granularity == "minute":
        parsed = parsed.replace(second=0, microsecond=0)
    elif granularity == "hour":
        parsed = parsed.replace(minute=0, second=0, microsecond=0)
    elif granularity == "day":
        parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError("unknown time granularity: %s" % granularity)
    return parsed.isoformat()


def build_git_cadence(commits: list[dict], files: list[dict]) -> list[dict]:
    """Aggregate local commit activity by minute, hour, and day."""
    file_counts: collections.Counter = collections.Counter()
    for row in files:
        file_counts[row["sha"]] += 1
    buckets: dict[tuple[str, str], dict] = {}
    for commit in commits:
        for granularity in ("minute", "hour", "day"):
            bucket = _time_bucket(commit.get("authored_at"), granularity)
            if not bucket:
                continue
            key = (granularity, bucket)
            row = buckets.setdefault(key, {
                "granularity": granularity, "bucket": bucket,
                "commit_count": 0, "author_count": set(), "file_count": 0,
                "insertions": 0, "deletions": 0,
            })
            row["commit_count"] += 1
            row["author_count"].add(commit.get("author"))
            row["file_count"] += file_counts[commit["sha"]]
            row["insertions"] += commit["insertions"]
            row["deletions"] += commit["deletions"]
    return [
        {**row, "author_count": len(row["author_count"])}
        for row in sorted(buckets.values(), key=lambda item: (item["granularity"], item["bucket"]))
    ]


def load_rule_events(repo: Path, files: list[dict]) -> list[dict]:
    """Extract candidate rule additions/removals from changed rule documents."""
    by_commit: dict[str, list[str]] = collections.defaultdict(list)
    for row in files:
        path = row["path"].replace("\\", "/")
        if RULE_PATH.search(path):
            by_commit[row["sha"]].append(path)
    events: list[dict] = []
    for sha, paths in by_commit.items():
        try:
            diff = _run_git(repo, ["show", "--format=", "--unified=0", sha, "--", *sorted(set(paths))])
        except RuntimeError:
            continue
        active_path = None
        for line in diff.splitlines():
            if line.startswith("diff --git "):
                match = re.search(r" b/(.+)$", line)
                active_path = match.group(1) if match else None
                continue
            if not active_path or line.startswith(("+++", "---", "@@")):
                continue
            sign = line[:1]
            text = line[1:].strip() if sign in "+-" else ""
            if sign not in "+-" or not text or not RULE_WORDS.search(text):
                continue
            events.append({
                "sha": sha, "path": active_path,
                "event_kind": "rule_introduced" if sign == "+" else "rule_eliminated_candidate",
                "text": text,
            })
    return events


def classify_turns(turns: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Produce conservative lexical candidates; no semantic verdict is made."""
    signals: list[dict] = []
    candidates: list[dict] = []
    for turn in turns:
        text = turn["texto"]
        signal_groups = {
            "frustration_hotspot": _matches(text, FRUSTRATION_PATTERNS),
            "delegation_candidate": _matches(text, DELEGATION_PATTERNS),
            "pause_or_scope_signal": _matches(text, PAUSE_PATTERNS),
        }
        for kind, matches in signal_groups.items():
            if not matches:
                continue
            signals.append({
                "turn_id": turn["n"], "signal_kind": kind,
                "score": min(1.0, 0.35 + 0.15 * len(matches)),
                "evidence": _json(matches), "method": "lexical_candidate",
            })
            candidates.append({
                "seed_kind": kind, "turn_id": turn["n"],
                "score": min(1.0, 0.35 + 0.15 * len(matches)),
                "evidence": _json({"matches": matches}),
            })
        if turn["rol"] == "user" and _matches(text, QUESTION_PATTERNS):
            candidates.append({
                "seed_kind": "question_candidate", "turn_id": turn["n"],
                "score": 0.25 if "?" not in text else 0.6,
                "evidence": _json({"question_mark": "?" in text}),
            })
        if turn["rol"] == "user":
            idea_matches = _matches(text, IDEA_PATTERNS)
            if idea_matches:
                signals.append({
                    "turn_id": turn["n"], "signal_kind": "idea_candidate",
                    "score": min(1.0, 0.35 + 0.15 * len(idea_matches)),
                    "evidence": _json(idea_matches), "method": "lexical_candidate",
                })
                candidates.append({
                    "seed_kind": "idea_candidate", "turn_id": turn["n"],
                    "score": min(1.0, 0.35 + 0.15 * len(idea_matches)),
                    "evidence": _json({"matches": idea_matches}),
                })
    return signals, candidates, _question_links(turns)


def _question_links(turns: list[dict]) -> list[dict]:
    by_session: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for turn in turns:
        if turn.get("sesion"):
            by_session[(turn.get("source", ""), turn["sesion"])].append(turn)
    links: list[dict] = []
    for session_turns in by_session.values():
        for index, turn in enumerate(session_turns):
            if turn["rol"] != "user" or not _matches(turn["texto"], QUESTION_PATTERNS):
                continue
            next_assistant = next(
                (item for item in session_turns[index + 1:] if item["rol"] == "assistant"),
                None,
            )
            links.append({
                "turn_id": turn["n"],
                "response_turn_id": next_assistant["n"] if next_assistant else None,
                "response_present": bool(next_assistant),
                "status": "mechanically_unresolved" if next_assistant is None else "needs_interpretation",
            })
    return links


def build_session_profiles(turns: list[dict], commits: list[dict], signals: list[dict]) -> list[dict]:
    by_session: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    signal_counts: collections.Counter = collections.Counter()
    for signal in signals:
        signal_counts[(signal["turn_id"], signal["signal_kind"])] += 1
    for turn in turns:
        if turn.get("sesion"):
            by_session[(turn.get("source", ""), turn["sesion"])].append(turn)
    profiles = []
    for (source, session_id), items in by_session.items():
        humans = [item for item in items if item["clase"] == "humano"]
        assistants = [item for item in items if item["rol"] == "assistant"]
        stamps = [_iso(item.get("ts")) for item in items if item.get("ts")]
        stamps = sorted(stamp for stamp in stamps if stamp)
        start = stamps[0] if stamps else None
        end = stamps[-1] if stamps else None
        commit_count = 0
        if start and end:
            for commit in commits:
                stamp = _iso(commit.get("authored_at"))
                if stamp and start <= stamp <= end:
                    commit_count += 1
        frustration = sum(signal_counts[(item["n"], "frustration_hotspot")] for item in items)
        delegation = sum(signal_counts[(item["n"], "delegation_candidate")] for item in items)
        pauses = sum(signal_counts[(item["n"], "pause_or_scope_signal")] for item in items)
        ratio = len(humans) / len(assistants) if assistants else None
        mode = "ordinary"
        if frustration:
            mode = "friction_hotspot"
        elif delegation and ratio is not None and ratio <= 0.2:
            mode = "delegation_low_interaction"
        elif delegation:
            mode = "delegation_candidate"
        profiles.append({
            "source": source, "session_id": session_id, "start": start, "end": end,
            "human_turns": len(humans), "assistant_turns": len(assistants),
            "human_assistant_ratio": ratio, "frustration_hits": frustration,
            "delegation_hits": delegation, "pause_hits": pauses,
            "commits_in_window": commit_count, "mode_candidate": mode,
        })
    return profiles


def build_idea_followups(turns: list[dict], candidates: list[dict],
                         commits: list[dict]) -> list[dict]:
    """Link idea candidates to nearby replies and measurable git activity.

    This is deliberately a follow-up queue. Absence of a matching commit is
    not proof that an idea was abandoned: work may have happened elsewhere or
    remained conceptual.
    """
    by_id = {turn["n"]: turn for turn in turns}
    by_session: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for turn in turns:
        by_session[(turn.get("source", ""), turn.get("sesion", ""))].append(turn)
    rows: list[dict] = []
    for candidate in candidates:
        if candidate["seed_kind"] != "idea_candidate":
            continue
        turn = by_id.get(candidate.get("turn_id"))
        if not turn:
            continue
        session_key = (turn.get("source", ""), turn.get("sesion", ""))
        session_turns = by_session[session_key]
        position = next((i for i, item in enumerate(session_turns)
                         if item["n"] == turn["n"]), -1)
        response = next(
            (item for item in session_turns[position + 1:]
             if item["rol"] == "assistant"), None
        )
        stamp = _iso(turn.get("ts"))
        session_stamps = sorted(
            _iso(item.get("ts")) for item in session_turns if _iso(item.get("ts"))
        )
        session_start = session_stamps[0] if session_stamps else stamp
        session_end = session_stamps[-1] if session_stamps else stamp
        session_commits = []
        if session_start and session_end:
            session_commits = [
                commit for commit in commits
                if _iso(commit.get("authored_at")) and
                session_start <= _iso(commit.get("authored_at")) <= session_end
            ]
        idea_words = set(re.findall(r"[a-z0-9_]{5,}", _strip_accents(turn["texto"])))
        stop_words = {
            "tengo", "otra", "idea", "quiero", "puede", "podemos", "hacer",
            "desde", "para", "como", "sobre", "esta", "esto", "that", "with",
            "would", "could", "there", "their",
        }
        idea_words -= stop_words
        matching_commits = []
        for commit in session_commits:
            subject_words = set(re.findall(
                r"[a-z0-9_]{5,}", _strip_accents(commit.get("subject", ""))
            )) - stop_words
            if idea_words & subject_words:
                matching_commits.append(commit)
        rows.append({
            "turn_id": turn["n"], "source": turn.get("source"),
            "session_id": turn.get("sesion"), "idea_timestamp": stamp,
            "response_turn_id": response["n"] if response else None,
            "response_present": bool(response),
            "session_commit_count": len(session_commits),
            "matching_commit_count": len(matching_commits),
            "matching_commit_shas": [commit["sha"] for commit in matching_commits],
            "status": "needs_semantic_link" if response else "no_response_in_session",
            "evidence": _json({
                "idea_text": turn["texto"][:240],
                "response_text": response["texto"][:240] if response else None,
                "candidate_score": candidate["score"],
                "session_window": [session_start, session_end],
            }),
        })
    return rows


def safe_artifact_path(repo: Path, raw_path: str | Path, label: str) -> Path:
    """Resolve a generated artifact path without allowing source overwrite.

    Artifacts may be written outside the repository (normally under ``/tmp``)
    or under the ignored ``repo/out`` projection tree. A path anywhere else
    inside the repository is a source surface and is rejected before any
    history or session input is loaded. Resolving symlinks first also prevents
    an apparently safe path from redirecting into ``data`` or ``context``.
    """
    root = repo.resolve()
    path = Path(raw_path).expanduser().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return path
    try:
        path.relative_to((root / "out").resolve())
    except ValueError as exc:
        raise RuntimeError(
            "%s must be outside the repository or under repo/out: %s"
            % (label, path)
        ) from exc
    return path


def _proposal_action_rows(turn: dict, vscode_actions: list[dict] | None,
                          repo: Path | None,
                          claude_actions: list[dict] | None = None,
                          action_end: str | None = None,
                          codex_actions: list[dict] | None = None) -> list[dict]:
    """Recover direct mutation actions for one proposal request.

    SOL actions are keyed by request id. Claude actions are bounded by session
    and time because the conversation extractor intentionally omits tool
    blocks. Failed Claude edits remain in the action index but are excluded
    from direct implementation evidence.
    """
    if turn.get("source") == "vscode_sol":
        if not vscode_actions:
            return []
        request_id = str(turn.get("source_turn_id", "")).split(":", 1)[0]
        candidates = [action for action in vscode_actions
                      if action.get("request_id") == request_id]
    elif turn.get("source") in ("claude_code", "codex"):
        action_pool = (claude_actions if turn.get("source") == "claude_code"
                       else codex_actions)
        if not action_pool:
            return []
        start = _iso(turn.get("ts"))
        candidates = []
        for action in action_pool:
            if action.get("session_id") != turn.get("sesion"):
                continue
            occurred_at = action.get("occurred_at")
            if start and occurred_at and occurred_at < start:
                continue
            if action_end and occurred_at and occurred_at > action_end:
                continue
            candidates.append(action)
    else:
        return []
    rows: list[dict] = []
    for action in candidates:
        tool_id = action.get("tool_id")
        tool_name = action.get("tool_name")
        if turn.get("source") == "vscode_sol" and tool_id not in SOL_MUTATING_TOOLS:
            continue
        if turn.get("source") in ("claude_code", "codex"):
            allowed = (CLAUDE_MUTATING_TOOLS if turn.get("source") == "claude_code"
                       else {CODEX_PATCH_TOOL})
            if tool_name not in allowed:
                continue
            if action.get("result_status") == "error":
                continue
        message = " ".join(str(action.get(key) or "") for key in (
            "invocation", "past_tense", "message", "tool_name", "payload"
        ))
        paths = [
            relative for path in (action.get("paths") or _action_paths(message))
            if (relative := _relative_action_path(path, repo))
        ]
        if not paths:
            continue
        rows.append({
            "action_id": action.get("event_index") or tool_id,
            "tool_id": tool_id,
            "tool_name": tool_name,
            "occurred_at": action.get("occurred_at"),
            "source_file": action.get("source_file"),
            "source_line": action.get("source_line"),
            "paths": paths,
            "message": message[:500],
            "result_status": action.get("result_status", "unverified"),
        })
    return rows


def build_proposal_followups(turns: list[dict], commits: list[dict],
                             vscode_actions: list[dict] | None = None,
                             repo: Path | None = None,
                             claude_actions: list[dict] | None = None,
                             codex_actions: list[dict] | None = None) -> list[dict]:
    """Track agent-originated proposals without attributing them to the user.

    An open user request can produce a large assistant proposal before any
    concrete work starts. This table preserves that authorship boundary and
    records later approval, direct mutation actions, and only weak temporal Git
    echoes. None of those signals alone proves that a proposal was completed.
    """
    by_session: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
    for turn in turns:
        by_session[(turn.get("source", ""), turn.get("sesion", ""))].append(turn)
    rows: list[dict] = []
    stop_words = {
        "tengo", "otra", "idea", "quiero", "puede", "podemos", "hacer",
        "desde", "para", "como", "sobre", "esta", "esto", "that", "with",
        "would", "could", "there", "their", "propongo", "propuesta",
        "implementare", "voy", "crear", "construir", "agregar", "anadir",
    }
    for session_key, session_turns in by_session.items():
        for index, turn in enumerate(session_turns):
            if turn.get("rol") != "assistant":
                continue
            proposal_matches = _matches(turn.get("texto", ""), PROPOSAL_PATTERNS)
            if not proposal_matches:
                continue
            prior_user = next(
                (item for item in reversed(session_turns[:index])
                 if item.get("rol") == "user"), None
            )
            next_user = next(
                (item for item in session_turns[index + 1:]
                 if item.get("rol") == "user"), None
            )
            prompt_text = prior_user.get("texto", "") if prior_user else ""
            prompt_driven = bool(prior_user and _matches(
                prompt_text, OPEN_PROPOSAL_PATTERNS
            ))
            approval_present = bool(next_user and _matches(
                next_user.get("texto", ""), APPROVAL_PATTERNS
            ))
            next_user_index = next(
                (candidate_index for candidate_index, candidate in enumerate(
                    session_turns[index + 1:], index + 1
                ) if candidate.get("rol") == "user"),
                None,
            )
            action_end = None
            if next_user_index is not None:
                boundary_start = next_user_index + 1 if approval_present else next_user_index
                boundary = next(
                    (candidate for candidate in session_turns[boundary_start:]
                     if candidate.get("rol") == "user"),
                    None,
                )
                action_end = _iso(boundary.get("ts")) if boundary else None
            direct_actions = _proposal_action_rows(
                turn, vscode_actions, repo, claude_actions, action_end,
                codex_actions
            )
            stamp = _iso(turn.get("ts"))
            end_stamp = _iso(next_user.get("ts")) if next_user else None
            if not end_stamp:
                end_stamp = stamp
            session_commits = [
                commit for commit in commits
                if stamp and end_stamp and _iso(commit.get("authored_at")) and
                stamp <= _iso(commit.get("authored_at")) <= end_stamp
            ]
            proposal_words = set(re.findall(
                r"[a-z0-9_]{5,}", _strip_accents(turn.get("texto", ""))
            )) - stop_words
            matching_commits = []
            for commit in session_commits:
                subject_words = set(re.findall(
                    r"[a-z0-9_]{5,}", _strip_accents(commit.get("subject", ""))
                )) - stop_words
                if proposal_words & subject_words:
                    matching_commits.append(commit)
            if direct_actions:
                status = "direct_action_candidate"
            elif prompt_driven and not approval_present:
                status = "prompt_generated_unaccepted"
            elif approval_present:
                status = "accepted_without_direct_action"
            else:
                status = "agent_proposal_pending_review"
            rows.append({
                "turn_id": turn["n"], "source": turn.get("source"),
                "session_id": turn.get("sesion"), "proposal_timestamp": stamp,
                "trigger_turn_id": prior_user.get("n") if prior_user else None,
                "prompt_driven": int(prompt_driven),
                "approval_turn_id": next_user.get("n") if next_user else None,
                "approval_present": int(approval_present),
                "direct_action_count": len(direct_actions),
                "session_commit_count": len(session_commits),
                "matching_commit_count": len(matching_commits),
                "matching_commit_shas": [item["sha"] for item in matching_commits],
                "status": status,
                "evidence": _json({
                    "proposal_matches": proposal_matches,
                    "proposal_text": turn.get("texto", "")[:500],
                    "trigger_text": prompt_text[:300] if prior_user else None,
                    "approval_text": next_user.get("texto", "")[:300]
                    if next_user else None,
                    "direct_actions": direct_actions,
                    "session_window": [stamp, end_stamp],
                    "limits": [
                        "agent proposal is not user authorship",
                        "approval is not implementation",
                        "lexical or temporal commits are not completion proof",
                    ],
                }),
            })
    return rows


def _create_sqlite(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE turns (
            id INTEGER PRIMARY KEY, source TEXT NOT NULL, session_id TEXT,
            source_turn_id TEXT,
            record_fingerprint TEXT NOT NULL, cross_source_fingerprint TEXT,
            is_duplicate INTEGER NOT NULL, duplicate_of INTEGER,
            duplicate_reason TEXT,
            analysis_exclusion TEXT,
            role TEXT NOT NULL, actor_class TEXT, occurred_at TEXT, branch TEXT,
            source_file TEXT, source_line INTEGER, prompt_source TEXT,
            synthetic INTEGER NOT NULL, chars INTEGER NOT NULL, text TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE turns_fts USING fts5(
            text, content='turns', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TABLE git_commits (
            sha TEXT PRIMARY KEY, authored_at TEXT, committed_at TEXT,
            author TEXT, subject TEXT, files INTEGER, insertions INTEGER,
            deletions INTEGER
        );
        CREATE TABLE git_files (
            sha TEXT NOT NULL, path TEXT NOT NULL, status TEXT NOT NULL,
            old_path TEXT, additions INTEGER, deletions INTEGER
        );
        CREATE TABLE git_cadence (
            granularity TEXT NOT NULL, bucket TEXT NOT NULL,
            commit_count INTEGER NOT NULL, author_count INTEGER NOT NULL,
            file_count INTEGER NOT NULL, insertions INTEGER NOT NULL,
            deletions INTEGER NOT NULL,
            PRIMARY KEY (granularity, bucket)
        );
        CREATE TABLE mak_activity (
            row_id INTEGER PRIMARY KEY, activity_id TEXT NOT NULL, ts INTEGER NOT NULL,
            kind TEXT, status TEXT, trigger TEXT, caller TEXT, queue TEXT,
            department TEXT, job_id TEXT, provider TEXT, model TEXT,
            resource TEXT, payload TEXT NOT NULL
        );
        CREATE TABLE memories (
            id INTEGER PRIMARY KEY, path TEXT NOT NULL, relative_path TEXT NOT NULL,
            node_type TEXT, origin_session TEXT, modified_at TEXT,
            chars INTEGER NOT NULL, text TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE memories_fts USING fts5(
            text, content='memories', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );
        CREATE TABLE vscode_sol_requests (
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, request_id TEXT NOT NULL,
            model_id TEXT NOT NULL, requested_at TEXT, responded_at TEXT,
            source_file TEXT NOT NULL, source_line INTEGER,
            prompt_tokens INTEGER, completion_tokens INTEGER, elapsed_ms INTEGER,
            response_items INTEGER, assistant_chars INTEGER, tool_invocations INTEGER
        );
        CREATE TABLE vscode_sol_actions (
            id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, request_id TEXT NOT NULL,
            model_id TEXT NOT NULL, occurred_at TEXT, source_file TEXT NOT NULL,
            source_line INTEGER, event_index INTEGER, event_kind TEXT NOT NULL,
            tool_id TEXT, invocation TEXT, past_tense TEXT,
            is_complete INTEGER, payload TEXT NOT NULL, message TEXT
        );
        CREATE TABLE claude_actions (
            id INTEGER PRIMARY KEY, session_id TEXT, occurred_at TEXT,
            source_file TEXT NOT NULL, source_line INTEGER, tool_id TEXT,
            tool_name TEXT NOT NULL, paths TEXT NOT NULL,
            result_status TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE codex_actions (
            id INTEGER PRIMARY KEY, session_id TEXT, occurred_at TEXT,
            source_file TEXT NOT NULL, source_line INTEGER, tool_id TEXT,
            tool_name TEXT NOT NULL, paths TEXT NOT NULL,
            result_status TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE rule_events (
            id INTEGER PRIMARY KEY, sha TEXT NOT NULL, path TEXT NOT NULL,
            event_kind TEXT NOT NULL, text TEXT NOT NULL
        );
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY, turn_id INTEGER NOT NULL,
            signal_kind TEXT NOT NULL, score REAL NOT NULL,
            evidence TEXT NOT NULL, method TEXT NOT NULL
        );
        CREATE TABLE question_links (
            turn_id INTEGER PRIMARY KEY, response_turn_id INTEGER,
            response_present INTEGER NOT NULL, status TEXT NOT NULL
        );
        CREATE TABLE session_profiles (
            source TEXT NOT NULL, session_id TEXT NOT NULL,
            start TEXT, end TEXT,
            human_turns INTEGER, assistant_turns INTEGER,
            human_assistant_ratio REAL, frustration_hits INTEGER,
            delegation_hits INTEGER, pause_hits INTEGER,
            commits_in_window INTEGER, mode_candidate TEXT,
            PRIMARY KEY (source, session_id)
        );
        CREATE TABLE seed_candidates (
            id INTEGER PRIMARY KEY, seed_kind TEXT NOT NULL, turn_id INTEGER,
            score REAL NOT NULL, evidence TEXT NOT NULL
        );
        CREATE TABLE idea_followups (
            id INTEGER PRIMARY KEY, turn_id INTEGER NOT NULL, source TEXT,
            session_id TEXT, idea_timestamp TEXT, response_turn_id INTEGER,
            response_present INTEGER NOT NULL, session_commit_count INTEGER NOT NULL,
            matching_commit_count INTEGER NOT NULL, matching_commit_shas TEXT NOT NULL,
            status TEXT NOT NULL, evidence TEXT NOT NULL
        );
        CREATE TABLE proposal_followups (
            id INTEGER PRIMARY KEY, turn_id INTEGER NOT NULL, source TEXT,
            session_id TEXT, proposal_timestamp TEXT, trigger_turn_id INTEGER,
            prompt_driven INTEGER NOT NULL, approval_turn_id INTEGER,
            approval_present INTEGER NOT NULL, direct_action_count INTEGER NOT NULL,
            session_commit_count INTEGER NOT NULL, matching_commit_count INTEGER NOT NULL,
            matching_commit_shas TEXT NOT NULL, status TEXT NOT NULL,
            evidence TEXT NOT NULL
        );
    """)
    return conn


def write_sqlite(path: Path, turns: list[dict], commits: list[dict], files: list[dict],
                 cadence: list[dict], activity: list[dict], memories: list[dict],
                 rules: list[dict], signals: list[dict], questions: list[dict],
                 profiles: list[dict], candidates: list[dict], idea_followups: list[dict],
                 meta: dict, vscode_requests: list[dict] | None = None,
                 vscode_actions: list[dict] | None = None,
                 proposal_followups: list[dict] | None = None,
                 claude_actions: list[dict] | None = None,
                 codex_actions: list[dict] | None = None) -> None:
    conn = _create_sqlite(path)
    with conn:
        conn.executemany(
            "INSERT INTO turns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(t["n"], t.get("source", "claude_code"), t.get("sesion"),
              t.get("source_turn_id", str(t.get("n", ""))),
              t.get("record_fingerprint", _digest(str(t.get("n", "")))),
              t.get("cross_source_fingerprint"), int(bool(t.get("is_duplicate"))),
              t.get("duplicate_of"), t.get("duplicate_reason"),
              t.get("analysis_exclusion"), t["rol"], t.get("clase"),
              _iso(t.get("ts")), t.get("rama"), t.get("archivo"), t.get("linea"),
              t.get("via"), int(bool(t.get("sintetico"))), t["chars"], t["texto"])
             for t in turns],
        )
        conn.execute(
            "INSERT INTO turns_fts(rowid, text) "
            "SELECT id, text FROM turns "
            "WHERE is_duplicate = 0 AND analysis_exclusion IS NULL"
        )
        conn.executemany(
            "INSERT INTO git_commits VALUES (?,?,?,?,?,?,?,?)",
            [(c["sha"], _iso(c.get("authored_at")), _iso(c.get("committed_at")),
              c.get("author"), c.get("subject"), c["files"], c["insertions"],
              c["deletions"]) for c in commits],
        )
        conn.executemany(
            "INSERT INTO git_files VALUES (?,?,?,?,?,?)",
            [(f["sha"], f["path"], f.get("status", "?"), f.get("old_path"),
              f["additions"], f["deletions"]) for f in files],
        )
        conn.executemany(
            "INSERT INTO git_cadence VALUES (?,?,?,?,?,?,?)",
            [(row["granularity"], row["bucket"], row["commit_count"],
              row["author_count"], row["file_count"], row["insertions"],
              row["deletions"]) for row in cadence],
        )
        conn.executemany(
            "INSERT INTO mak_activity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(index, row["activity_id"], row["ts"], row["kind"], row["status"],
              row["trigger"], row["caller"], row["queue"], row["department"],
              row["job_id"], row["provider"], row["model"], row["resource"],
              row["payload"]) for index, row in enumerate(activity, 1)],
        )
        conn.executemany(
            "INSERT INTO memories VALUES (?,?,?,?,?,?,?,?)",
            [(index, row["path"], row["relative_path"], row["node_type"],
              row["origin_session"], row["modified_at"], row["chars"], row["text"])
             for index, row in enumerate(memories, 1)],
        )
        conn.execute(
            "INSERT INTO memories_fts(rowid, text) SELECT id, text FROM memories"
        )
        conn.executemany(
            "INSERT INTO vscode_sol_requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(index, row["session_id"], row["request_id"], row["model_id"],
              row["requested_at"], row["responded_at"], row["source_file"],
              row["source_line"], row["prompt_tokens"], row["completion_tokens"],
              row["elapsed_ms"], row["response_items"], row["assistant_chars"],
              row["tool_invocations"])
             for index, row in enumerate(vscode_requests or [], 1)],
        )
        conn.executemany(
            "INSERT INTO vscode_sol_actions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(index, row["session_id"], row["request_id"], row["model_id"],
              row["occurred_at"], row["source_file"], row["source_line"],
              row["event_index"], row["event_kind"], row["tool_id"],
              row["invocation"], row["past_tense"], row["is_complete"],
              row["payload"], row["message"])
             for index, row in enumerate(vscode_actions or [], 1)],
        )
        conn.executemany(
            "INSERT INTO claude_actions VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(index, row.get("session_id"), row.get("occurred_at"),
              row["source_file"], row["source_line"], row.get("tool_id"),
              row["tool_name"], _json(row.get("paths") or []),
              row.get("result_status", "unverified"), row.get("payload", "{}"))
             for index, row in enumerate(claude_actions or [], 1)],
        )
        conn.executemany(
            "INSERT INTO codex_actions VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(index, row.get("session_id"), row.get("occurred_at"),
              row["source_file"], row["source_line"], row.get("tool_id"),
              row["tool_name"], _json(row.get("paths") or []),
              row.get("result_status", "unverified"), row.get("payload", "{}"))
             for index, row in enumerate(codex_actions or [], 1)],
        )
        conn.executemany(
            "INSERT INTO rule_events VALUES (?,?,?,?,?)",
            [(index, r["sha"], r["path"], r["event_kind"], r["text"])
             for index, r in enumerate(rules, 1)],
        )
        conn.executemany(
            "INSERT INTO signals VALUES (?,?,?,?,?,?)",
            [(index, s["turn_id"], s["signal_kind"], s["score"], s["evidence"], s["method"])
             for index, s in enumerate(signals, 1)],
        )
        conn.executemany(
            "INSERT INTO question_links VALUES (?,?,?,?)",
            [(q["turn_id"], q["response_turn_id"], int(q["response_present"]), q["status"])
             for q in questions],
        )
        conn.executemany(
            "INSERT INTO session_profiles VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [(p["source"], p["session_id"], p["start"], p["end"], p["human_turns"],
              p["assistant_turns"], p["human_assistant_ratio"], p["frustration_hits"],
              p["delegation_hits"], p["pause_hits"], p["commits_in_window"],
              p["mode_candidate"]) for p in profiles],
        )
        conn.executemany(
            "INSERT INTO seed_candidates VALUES (?,?,?,?,?)",
            [(index, c["seed_kind"], c.get("turn_id"), c["score"], c["evidence"])
             for index, c in enumerate(candidates, 1)],
        )
        conn.executemany(
            "INSERT INTO idea_followups VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            [(index, row["turn_id"], row["source"], row["session_id"],
              row["idea_timestamp"], row["response_turn_id"],
              int(row["response_present"]), row["session_commit_count"],
              row["matching_commit_count"], _json(row["matching_commit_shas"]),
              row["status"], row["evidence"])
             for index, row in enumerate(idea_followups, 1)],
        )
        conn.executemany(
            "INSERT INTO proposal_followups VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(index, row["turn_id"], row["source"], row["session_id"],
              row["proposal_timestamp"], row["trigger_turn_id"],
              row["prompt_driven"], row["approval_turn_id"],
              row["approval_present"], row["direct_action_count"],
              row["session_commit_count"], row["matching_commit_count"],
              _json(row["matching_commit_shas"]), row["status"], row["evidence"])
             for index, row in enumerate(proposal_followups or [], 1)],
        )
        conn.executemany("INSERT INTO meta VALUES (?,?)", [(k, str(v)) for k, v in meta.items()])
    conn.close()


def _duckdb_type(sqlite_type: str) -> str:
    """Map SQLite declarations to usable DuckDB relational types."""
    declared = (sqlite_type or "").upper()
    if "INT" in declared:
        return "BIGINT"
    if any(token in declared for token in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE"
    return "VARCHAR"


def write_duckdb(path: Path, sqlite_path: Path) -> None:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("DuckDB is unavailable; install the project dependency first") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    source = sqlite3.connect(sqlite_path)
    db = duckdb.connect(str(path))
    try:
        tables = [
            "meta", "turns", "git_commits", "git_files", "git_cadence",
            "mak_activity", "memories", "vscode_sol_requests", "vscode_sol_actions",
            "claude_actions",
            "codex_actions",
            "rule_events",
            "signals", "question_links", "session_profiles", "seed_candidates",
            "idea_followups", "proposal_followups",
        ]
        for table in tables:
            rows = source.execute("SELECT * FROM %s" % table).fetchall()
            schema_rows = source.execute("PRAGMA table_info(%s)" % table).fetchall()
            columns = [row[1] for row in schema_rows]
            types = ", ".join(
                '"%s" %s' % (row[1], _duckdb_type(row[2]))
                for row in schema_rows
            )
            db.execute('CREATE TABLE "%s" (%s)' % (table, types))
            if rows:
                placeholders = ",".join("?" for _ in columns)
                db.executemany('INSERT INTO "%s" VALUES (%s)' % (table, placeholders), rows)
    finally:
        db.close()
        source.close()


def build(args: argparse.Namespace) -> dict:
    repo = Path(args.repo).resolve()
    output = safe_artifact_path(repo, args.output, "sqlite output")
    duckdb_path = (
        safe_artifact_path(repo, args.duckdb, "duckdb output")
        if args.duckdb else None
    )
    summary_path = (
        safe_artifact_path(repo, args.summary, "summary output")
        if args.summary else None
    )
    claude_root = Path(args.claude_root).expanduser().resolve()
    claude_web = Path(args.claude_web).expanduser().resolve() if args.claude_web else None
    codex_root = Path(args.codex_root).expanduser().resolve() if args.codex_root else None
    codex_exclude = {
        Path(item).expanduser().resolve() for item in (args.codex_exclude_file or [])
    }
    vscode_roots = [
        Path(item).expanduser().resolve() for item in (args.vscode_root or [])
    ]
    turns, warnings, source_counts = load_all_turns(
        claude_root, claude_web, codex_root, codex_exclude, vscode_roots
    )
    analysis_turns = [
        turn for turn in turns
        if not turn["is_duplicate"] and not turn["analysis_exclusion"]
    ]
    commits, files = load_git(repo)
    cadence = build_git_cadence(commits, files)
    activity, activity_warnings = load_mak_activity(
        Path(args.mak_activity).expanduser().resolve() if args.mak_activity else None
    )
    memories, memory_warnings = load_memories(
        Path(args.memory_root).expanduser().resolve() if args.memory_root else None
    )
    claude_actions, claude_action_warnings = load_claude_actions(claude_root)
    codex_actions, codex_action_warnings = load_codex_actions(
        codex_root, codex_exclude
    ) if codex_root else ([], [])
    vscode_requests, vscode_actions, vscode_warnings = load_vscode_sol_metrics(vscode_roots)
    rules = load_rule_events(repo, files)
    signals, candidates, questions = classify_turns(analysis_turns)
    profiles = build_session_profiles(analysis_turns, commits, signals)
    idea_followups = build_idea_followups(analysis_turns, candidates, commits)
    proposal_followups = build_proposal_followups(
        analysis_turns, commits, vscode_actions, repo, claude_actions,
        codex_actions
    )
    meta = {
        "schema": "inferential-archaeology-v7",
        "repo": str(repo), "claude_root": str(claude_root),
        "vscode_sol_roots": _json([str(path) for path in vscode_roots]),
        "turns": len(turns),
        "unique_turns": sum(not turn["is_duplicate"] for turn in turns),
        "analysis_turns": len(analysis_turns),
        "duplicate_turns": sum(turn["is_duplicate"] for turn in turns),
        "analysis_excluded_turns": sum(
            bool(turn["analysis_exclusion"]) for turn in turns
        ),
        "commits": len(commits), "git_files": len(files),
        "deleted_file_events": sum(row.get("status") == "D" for row in files),
        "renamed_file_events": sum(row.get("status") == "R" for row in files),
        "git_file_statuses": _json(dict(collections.Counter(
            row.get("status", "?") for row in files
        ))),
        "git_cadence_buckets": len(cadence),
        "mak_activity_rows": len(activity),
        "memory_files": len(memories),
        "vscode_sol_requests": len(vscode_requests),
        "vscode_sol_actions": len(vscode_actions),
        "claude_actions": len(claude_actions),
        "codex_actions": len(codex_actions),
        "rule_events": len(rules), "signals": len(signals),
        "questions": len(questions), "sessions": len(profiles),
        "seed_candidates": len(candidates), "idea_followups": len(idea_followups),
        "proposal_followups": len(proposal_followups),
        "sources": _json(source_counts),
        "codex_excluded_files": _json(sorted(str(path) for path in codex_exclude)),
        "warnings": _json(
            warnings + activity_warnings + memory_warnings + vscode_warnings +
            claude_action_warnings + codex_action_warnings
        ),
    }
    write_sqlite(output, turns, commits, files, cadence, activity, memories, rules, signals, questions,
                 profiles, candidates, idea_followups, meta,
                 vscode_requests, vscode_actions, proposal_followups,
                 claude_actions, codex_actions)
    if duckdb_path:
        write_duckdb(duckdb_path, output)
    summary = {**meta, "sqlite": str(output), "duckdb": str(duckdb_path) if duckdb_path else None}
    if summary_path:
        summary_path.write_text(_json(summary) + "\n", encoding="utf-8")
    return summary


def _turn_evidence(conn: sqlite3.Connection, turn_id: int | None) -> dict | None:
    if turn_id is None:
        return None
    row = conn.execute(
        "SELECT id,source,session_id,source_turn_id,occurred_at,role,branch,"
        "source_file,source_line,chars,text,analysis_exclusion FROM turns WHERE id=?",
        (turn_id,),
    ).fetchone()
    if row is None:
        return None
    keys = ("turn_id", "source", "session_id", "source_turn_id", "occurred_at",
            "role", "branch", "source_file", "source_line", "chars", "text",
            "analysis_exclusion")
    return dict(zip(keys, row))


def _row_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


def _commit_evidence(conn: sqlite3.Connection, sha: str, path_limit: int = 20) -> dict | None:
    commit = conn.execute(
        "SELECT sha,authored_at,committed_at,author,subject,files,insertions,deletions "
        "FROM git_commits WHERE sha=?", (sha,)
    ).fetchone()
    if commit is None:
        return None
    files = conn.execute(
        "SELECT status,path,old_path,additions,deletions FROM git_files "
        "WHERE sha=? ORDER BY path LIMIT ?", (sha, path_limit)
    ).fetchall()
    return {
        "sha": commit[0], "authored_at": commit[1], "committed_at": commit[2],
        "author": commit[3], "subject": commit[4], "file_count": commit[5],
        "insertions": commit[6], "deletions": commit[7],
        "files": [
            {"status": row[0], "path": row[1], "old_path": row[2],
             "additions": row[3], "deletions": row[4]}
            for row in files
        ],
    }


def _cross_source_terms(text: str) -> list[str]:
    """Return deterministic anchor terms without pretending they are concepts."""
    folded = _strip_accents(text)
    raw = re.findall(r"[a-z0-9][a-z0-9_.-]{2,}", folded)
    terms: list[str] = []
    seen: set[str] = set()
    for raw_term in raw:
        term = raw_term.strip("._-")
        if not term or term in seen:
            continue
        if len(term) < 4 and term not in CROSS_SOURCE_KEEP_SHORT:
            continue
        if term in CROSS_SOURCE_STOP_WORDS or term in {"http", "https", "www", "com"}:
            continue
        if term.startswith(("file", "request", "workspace")):
            continue
        seen.add(term)
        terms.append(term)
    return terms


def _fts_turn_hits(conn: sqlite3.Connection, term: str, limit: int = 6) -> list[dict]:
    """Find exact FTS evidence while preserving the source boundary."""
    query = '"%s"' % term.replace('"', "")
    try:
        rows = conn.execute(
            "SELECT t.id,t.source,t.session_id,t.occurred_at,t.role,t.source_file,"
            "t.source_line,snippet(turns_fts,0,'[',']','...',28) "
            "FROM turns_fts JOIN turns t ON t.id=turns_fts.rowid "
            "WHERE turns_fts MATCH ? AND t.source <> 'vscode_sol' "
            "AND t.is_duplicate=0 AND t.analysis_exclusion IS NULL "
            "ORDER BY t.occurred_at,t.id LIMIT ?", (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    keys = ("turn_id", "source", "session_id", "occurred_at", "role",
            "source_file", "source_line", "snippet")
    return [dict(zip(keys, row)) for row in rows]


def _fts_turn_count(conn: sqlite3.Connection, term: str) -> tuple[int, int]:
    query = '"%s"' % term.replace('"', "")
    try:
        row = conn.execute(
            "SELECT COUNT(*),COUNT(DISTINCT t.source) FROM turns_fts "
            "JOIN turns t ON t.id=turns_fts.rowid WHERE turns_fts MATCH ? "
            "AND t.source <> 'vscode_sol' AND t.is_duplicate=0 "
            "AND t.analysis_exclusion IS NULL", (query,),
        ).fetchone()
    except sqlite3.OperationalError:
        return 0, 0
    return int(row[0] or 0), int(row[1] or 0)


def _fts_memory_hits(conn: sqlite3.Connection, term: str, limit: int = 4) -> list[dict]:
    query = '"%s"' % term.replace('"', "")
    try:
        rows = conn.execute(
            "SELECT m.id,m.path,m.relative_path,m.node_type,m.origin_session,"
            "m.modified_at,snippet(memories_fts,0,'[',']','...',28) "
            "FROM memories_fts JOIN memories m ON m.id=memories_fts.rowid "
            "WHERE memories_fts MATCH ? ORDER BY m.modified_at DESC,m.id LIMIT ?",
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    keys = ("memory_id", "path", "relative_path", "node_type",
            "origin_session", "modified_at", "snippet")
    return [dict(zip(keys, row)) for row in rows]


def _action_paths(value: str) -> list[str]:
    text = unquote(value or "").replace("%5C", "\\")
    paths: list[str] = []
    seen: set[str] = set()
    for match in ACTION_PATH_PATTERN.findall(text):
        path = match.rstrip(".,;:)]}'\"")
        normalized = path.replace("\\", "/")
        if normalized.lower().startswith("file:///"):
            normalized = normalized[8:]
        if normalized not in seen:
            seen.add(normalized)
            paths.append(normalized)
    return paths


def _relative_action_path(path: str, repo: Path | None) -> str | None:
    normalized = path.replace("\\", "/").lstrip("/")
    lowered = normalized.casefold()
    # SOL often worked in sibling checkouts such as ``flujo-mejoras`` or
    # ``flujo-sin-gptmini``. Preserve that provenance elsewhere, but normalize
    # the repository-relative suffix so current Git can be checked safely.
    checkout_match = re.search(r"/flujo(?:-[^/]+)?/(.+)$", normalized, re.IGNORECASE)
    if checkout_match:
        normalized = normalized[checkout_match.start(1):]
    else:
        marker = "/flujo/"
        if marker in lowered:
            normalized = normalized[lowered.index(marker) + len(marker):]
    if repo is not None:
        try:
            candidate = Path(path)
            if candidate.is_absolute() and candidate.is_file():
                normalized = candidate.resolve().relative_to(repo.resolve()).as_posix()
        except (OSError, ValueError):
            pass
    return normalized or None


def _temporal_git_hits(conn: sqlite3.Connection, terms: list[str], stamp: str | None,
                       limit: int = 8) -> list[dict]:
    """Link nearby commits by exact subject/path overlap, never as proof alone."""
    if not terms:
        return []
    clauses = []
    params: list[Any] = []
    for term in terms:
        clauses.append("(lower(c.subject) LIKE ? OR lower(f.path) LIKE ?)")
        params.extend(["%%%s%%" % term, "%%%s%%" % term])
    temporal = ""
    if stamp:
        temporal = " AND julianday(c.committed_at) BETWEEN julianday(?) - 2 AND julianday(?) + 14"
        params.extend([stamp, stamp])
    rows = conn.execute(
        "SELECT DISTINCT c.sha,c.authored_at,c.committed_at,c.author,c.subject,"
        "c.files,c.insertions,c.deletions,f.status,f.path,f.old_path "
        "FROM git_commits c JOIN git_files f ON f.sha=c.sha WHERE (" +
        " OR ".join(clauses) + ")" + temporal +
        " ORDER BY c.committed_at LIMIT ?", (*params, limit),
    ).fetchall()
    keys = ("sha", "authored_at", "committed_at", "author", "subject",
            "file_count", "insertions", "deletions", "status", "path", "old_path")
    grouped: dict[str, dict] = {}
    for row in rows:
        item = dict(zip(keys, row))
        current = grouped.get(item["sha"])
        if current is None:
            current = {key: item[key] for key in keys[:8]}
            current["paths"] = []
            grouped[item["sha"]] = current
        current["paths"].append({
            "status": item["status"], "path": item["path"],
            "old_path": item["old_path"],
        })
    return list(grouped.values())[:limit]


def _mak_activity_hits(conn: sqlite3.Connection, terms: list[str], limit: int = 8) -> list[dict]:
    if not terms:
        return []
    clauses = []
    params: list[Any] = []
    for term in terms:
        clauses.append(
            "(lower(department) LIKE ? OR lower(provider) LIKE ? OR "
            "lower(model) LIKE ? OR lower(trigger) LIKE ? OR "
            "lower(resource) LIKE ? OR lower(payload) LIKE ?)"
        )
        params.extend(["%%%s%%" % term] * 6)
    rows = conn.execute(
        "SELECT activity_id,ts,kind,status,trigger,department,provider,model,resource "
        "FROM mak_activity WHERE " + " OR ".join(clauses) +
        " ORDER BY ts DESC LIMIT ?", (*params, limit),
    ).fetchall()
    keys = ("activity_id", "ts", "kind", "status", "trigger", "department",
            "provider", "model", "resource")
    return [dict(zip(keys, row)) for row in rows]


def _bifurcation_context(conn: sqlite3.Connection, text: str,
                         limit: int = 8) -> dict:
    """Retrieve bounded memory and MAK echoes for one review group.

    Memories are already-authored semantic reports, not another interaction
    classifier. Their snippets are preserved as context; FTS overlap is never
    promoted to authorship, implementation, or value.
    """
    terms = _cross_source_terms(text)[:8]
    memory_hits: list[dict] = []
    for term in terms:
        memory_hits.extend(_fts_memory_hits(conn, term, 2))
    memory_hits = list({item["memory_id"]: item for item in memory_hits}.values())
    return {
        "anchor_terms": terms,
        "memory_evidence": memory_hits[:limit],
        "mak_activity": _mak_activity_hits(conn, terms, limit),
        "limits": [
            "memory snippets are authored context, not a new conversation turn",
            "FTS overlap does not establish semantic identity",
            "MAK activity is an execution inventory snapshot, not live service proof",
        ],
    }


def _sol_action_evidence(conn: sqlite3.Connection, request_id: str,
                         repo: Path | None) -> tuple[list[dict], list[dict]]:
    rows = conn.execute(
        "SELECT id,tool_id,event_kind,occurred_at,source_file,source_line,"
        "invocation,past_tense,message FROM vscode_sol_actions "
        "WHERE request_id=? ORDER BY id", (request_id,),
    ).fetchall()
    all_actions: list[dict] = []
    mutation_actions: list[dict] = []
    for row in rows:
        text = " ".join(str(value or "") for value in row[6:9])
        paths = [_relative_action_path(path, repo) for path in _action_paths(text)]
        item = {
            "action_id": row[0], "tool_id": row[1], "event_kind": row[2],
            "occurred_at": row[3], "source_file": row[4], "source_line": row[5],
            "paths": [path for path in paths if path],
            "message": text[:500],
        }
        all_actions.append(item)
        if row[1] in SOL_MUTATING_TOOLS and item["paths"]:
            mutation_actions.append(item)
    return all_actions, mutation_actions


def build_cross_source_packet(conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    """Rank a small SOL seed packet across text, memory, Git, activity and actions.

    This is a retrieval circuit, not a semantic verdict. A cross-source echo is
    useful for choosing what to read; only a mutation action with a recoverable
    path is tagged as implementation evidence, and even that remains a human
    review candidate.
    """
    meta = dict(conn.execute("SELECT key,value FROM meta").fetchall())
    repo = Path(meta["repo"]) if meta.get("repo") else None
    sol_users = conn.execute(
        "SELECT id,session_id,source_turn_id,occurred_at,source_file,source_line,text "
        "FROM turns WHERE source='vscode_sol' AND role='user' AND is_duplicate=0 "
        "AND analysis_exclusion IS NULL ORDER BY occurred_at,id"
    ).fetchall()
    ranked: list[tuple[float, dict]] = []
    for row in sol_users:
        turn_id, session_id, source_turn_id, stamp, source_file, source_line, text = row
        terms = _cross_source_terms(text)
        term_stats: list[tuple[float, int, int, str, list[dict]]] = []
        turn_hits: list[dict] = []
        for term in terms:
            hits = _fts_turn_hits(conn, term, 6)
            total_count, source_count = _fts_turn_count(conn, term)
            if source_count:
                # Exact rare terms are better anchors than ubiquitous project
                # nouns. Diversity remains in the score, so a one-source typo
                # cannot dominate a term repeated across corpora.
                quality = source_count + (30.0 / (total_count + 1.0))
                term_stats.append((quality, source_count, total_count, term, hits))
                turn_hits.extend(hits)
        # Rare terms are more useful than generic words. Source diversity still
        # matters, so the tuple prefers terms seen in more source types first,
        # then the lowest exact hit count.
        term_stats.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
        anchors = [term for _quality, _sources, _total, term, _hits in term_stats[:6]]
        if not anchors:
            continue
        if not any(anchor not in CROSS_SOURCE_GENERIC_ANCHORS for anchor in anchors):
            continue
        request_id = source_turn_id.split(":", 1)[0]
        actions, mutation_actions = _sol_action_evidence(conn, request_id, repo)
        anchor_totals = {
            term: total for _quality, _sources, total, term, _hits in term_stats
        }
        candidate_kinds = {
            row[0] for row in conn.execute(
                "SELECT seed_kind FROM seed_candidates WHERE turn_id=?", (turn_id,)
            ).fetchall()
        }
        memory_hits: list[dict] = []
        for term in anchors:
            memory_hits.extend(_fts_memory_hits(conn, term, 3))
        memory_hits = list({item["memory_id"]: item for item in memory_hits}.values())
        git_hits = _temporal_git_hits(conn, anchors, stamp, 10)
        activity_hits = _mak_activity_hits(conn, anchors, 8)
        distinct_sources = len({hit["source"] for hit in turn_hits})
        # Prefer source diversity, then recoverable implementation traces, then
        # temporal Git echoes. The ranking stays mechanical and inspectable.
        score = (
            distinct_sources * 2.0 + min(len(memory_hits), 4) * 0.75 +
            min(len(git_hits), 6) * 1.0 + min(len(mutation_actions), 4) * 3.0 +
            (1.0 if actions else 0.0) +
            min(4.0, sum(1.5 for anchor in anchors
                         if anchor_totals.get(anchor, 999999) <= 25)) +
            (1.5 if candidate_kinds & {"question_candidate", "idea_candidate"} else 0.0)
        )
        if distinct_sources < 1 and not mutation_actions:
            continue
        unique_turn_hits = {}
        for hit in turn_hits:
            unique_turn_hits[hit["turn_id"]] = hit
        direct = bool(mutation_actions)
        item = {
            "seed_id": "sol-%s" % turn_id,
            "selection_score": round(score, 3),
            "selection_method": "ranked_anchor_overlap_with_source_diversity",
            "implementation_status": (
                "direct_action_candidate" if direct else
                "temporal_echo_candidate" if git_hits else "conceptual_seed"
            ),
            "implementation_evidence": mutation_actions,
            "turn": {
                "turn_id": turn_id, "source": "vscode_sol", "session_id": session_id,
                "source_turn_id": source_turn_id, "occurred_at": stamp,
                "source_file": source_file, "source_line": source_line,
                "text": text,
            },
            "anchors": anchors,
            "cross_source_turns": list(unique_turn_hits.values())[:12],
            "memory_hits": memory_hits[:8],
            "git_evidence": git_hits,
            "mak_activity_hits": activity_hits,
            "sol_actions": actions[:20],
            "evidence_limits": [
                "anchor overlap does not establish semantic identity",
                "nearby commits do not prove the user idea caused the change",
                "a mutation action does not prove the final runtime was accepted",
                "activity inventory does not prove provider output quality or billing",
            ],
        }
        ranked.append((score, item))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["turn"]["occurred_at"] or ""))
    selected: list[dict] = []
    seen_text: set[str] = set()
    for _score, item in ranked:
        fingerprint = _dedupe_text(item["turn"]["text"])
        if fingerprint in seen_text:
            continue
        seen_text.add(fingerprint)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _proposal_repetition_index(conn: sqlite3.Connection) -> tuple[dict[int, dict], dict]:
    """Index exact normalized proposal repetitions without semantic merging."""
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    rows = conn.execute(
        "SELECT id,source,session_id,status,prompt_driven,evidence "
        "FROM proposal_followups ORDER BY id"
    ).fetchall()
    by_id: dict[int, dict] = {}
    for row in rows:
        try:
            evidence = json.loads(row[5])
        except (TypeError, json.JSONDecodeError):
            evidence = {}
        text = _dedupe_text(str(evidence.get("proposal_text") or ""))
        fingerprint = _digest(text) if text else ""
        record = {
            "id": row[0], "source": row[1], "session_id": row[2],
            "status": row[3], "prompt_driven": bool(row[4]),
            "fingerprint": fingerprint,
        }
        by_id[row[0]] = record
        if fingerprint:
            groups[fingerprint].append(record)
    repeated = [items for items in groups.values() if len(items) > 1]
    summary = {
        "proposal_rows": len(rows),
        "unique_exact_texts": len(groups),
        "repeated_exact_groups": len(repeated),
        "repeated_rows_beyond_first": sum(len(items) - 1 for items in repeated),
        "method": "NFKC casefold whitespace-normalized exact proposal text",
        "semantic_merges": False,
        "top_repetitions": [
            {
                "fingerprint": items[0]["fingerprint"],
                "count": len(items),
                "proposal_ids": [item["id"] for item in items],
                "sources": sorted({item["source"] for item in items}),
            }
            for items in sorted(repeated, key=lambda group: (-len(group), group[0]["id"]))[:12]
        ],
    }
    counts = collections.Counter(item["fingerprint"] for item in by_id.values()
                                 if item["fingerprint"])
    for item in by_id.values():
        item["repeat_count"] = counts.get(item["fingerprint"], 0)
    return by_id, summary


def _proposal_scale_summary(conn: sqlite3.Connection) -> dict:
    """Measure proposal size separately from implementation state."""
    grouped: dict[tuple[str, int, int], list[int]] = collections.defaultdict(list)
    for row in conn.execute(
        "SELECT p.status,p.prompt_driven,p.approval_present,LENGTH(t.text) "
        "FROM proposal_followups p JOIN turns t ON t.id=p.turn_id"
    ):
        grouped[(row[0], int(row[1]), int(row[2]))].append(int(row[3] or 0))
    rows = []
    for (status, prompt_driven, approval_present), lengths in sorted(grouped.items()):
        rows.append({
            "status": status, "prompt_driven": bool(prompt_driven),
            "approval_present": bool(approval_present), "count": len(lengths),
            "mean_chars": round(statistics.mean(lengths), 1),
            "median_chars": statistics.median(lengths), "max_chars": max(lengths),
        })
    return {
        "method": "exact assistant turn length grouped by mechanical proposal status",
        "groups": rows,
        "warning": "length is not quality and does not prove the proposal was excessive",
    }


def _load_bifurcation_items(conn: sqlite3.Connection) -> list[dict]:
    """Load proposal and user-idea seeds into one author-preserving stream."""
    items: list[dict] = []
    for row in conn.execute(
        "SELECT id,turn_id,source,session_id,trigger_turn_id,approval_turn_id,"
        "approval_present,direct_action_count,matching_commit_count,"
        "matching_commit_shas,status,evidence FROM proposal_followups ORDER BY id"
    ):
        try:
            evidence = json.loads(row[11])
        except (TypeError, json.JSONDecodeError):
            evidence = {}
        turn = _turn_evidence(conn, row[1])
        text = (turn or {}).get("text") or evidence.get("proposal_text") or ""
        trigger = _turn_evidence(conn, row[4])
        approval = _turn_evidence(conn, row[5])
        try:
            matching_shas = json.loads(row[9] or "[]")
        except (TypeError, json.JSONDecodeError):
            matching_shas = []
        items.append({
            "item_id": "proposal-%s" % row[0], "record_id": row[0],
            "turn_id": row[1], "kind": "agent_proposal", "source": row[2],
            "session_id": row[3], "trigger_turn_id": row[4],
            "approval_turn_id": row[5], "approval_present": bool(row[6]),
            "direct_action_count": int(row[7] or 0),
            "matching_commit_count": int(row[8] or 0),
            "matching_commit_shas": matching_shas,
            "status": row[10], "text": text,
            "occurred_at": (turn or {}).get("occurred_at"),
            "trigger": trigger,
            "approval": approval,
            "evidence": evidence,
        })
    for row in conn.execute(
        "SELECT id,turn_id,source,session_id,response_turn_id,response_present,"
        "matching_commit_count,matching_commit_shas,status,evidence "
        "FROM idea_followups ORDER BY id"
    ):
        try:
            evidence = json.loads(row[9])
        except (TypeError, json.JSONDecodeError):
            evidence = {}
        turn = _turn_evidence(conn, row[1])
        text = (turn or {}).get("text") or evidence.get("idea_text") or ""
        response = _turn_evidence(conn, row[4])
        try:
            matching_shas = json.loads(row[7] or "[]")
        except (TypeError, json.JSONDecodeError):
            matching_shas = []
        items.append({
            "item_id": "idea-%s" % row[0], "record_id": row[0],
            "turn_id": row[1], "kind": "user_idea", "source": row[2],
            "session_id": row[3], "trigger_turn_id": None,
            "approval_turn_id": row[4], "approval_present": bool(row[5]),
            "direct_action_count": 0,
            "matching_commit_count": int(row[6] or 0),
            "matching_commit_shas": matching_shas,
            "status": row[8], "text": text,
            "occurred_at": (turn or {}).get("occurred_at"),
            "trigger": None,
            "approval": response,
            "evidence": evidence,
        })
    return items


def _path_history(conn: sqlite3.Connection, repo: Path | None,
                  paths: list[str]) -> dict:
    """Check action paths against current checkout and indexed Git history."""
    current: list[str] = []
    history: list[dict] = []
    seen_history: set[tuple[str, str, str | None]] = set()
    for raw_path in paths:
        path = _relative_action_path(raw_path, repo)
        if not path:
            continue
        candidate = Path(repo, path) if repo else Path(path)
        if candidate.exists():
            current.append(path)
        rows = conn.execute(
            "SELECT c.sha,c.committed_at,c.subject,f.status,f.path,f.old_path "
            "FROM git_commits c JOIN git_files f ON f.sha=c.sha "
            "WHERE lower(f.path)=? OR lower(coalesce(f.old_path,''))=? "
            "ORDER BY c.committed_at DESC LIMIT 12",
            (path.casefold(), path.casefold()),
        ).fetchall()
        for row in rows:
            key = (row[0], row[4], row[5])
            if key in seen_history:
                continue
            seen_history.add(key)
            history.append({
                "sha": row[0], "committed_at": row[1], "subject": row[2],
                "status": row[3], "path": row[4], "old_path": row[5],
                "requested_path": path,
            })
    return {
        "requested_paths": sorted(set(paths)),
        "current_paths": sorted(set(current)),
        "git_history": history[:20],
    }


def _proposal_outcome(item: dict, path_state: dict) -> tuple[str, str]:
    """Assign one of five review outcomes with a reason, not a verdict."""
    if item["kind"] == "user_idea":
        return "user_idea_still_open", "user idea has no direct implementation evidence in this packet"
    direct = item["direct_action_count"] > 0
    has_history = bool(path_state["git_history"])
    has_current = bool(path_state["current_paths"])
    if direct and has_current and has_history:
        return "implemented_and_current", "direct action path exists in checkout and has indexed Git history"
    if direct and has_history and not has_current:
        return "implemented_but_abandoned", "direct action path has Git history but is absent from current checkout"
    if item["approval_present"]:
        return "approved_without_verified_execution", "approval exists without a current direct implementation link"
    return "agent_proposal_never_adopted", "no approval or direct implementation evidence in bounded packet"


def build_bifurcation_map(conn: sqlite3.Connection, repo: Path | None) -> dict:
    """Build exact-text review groups and conservative five-way outcomes."""
    items = _load_bifurcation_items(conn)
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    outcome_rows: list[dict] = []
    for item in items:
        fingerprint = _digest(_dedupe_text(item["text"]))
        item["fingerprint"] = fingerprint
        actions = item["evidence"].get("direct_actions") or []
        paths = []
        for action in actions:
            paths.extend(action.get("paths") or [])
        path_state = _path_history(conn, repo, paths)
        outcome, reason = _proposal_outcome(item, path_state)
        item["outcome"] = outcome
        item["outcome_reason"] = reason
        item["path_state"] = path_state
        item["matching_commit_evidence"] = [
            evidence for sha in item["matching_commit_shas"][:12]
            if (evidence := _commit_evidence(conn, sha)) is not None
        ]
        groups[fingerprint].append(item)
        outcome_rows.append({
            "item_id": item["item_id"], "kind": item["kind"],
            "turn_id": item["turn_id"], "outcome": outcome,
            "reason": reason, "source": item["source"],
            "occurred_at": item["occurred_at"],
            "approval_present": bool(item["approval_present"]),
            "direct_action_count": item["direct_action_count"],
            "current_paths": path_state["current_paths"],
            "git_history": path_state["git_history"][:6],
            "trigger": item["trigger"],
            "response": item["approval"],
            "direct_actions": item["evidence"].get("direct_actions") or [],
            "matching_commit_evidence": item["matching_commit_evidence"],
        })
    group_rows: list[dict] = []
    for fingerprint, members in groups.items():
        counts = collections.Counter(item["outcome"] for item in members)
        ranked = sorted(
            counts.items(),
            key=lambda pair: (OUTCOME_ORDER.index(pair[0]), -pair[1]),
        )
        representative = max(members, key=lambda item: len(item["text"]))
        context = _bifurcation_context(conn, representative["text"])
        member_evidence = []
        for member in members[:24]:
            member_evidence.append({
                "item_id": member["item_id"], "kind": member["kind"],
                "turn_id": member["turn_id"], "source": member["source"],
                "approval_present": bool(member["approval_present"]),
                "trigger": member["trigger"], "response": member["approval"],
                "direct_actions": member["evidence"].get("direct_actions") or [],
                "path_state": member["path_state"],
                "matching_commit_evidence": member["matching_commit_evidence"],
                "outcome": member["outcome"],
            })
        group_rows.append({
            "group_id": "bif-%s" % fingerprint[:16],
            "fingerprint": fingerprint,
            "grouping_method": "exact_NFKC_casefold_whitespace_text",
            "member_count": len(members),
            "proposal_count": sum(item["kind"] == "agent_proposal" for item in members),
            "user_idea_count": sum(item["kind"] == "user_idea" for item in members),
            "outcome_counts": dict(counts),
            "dominant_outcome": ranked[0][0],
            "review_required": any(
                item["outcome"] in {
                    "approved_without_verified_execution", "user_idea_still_open",
                    "agent_proposal_never_adopted",
                } for item in members
            ),
            "sources": sorted({item["source"] for item in members}),
            "member_ids": [item["item_id"] for item in members],
            "representative_turn_id": representative["turn_id"],
            "representative_text": representative["text"][:900],
            "representative_trigger": representative["trigger"],
            "representative_response": representative["approval"],
            "memory_evidence": context["memory_evidence"],
            "mak_activity": context["mak_activity"],
            "anchor_terms": context["anchor_terms"],
            "member_evidence": member_evidence,
            "direct_paths": sorted({
                path for item in members
                for path in item["path_state"]["requested_paths"]
            }),
            "current_paths": sorted({
                path for item in members
                for path in item["path_state"]["current_paths"]
            }),
            "commit_shas": sorted({
                sha for item in members for sha in item["matching_commit_shas"]
            }),
            "limits": [
                "exact text grouping does not merge paraphrases",
                "lexical commit overlap does not prove implementation",
                "direct action plus current path is a candidate, not human acceptance",
                "memory and MAK matches are contextual echoes, not causal proof",
            ],
        })
    group_rows.sort(key=lambda row: (-row["member_count"], row["group_id"]))
    return {
        "schema": "inferential-archaeology-bifurcation-v1",
        "method": "all proposal and user-idea followups grouped by exact normalized text",
        "item_count": len(items), "group_count": len(group_rows),
        "outcome_counts": dict(collections.Counter(row["outcome"] for row in outcome_rows)),
        "groups": group_rows,
        "items": outcome_rows,
    }


def build_hotspot_map(conn: sqlite3.Connection, outcome_map: dict,
                      limit: int = 24) -> dict:
    """Connect frustration/scope signals to the proposal immediately after them."""
    outcome_by_item = {row["item_id"]: row for row in outcome_map["items"]}
    grouped: dict[int, dict] = {}
    signal_rows = conn.execute(
        "SELECT turn_id,signal_kind,score,evidence FROM signals "
        "WHERE signal_kind IN ('frustration_hotspot','pause_or_scope_signal') "
        "ORDER BY score DESC,turn_id"
    ).fetchall()
    for turn_id, kind, score, evidence in signal_rows:
        turn = _turn_evidence(conn, turn_id)
        if not turn or turn.get("role") != "user":
            continue
        row = grouped.setdefault(turn_id, {
            "turn_id": turn_id, "occurred_at": turn.get("occurred_at"),
            "source": turn.get("source"), "session_id": turn.get("session_id"),
            "text": turn.get("text", "")[:700], "signal_kinds": [],
            "signal_scores": [], "proposals": [],
        })
        row["signal_kinds"].append(kind)
        row["signal_scores"].append(score)
    proposals_by_trigger: dict[int, list[dict]] = collections.defaultdict(list)
    for item in outcome_map["items"]:
        if item["kind"] != "agent_proposal":
            continue
        proposal_id = int(item["item_id"].split("-", 1)[1])
        trigger = conn.execute(
            "SELECT trigger_turn_id FROM proposal_followups WHERE id=?",
            (proposal_id,),
        ).fetchone()
        if trigger and trigger[0] is not None:
            proposals_by_trigger[trigger[0]].append(item)
    for turn_id, row in grouped.items():
        for proposal in proposals_by_trigger.get(turn_id, []):
            row["proposals"].append({
                "item_id": proposal["item_id"], "outcome": proposal["outcome"],
                "direct_action_count": proposal["direct_action_count"],
                "current_paths": proposal["current_paths"],
            })
        has_frustration = "frustration_hotspot" in row["signal_kinds"]
        has_pause = "pause_or_scope_signal" in row["signal_kinds"]
        if has_pause and any(item["direct_action_count"] for item in row["proposals"]):
            pattern = "scope_violation_candidate"
        elif has_frustration and row["proposals"] and not any(
            item["direct_action_count"] for item in row["proposals"]
        ):
            pattern = "proposal_without_execution_candidate"
        elif row["proposals"]:
            pattern = "correction_followed_by_proposal_candidate"
        else:
            pattern = "unpaired_hotspot"
        row["failure_pattern"] = pattern
        row["max_signal_score"] = max(row["signal_scores"])
    hotspots = sorted(
        grouped.values(), key=lambda row: (-row["max_signal_score"], row["turn_id"])
    )[:limit]
    summary = collections.Counter()
    for row in grouped.values():
        summary[row["failure_pattern"]] += 1
    return {
        "schema": "inferential-archaeology-hotspots-v1",
        "method": "frustration/scope lexical signal joined to same-session proposal trigger",
        "total_hotspot_turns": len(grouped), "pattern_counts": dict(summary),
        "rows": hotspots,
        "limits": [
            "lexical hotspot is a review lead, not a psychological diagnosis",
            "absence of a linked proposal does not mean absence of a response",
        ],
    }


def build_possibility_map(conn: sqlite3.Connection, outcome_map: dict,
                          repo: Path | None) -> dict:
    """Map named continuation lanes to exact text, Git and MAK evidence."""
    items_by_id = {item["item_id"]: item for item in outcome_map["items"]}
    groups_by_item: dict[str, str] = {}
    for group in outcome_map["groups"]:
        for item_id in group["member_ids"]:
            groups_by_item[item_id] = group["group_id"]
    all_items = _load_bifurcation_items(conn)
    lanes: list[dict] = []
    for lane in POSSIBILITY_LANES:
        folded_terms = [_strip_accents(term) for term in lane["terms"]]
        matched = [
            item for item in all_items
            if any(term in _strip_accents(item["text"]) for term in folded_terms)
        ]
        proposal_ids = [item["item_id"] for item in matched if item["kind"] == "agent_proposal"]
        idea_ids = [item["item_id"] for item in matched if item["kind"] == "user_idea"]
        outcome_counts = collections.Counter(
            items_by_id[item_id]["outcome"] for item_id in proposal_ids + idea_ids
            if item_id in items_by_id
        )
        clauses = []
        params: list[str] = []
        for term in folded_terms:
            clauses.append("(lower(c.subject) LIKE ? OR lower(f.path) LIKE ?)")
            params.extend(["%%%s%%" % term, "%%%s%%" % term])
        commit_rows = conn.execute(
            "SELECT DISTINCT c.sha,c.committed_at,c.subject,f.path,f.status "
            "FROM git_commits c JOIN git_files f ON f.sha=c.sha WHERE " +
            " OR ".join(clauses) + " ORDER BY c.committed_at DESC LIMIT 30",
            params,
        ).fetchall() if clauses else []
        current_paths = sorted({
            row[3] for row in commit_rows
            if repo is not None and Path(repo, row[3]).exists()
        })
        activity = _mak_activity_hits(conn, folded_terms, 12)
        source_turns = []
        for item in matched[:12]:
            source_turns.append({
                "item_id": item["item_id"], "kind": item["kind"],
                "turn_id": item["turn_id"], "source": item["source"],
                "occurred_at": item["occurred_at"],
                "group_id": groups_by_item.get(item["item_id"]),
                "text": item["text"][:500],
            })
        current_count = outcome_counts.get("implemented_and_current", 0)
        abandoned_count = outcome_counts.get("implemented_but_abandoned", 0)
        open_count = sum(
            outcome_counts.get(key, 0)
            for key in (
                "approved_without_verified_execution",
                "user_idea_still_open",
                "agent_proposal_never_adopted",
            )
        )
        if current_count and open_count:
            state = "mixed_current_and_open_candidates"
        elif current_count:
            state = "implemented_and_current_candidate"
        elif abandoned_count and open_count:
            state = "mixed_abandoned_and_open_candidates"
        elif abandoned_count:
            state = "implemented_but_abandoned_candidate"
        elif idea_ids:
            state = "user_seed_still_open"
        elif commit_rows:
            state = "historical_echo"
        else:
            state = "unresolved"
        lanes.append({
            "lane_id": lane["lane_id"], "label": lane["label"],
            "state": state, "terms": list(lane["terms"]),
            "agent_proposal_count": len(proposal_ids),
            "user_idea_count": len(idea_ids),
            "outcome_counts": dict(outcome_counts),
            "state_basis": {
                "current_candidates": current_count,
                "abandoned_candidates": abandoned_count,
                "open_candidates": open_count,
            },
            "group_count": len({groups_by_item.get(item_id) for item_id in proposal_ids + idea_ids}),
            "git_commit_count": len({row[0] for row in commit_rows}),
            "git_commits": [
                {"sha": row[0], "committed_at": row[1], "subject": row[2],
                 "path": row[3], "status": row[4]}
                for row in commit_rows[:12]
            ],
            "current_paths": current_paths[:20],
            "mak_activity": activity,
            "source_turns": source_turns,
            "continuation_question": lane["continuation_question"],
            "limits": [
                "lane membership is lexical retrieval, not a semantic verdict",
                "Git presence shows material continuity, not artistic value",
                "MAK activity shows execution inventory, not successful interpretation",
            ],
        })
    return {
        "schema": "inferential-archaeology-possibility-map-v1",
        "method": "named lexical lanes joined to exact bifurcation items, Git and MAK activity",
        "lanes": lanes,
    }


def build_evidence_report(sqlite_path: Path, limit: int = 12) -> dict:
    """Export a bounded, exact-provenance review packet from the SQLite index."""
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        meta = dict(conn.execute("SELECT key,value FROM meta").fetchall())
        question_rows = conn.execute(
            "SELECT q.turn_id,q.response_turn_id,q.response_present,q.status "
            "FROM question_links q ORDER BY q.response_present ASC,q.turn_id LIMIT ?",
            (limit,),
        ).fetchall()
        questions = []
        for row in question_rows:
            questions.append({
                "status": row[3], "response_present": bool(row[2]),
                "question": _turn_evidence(conn, row[0]),
                "response": _turn_evidence(conn, row[1]),
                "interpretation_required": row[3] == "needs_interpretation",
            })

        idea_rows = conn.execute(
            "SELECT id,turn_id,source,session_id,idea_timestamp,response_turn_id,"
            "response_present,session_commit_count,matching_commit_count,"
            "matching_commit_shas,status,evidence FROM idea_followups "
            "ORDER BY matching_commit_count DESC,turn_id LIMIT ?", (limit,)
        ).fetchall()
        ideas = []
        for row in idea_rows:
            try:
                shas = json.loads(row[9])
            except (TypeError, json.JSONDecodeError):
                shas = []
            ideas.append({
                "followup_id": row[0], "status": row[10],
                "evidence_link_method": "lexical_subject_overlap_only",
                "response_present": bool(row[6]),
                "session_commit_count": row[7],
                "matching_commit_count": row[8],
                "idea": _turn_evidence(conn, row[1]),
                "response": _turn_evidence(conn, row[5]),
                "commit_evidence": [
                    _commit_evidence(conn, sha) for sha in shas[:limit]
                ],
                "queue_note": (
                    "Candidate requires semantic linking; commit overlap is not "
                    "proof of implementation or abandonment."
                ),
            })

        profiles = [_row_dict(row) for row in conn.execute(
            "SELECT source,session_id,start,end,human_turns,assistant_turns,"
            "human_assistant_ratio,frustration_hits,delegation_hits,pause_hits,"
            "commits_in_window,mode_candidate FROM session_profiles "
            "WHERE mode_candidate <> 'ordinary' ORDER BY frustration_hits DESC,"
            "delegation_hits DESC LIMIT ?", (limit * 3,)
        ).fetchall()]
        rule_events = [_row_dict(row) for row in conn.execute(
            "SELECT id,sha,path,event_kind,text FROM rule_events "
            "ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
        cadence = [_row_dict(row) for row in conn.execute(
            "SELECT granularity,bucket,commit_count,author_count,file_count,"
            "insertions,deletions FROM git_cadence WHERE granularity='minute' "
            "ORDER BY commit_count DESC,bucket LIMIT ?", (limit,)
        ).fetchall()]
        activity = [_row_dict(row) for row in conn.execute(
            "SELECT department,provider,model,trigger,status,resource,COUNT(*) AS n "
            "FROM mak_activity GROUP BY department,provider,model,trigger,status,resource "
            "ORDER BY n DESC,department LIMIT ?", (limit * 4,)
        ).fetchall()]
        memories = [_row_dict(row) for row in conn.execute(
            "SELECT id,path,relative_path,node_type,origin_session,modified_at,chars,text "
            "FROM memories ORDER BY modified_at DESC,relative_path LIMIT ?", (limit,)
        ).fetchall()]
        vscode_requests = [_row_dict(row) for row in conn.execute(
            "SELECT session_id,request_id,model_id,requested_at,responded_at,"
            "prompt_tokens,completion_tokens,elapsed_ms,response_items,assistant_chars,"
            "tool_invocations,source_file,source_line FROM vscode_sol_requests "
            "ORDER BY requested_at LIMIT ?", (limit,)
        ).fetchall()]
        vscode_actions = [_row_dict(row) for row in conn.execute(
            "SELECT event_kind,tool_id,COUNT(*) AS n FROM vscode_sol_actions "
            "GROUP BY event_kind,tool_id ORDER BY n DESC,event_kind LIMIT ?", (limit * 4,)
        ).fetchall()]
        proposal_rows = conn.execute(
            "SELECT id,turn_id,source,session_id,proposal_timestamp,trigger_turn_id,"
            "prompt_driven,approval_turn_id,approval_present,direct_action_count,"
            "session_commit_count,matching_commit_count,matching_commit_shas,status,evidence "
            "FROM proposal_followups ORDER BY direct_action_count DESC,prompt_driven DESC,id "
            "LIMIT ?", (limit * 3,)
        ).fetchall()
        proposal_repetitions, proposal_repetition_summary = _proposal_repetition_index(conn)
        proposal_scale_summary = _proposal_scale_summary(conn)
        proposals = []
        for row in proposal_rows:
            try:
                shas = json.loads(row[12])
            except (TypeError, json.JSONDecodeError):
                shas = []
            proposals.append({
                "proposal_id": row[0], "status": row[13],
                "authorship": "agent_turn_not_user_idea",
                "prompt_driven": bool(row[6]),
                "approval_present": bool(row[8]),
                "direct_action_count": row[9],
                "session_commit_count": row[10],
                "matching_commit_count": row[11],
                "matching_commit_shas": shas,
                "exact_text_fingerprint": proposal_repetitions.get(row[0], {}).get("fingerprint"),
                "exact_text_repeat_count": proposal_repetitions.get(row[0], {}).get("repeat_count", 0),
                "proposal": _turn_evidence(conn, row[1]),
                "trigger": _turn_evidence(conn, row[5]),
                "approval": _turn_evidence(conn, row[7]),
                "evidence": json.loads(row[14]),
                "queue_note": (
                    "Agent-generated proposals are tracked separately from user ideas; "
                    "acceptance, action, and nearby commits are not completion proof."
                ),
            })
        cross_source_packet = build_cross_source_packet(conn, min(10, max(1, limit)))
        repo = Path(meta["repo"]) if meta.get("repo") else None
        bifurcation_map = build_bifurcation_map(conn, repo)
        hotspot_map = build_hotspot_map(conn, bifurcation_map)
        possibility_map = build_possibility_map(conn, bifurcation_map, repo)
        return {
            "schema": "inferential-archaeology-report-v1",
            "source_meta": meta,
            "interpretation_policy": {
                "candidate_status": "mechanical candidate, not a verdict",
                "question_status": "mechanically unresolved or needs interpretation",
                "idea_commit_link": "lexical_subject_overlap_only",
                "rule_change": "removed rule text does not establish why it was removed",
                "activity": "execution inventory, not evidence of artistic or semantic truth",
                "memories": "project memory is exact-text context, not a new conversation turn",
                "vscode_sol": "SOL request/tool metadata is provenance; it does not prove repository coverage or implementation",
                "cross_source_packet": "ranked retrieval packet; anchors and temporal overlap require human semantic review",
                "proposal_authorship": "assistant proposal text is not user idea authorship; open prompts are recorded as triggers",
                "direct_action_scope": {
                    "claude_code": ["Edit", "Write", "MultiEdit", "NotebookEdit"],
                    "codex": ["apply_patch"],
                    "vscode_sol": "existing SOL tool metadata",
                    "excluded_from_direct_mutation_claims": [
                        "shell/Bash commands without a parsed file mutation",
                        "unpaired or failed tool calls",
                        "assistant descriptions without an action record",
                        "Claude Workflow/Agent and Codex exec wrappers",
                    ],
                    "meaning": "direct action is bounded evidence of an attempted file mutation, not proof of adoption, authorship, or semantic success",
                },
            },
            "question_queue": questions,
            "idea_queue": ideas,
            "mode_profiles": profiles,
            "rule_change_candidates": rule_events,
            "git_cadence_peaks": cadence,
            "mak_activity_summary": activity,
            "memory_index": memories,
            "vscode_sol_requests": vscode_requests,
            "vscode_sol_action_summary": vscode_actions,
            "proposal_queue": proposals,
            "proposal_repetition": proposal_repetition_summary,
            "proposal_scale": proposal_scale_summary,
            "cross_source_seed_packet": cross_source_packet,
            "bifurcation_map": bifurcation_map,
            "hotspot_map": hotspot_map,
            "possibility_map": possibility_map,
        }
    finally:
        conn.close()


def report(args: argparse.Namespace) -> int:
    packet = build_evidence_report(Path(args.sqlite).resolve(), args.limit)
    output = Path(args.output).resolve() if args.output else None
    text = _json(packet) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def search(args: argparse.Namespace) -> int:
    conn = sqlite3.connect(Path(args.sqlite).resolve())
    if args.corpus in ("turns", "both"):
        rows = conn.execute(
            "SELECT turns.id, turns.session_id, turns.occurred_at, turns.role, turns.source_file, "
            "turns.source_line, snippet(turns_fts, 0, '[', ']', '...', 24) "
            "FROM turns_fts JOIN turns ON turns.id = turns_fts.rowid "
            "WHERE turns_fts MATCH ? AND turns.is_duplicate = 0 "
            "AND turns.analysis_exclusion IS NULL "
            "ORDER BY turns.id LIMIT ?", (args.query, args.limit),
        ).fetchall()
        for row in rows:
            print(json.dumps({"corpus": "turns", "id": row[0], "session": row[1],
                              "ts": row[2], "role": row[3], "file": row[4],
                              "line": row[5], "snippet": row[6]}, ensure_ascii=False))
    if args.corpus in ("memories", "both"):
        rows = conn.execute(
            "SELECT memories.id,memories.path,memories.relative_path,"
            "memories.modified_at,snippet(memories_fts,0,'[',']','...',24) "
            "FROM memories_fts JOIN memories ON memories.id=memories_fts.rowid "
            "WHERE memories_fts MATCH ? ORDER BY memories.id LIMIT ?",
            (args.query, args.limit),
        ).fetchall()
        for row in rows:
            print(json.dumps({"corpus": "memories", "id": row[0], "file": row[1],
                              "relative_path": row[2], "modified_at": row[3],
                              "snippet": row[4]}, ensure_ascii=False))
    conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--repo", default=str(ROOT))
    build_parser.add_argument("--claude-root", default=str(DEFAULT_CLAUDE_ROOT))
    build_parser.add_argument("--claude-web", default=str(DEFAULT_CLAUDE_WEB)
                              if DEFAULT_CLAUDE_WEB.exists() else None)
    build_parser.add_argument("--codex-root", default=str(DEFAULT_CODEX_ROOT)
                              if DEFAULT_CODEX_ROOT.exists() else None)
    build_parser.add_argument("--codex-exclude-file", action="append", default=[],
                              help="Exclude a live Codex JSONL file from the snapshot")
    build_parser.add_argument("--vscode-root", action="append", default=[],
                              help="Read-only VS Code chatSessions root/file; SOL requests only")
    build_parser.add_argument("--mak-activity", default=None,
                              help="Read-only MAK activity.jsonl snapshot")
    build_parser.add_argument("--memory-root", default=(str(DEFAULT_CLAUDE_MEMORY)
                              if DEFAULT_CLAUDE_MEMORY.exists() else None),
                              help="Project-scoped Claude memory directory")
    build_parser.add_argument("--output", default=str(DEFAULT_OUTPUT / "archaeology.sqlite"))
    build_parser.add_argument("--duckdb", default=None)
    build_parser.add_argument("--summary", default=None)
    search_parser = sub.add_parser("search")
    search_parser.add_argument("--sqlite", required=True)
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--corpus", choices=("turns", "memories", "both"),
                               default="turns")
    report_parser = sub.add_parser("report")
    report_parser.add_argument("--sqlite", required=True)
    report_parser.add_argument("--output", default=None)
    report_parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            print(json.dumps(build(args), ensure_ascii=False, indent=2))
            return 0
        if args.command == "report":
            return report(args)
        return search(args)
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
