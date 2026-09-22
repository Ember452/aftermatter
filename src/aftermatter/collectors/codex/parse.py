"""Codex 会话 JSONL 适配器：信封两层判别 + 跨行上下文回填。

与 Claude 的关键差异全部来自实测（3 会话 / 138 行 / 409 KB），不是记忆：
1. 判别在 `type` + `payload.type` 两层；
2. `session_id`/`cwd` 只在 `session_meta`（3 次），`model` 只在 `turn_context`（3 次），
   所以必须跨行 carry-forward，不能逐行取；
3. `arguments` 是 JSON 字符串（24/24）；
4. `output` 是纯字符串且 24/25 不带退出码 → **`result_ok` 一律 None**，不猜成败。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from aftermatter.collectors.artifacts import is_self_artifact
from aftermatter.collectors.codex.discover import discover_sessions
from aftermatter.collectors.codex.mapping import (
    CALL_PAIRS,
    HOST,
    LIFECYCLE_PAIRS,
    OUTPUT_PAIRS,
    LineDisposition,
    classify_record,
    command_from,
    message_kind,
    parse_arguments,
    paths_from_patch,
    safe_reason,
    workdir_from,
)
from aftermatter.collectors.jsonl import read_lines
from aftermatter.collectors.protocol import ParseTally
from aftermatter.core.errors import AfterMatterError, ParseError
from aftermatter.core.fingerprint import fingerprint
from aftermatter.core.pathutil import norm_path
from aftermatter.core.timeutil import parse_ts
from aftermatter.evidence.models import (
    AdapterHealth,
    ERef,
    EventKind,
    ParseStats,
    RawEvent,
    SessionRef,
)

# 实测 envelope 形状在 0.147.0-alpha.1.2 → 0.153.1 之间未变，故整个 0.x 视为受支持；
# 命中不了只降级（lane 标 degraded），不猜映射。
SUPPORTED_VERSION_PREFIXES = ("0.",)
_TEXT_BLOCK_TYPES = frozenset({"input_text", "output_text", "text"})
_EventDraft = tuple[EventKind, str | None, tuple[str, ...], str | None, bool | None]


@dataclass(frozen=True)
class _Context:
    """跨行 carry-forward：会话身份、工作目录与当前模型。"""

    session_id: str = ""
    cwd: str = ""
    model: str | None = None


class CodexAdapter:
    """`SessionAdapter` 协议的 Codex 实现（与 ClaudeAdapter 同构，便于跨宿主统计合并）。"""

    def __init__(self, sessions_root: str | Path) -> None:
        self._sessions_root = Path(sessions_root)
        self._tally = ParseTally()
        self._detected: tuple[str, ...] = ()

    @property
    def stats(self) -> ParseStats:
        return self._tally.to_stats()

    def reset_stats(self) -> None:
        self._tally = ParseTally()
        self._detected = ()

    def discover(self, workspace: str | Path | None = None) -> list[SessionRef]:
        refs = discover_sessions(self._sessions_root, workspace=workspace)
        self._detected = tuple(sorted({ref.format_version for ref in refs if ref.format_version}))
        return refs

    def healthcheck(self) -> AdapterHealth:
        if not self._detected:
            support = "unknown"
        elif all(name.startswith(SUPPORTED_VERSION_PREFIXES) for name in self._detected):
            support = "ok"
        else:
            support = "degraded"
        return AdapterHealth(host=HOST, support=support, detected_versions=self._detected)

    async def parse(self, ref: SessionRef, *, since_offset: int = 0) -> AsyncIterator[RawEvent]:
        """流式产出一个会话文件的事件；坏行 fail-soft，坏文件 fail-hard。"""
        raw = await asyncio.to_thread(_read_bytes, ref.path)
        source_path = _source_path(ref, self._sessions_root)
        context = _Context(session_id="", cwd="")
        for line in read_lines(raw, since_offset):
            events, stop_parsing, context = self._handle_line(
                ref, source_path, line.content, line.byte_start, line.line_no, context
            )
            for event in events:
                yield event
            if stop_parsing:
                return

    # --- 行级处理 -------------------------------------------------------

    def _handle_line(
        self,
        ref: SessionRef,
        source_path: str,
        content: bytes,
        byte_start: int,
        line_no: int,
        context: _Context,
    ) -> tuple[list[RawEvent], bool, _Context]:
        """返回 (本行事件, 是否终止整文件, 更新后的上下文)。空行已由 `read_lines` 滤掉。"""
        self._tally.lines_total += 1
        try:
            record = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._count(LineDisposition.MALFORMED, "not_json")
            return [], False, context
        if not isinstance(record, Mapping):
            self._count(LineDisposition.MALFORMED, "not_object")
            return [], False, context

        disposition, reason = classify_record(record)
        if disposition is LineDisposition.NOT_OURS:
            self._count(disposition, reason)
            return [], True, context

        payload = record.get("payload")
        payload = payload if isinstance(payload, Mapping) else {}
        # carry-forward 必须在任何提前返回之前做：`turn_context` 本身是 ignored，
        # 但它是 model/cwd 的唯一来源（实测逐行记录都不带 model）。
        context = self._carry_forward(record, payload, context)
        if disposition is not LineDisposition.PARSED:
            self._count(disposition, reason)
            return [], False, context
        try:
            moment = parse_ts(_as_str(record.get("timestamp")) or "")
        except ParseError:
            self._count(LineDisposition.UNPARSED, "ts_unparsable")
            return [], False, context

        pair = (record.get("type"), _as_str(payload.get("type")))
        drafts, notes = self._drafts_for(pair, payload, context)
        if not drafts:
            # 行被认下来却没产出事件：计一次 ignored，并用首个 reason 说明为什么。
            self._tally.ignored += 1
            self._tally.add_reason(notes[0] if notes else "no_blocks")
        else:
            # 有事件产出时，notes 是字段级注记（如 arguments_unparsable），不动行级计数器。
            for note in notes:
                self._tally.add_reason(note)
        return (
            [
                self._event(
                    context, moment, pair, draft, ref, source_path, byte_start, content, line_no
                )
                for draft in drafts
            ],
            False,
            context,
        )

    def _carry_forward(
        self, record: Mapping[str, object], payload: Mapping[str, object], context: _Context
    ) -> _Context:
        """`turn_context`/`session_meta` 虽是 ignored 或 lifecycle，仍要读它：model 只在那里。"""
        outer = _as_str(record.get("type")) or ""
        updated = context
        if outer == "session_meta":
            updated = replace(
                updated,
                session_id=_as_str(payload.get("session_id")) or updated.session_id,
                cwd=_as_str(payload.get("cwd")) or updated.cwd,
            )
        elif outer == "turn_context":
            updated = replace(
                updated,
                model=_as_str(payload.get("model")) or updated.model,
                cwd=_as_str(payload.get("cwd")) or updated.cwd,
            )
        return updated

    def _drafts_for(
        self,
        pair: tuple[object, str | None],
        payload: Mapping[str, object],
        context: _Context,
    ) -> tuple[list[_EventDraft], list[str]]:
        typed_pair = (str(pair[0]), pair[1])
        if typed_pair in LIFECYCLE_PAIRS:
            return [(EventKind.LIFECYCLE, None, (), None, None)], []
        if typed_pair in OUTPUT_PAIRS:
            # 实测 24/25 条 output 不带退出码：成败不可观测，如实留 None。
            return [(EventKind.TOOL_RESULT, None, (), None, None)], []
        if typed_pair in CALL_PAIRS:
            return self._call_draft(payload, context)
        if typed_pair == ("response_item", "message"):
            kind, reason = message_kind(payload)
            if kind is None:
                return [], [reason]
            blocks = _blocks(payload.get("content"))
            if not any(block.get("type") in _TEXT_BLOCK_TYPES for block in blocks):
                return [], ["no_text_block"]
            return [(kind, None, (), None, None)], []
        # 以下分支结构上不可达：classify_record 只会对 LIFECYCLE/CALL/OUTPUT/message 这几对
        # 返回 PARSED。保留而不是删掉，是为了两张表以后不同步时（加了新 payload.type 却忘了
        # 接分派）会落到可见的 unparsed/ignored，而不是静默丢行。
        return [], [safe_reason(f"{typed_pair[0]}_{typed_pair[1]}")]

    def _call_draft(
        self, payload: Mapping[str, object], context: _Context
    ) -> tuple[list[_EventDraft], list[str]]:
        """工具调用：`function_call` 带 `arguments`（JSON 字符串），`custom_tool_call` 带 `input`
        （补丁文本）。两者互斥（实测 arguments 24 / input 1），所以不对缺其中一个报错。
        """
        name = _as_str(payload.get("name"))
        arguments: Mapping[str, object] | None = None
        if "input" in payload:
            raw_paths = paths_from_patch(payload.get("input"))
            command, notes = None, []
        else:
            arguments, note = parse_arguments(payload.get("arguments"))
            notes = [] if note is None else [note]
            command = command_from(arguments)
            raw_paths = _workdir_as_path(arguments) if command is None else []
        paths, outside = self._normalize(raw_paths, _workdir_from(arguments, context))
        if outside:
            notes.extend(["outside_workspace"] * outside)
        return [(EventKind.TOOL_CALL, name, paths, command, None)], notes

    def _normalize(self, raw_paths: list[str], root: str) -> tuple[tuple[str, ...], int]:
        paths: list[str] = []
        outside = 0
        for value in raw_paths:
            if is_self_artifact(value):
                self._count(LineDisposition.PARSED, "self_artifact_path", self_artifact=True)
                continue
            try:
                paths.append(norm_path(value, root) if root else value)
            except AfterMatterError:
                outside += 1
                self._tally.outside_path_count += 1
        return tuple(paths), outside

    def _event(
        self,
        context: _Context,
        moment: datetime,
        pair: tuple[object, str | None],
        draft: _EventDraft,
        ref: SessionRef,
        source_path: str,
        byte_start: int,
        content: bytes,
        line_no: int,
    ) -> RawEvent:
        kind, tool_name, target_paths, command_text, result_ok = draft
        self._tally.parsed += 1
        eref = ERef(
            source_id=ref.source_id,
            source_path=source_path,
            byte_start=byte_start,
            byte_len=len(content),
            digest=hashlib.sha256(content).hexdigest(),
            line_no=line_no,
        )
        payload = {
            "host": HOST,
            "session_id": context.session_id,
            "kind": str(kind),
            "tool_name": tool_name,
            "target_paths": list(target_paths),
            "result_ok": result_ok,
            "pair": f"{pair[0]}/{pair[1]}",
            "ref": eref.digest,
        }
        return RawEvent(
            host=HOST,
            session_id=context.session_id,
            seq=self._tally.parsed,
            ts=moment,
            kind=kind,
            cwd=context.cwd,
            evidence_ref=eref,
            fingerprint=fingerprint(payload),
            tool_name=tool_name,
            target_paths=target_paths,
            command_text=command_text,
            model=context.model,
            result_ok=result_ok,
        )

    def _count(self, disposition: LineDisposition, reason: str, **flags: bool) -> None:
        counter = {
            LineDisposition.PARSED: None,
            LineDisposition.IGNORED: "ignored",
            LineDisposition.UNPARSED: "unparsed",
            LineDisposition.NOT_OURS: "not_ours",
            LineDisposition.MALFORMED: "malformed_json",
        }[disposition]
        if counter is not None:
            setattr(self._tally, counter, getattr(self._tally, counter) + 1)
        if flags.get("self_artifact"):
            self._tally.excluded_self_artifact += 1
        self._tally.add_reason(safe_reason(reason))


def _read_bytes(path: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        # 断开异常链：OSError 文本含主机绝对路径。
        raise ParseError("session_unreadable", context={"kind": type(exc).__name__}) from None


def _source_path(ref: SessionRef, sessions_root: Path) -> str:
    try:
        return norm_path(ref.path, sessions_root)
    except AfterMatterError:
        return Path(ref.path).name


def _blocks(content: object) -> list[Mapping[str, object]]:
    if isinstance(content, str):
        return [{"type": "input_text", "text": content}]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, Mapping)]
    return []


def _workdir_as_path(arguments: Mapping[str, object] | None) -> list[str]:
    """没有 shell 命令时，`workdir` 是唯一能代表“操作发生在哪”的路径证据。"""
    workdir = workdir_from(arguments)
    return [workdir] if workdir else []


def _workdir_from(arguments: Mapping[str, object] | None, context: _Context) -> str:
    return workdir_from(arguments) or context.cwd


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
