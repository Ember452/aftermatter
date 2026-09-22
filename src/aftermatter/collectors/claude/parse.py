"""Claude JSONL 适配器：流式解析、行级 fail-soft、三类去向计数。

阻塞与内存债：整文件读入后经 `asyncio.to_thread` 离开事件循环；FR-A6 要求的
"1 GB 会话 < 256 MB 内存"流式改造属 T6.4，本任务不偷偷做。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator, Mapping
from datetime import datetime
from pathlib import Path

from aftermatter.collectors.artifacts import is_self_artifact
from aftermatter.collectors.claude.discover import discover_sessions
from aftermatter.collectors.claude.mapping import (
    COMMAND_INPUT_KEYS,
    HOST,
    LIFECYCLE_SUBTYPES,
    PATH_INPUT_KEYS,
    SELF_ARTIFACT_REASON,
    LineDisposition,
    classify_record,
    content_blocks,
    safe_reason,
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

SUPPORTED_VERSION_PREFIXES = ("2.1.",)
_EventDraft = tuple[EventKind, str | None, tuple[str, ...], str | None, bool | None]


class ClaudeAdapter:
    """`SessionAdapter` 协议的 Claude 实现。

    单次 `parse` 内 `seq` 从 1 递增；断点续读时下游按 `ts`+`seq` 重排，因此跨调用的稳定
    语义是"全量序列去掉已消费前缀"，不是"seq 全局连续"。
    """

    def __init__(self, sessions_root: str | Path) -> None:
        self._sessions_root = Path(sessions_root)
        self._tally = ParseTally()
        self._detected: tuple[str, ...] = ()

    @property
    def stats(self) -> ParseStats:
        return self._tally.to_stats()

    def reset_stats(self) -> None:
        """清空行级计数：一次 run 一个统计窗口，跨 run 累加会污染 unparsed 信号。"""
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
        for line in read_lines(raw, since_offset):
            events, stop_parsing = self._handle_line(
                ref, source_path, line.content, line.byte_start, line.line_no
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
    ) -> tuple[list[RawEvent], bool]:
        """返回 (本行事件, 是否终止整文件解析)。空行已由 `read_lines` 滤掉。"""
        self._tally.lines_total += 1
        try:
            record = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._count(LineDisposition.MALFORMED, "not_json")
            return [], False
        if not isinstance(record, Mapping):
            self._count(LineDisposition.MALFORMED, "not_object")
            return [], False

        disposition, reason = classify_record(record)
        if disposition is not LineDisposition.PARSED:
            self._count(disposition, reason)
            # 正面判定为外来 → 整文件不再解析，避免用假事件污染下游。
            return [], disposition is LineDisposition.NOT_OURS

        try:
            moment = parse_ts(_as_str(record.get("timestamp")) or "")
        except ParseError:
            self._count(LineDisposition.UNPARSED, "ts_unparsable")
            return [], False

        eref = ERef(
            source_id=ref.source_id,
            source_path=source_path,
            byte_start=byte_start,
            byte_len=len(content),
            digest=hashlib.sha256(content).hexdigest(),
            line_no=line_no,
        )
        session_id = _as_str(record.get("sessionId")) or ""
        cwd = _as_str(record.get("cwd")) or ""
        return self._build_events(record, session_id, cwd, moment, eref), False

    def _build_events(
        self,
        record: Mapping[str, object],
        session_id: str,
        cwd: str,
        moment: datetime,
        eref: ERef,
    ) -> list[RawEvent]:
        drafts, ignored_reasons = self._drafts_for(record, cwd)
        if not drafts and not ignored_reasons:
            # 行被认下来了却没产出任何事件（空 content 等）：归 ignored 而不是静默消失，
            # 否则这类行会从所有计数器里漏掉，去向账对不上。
            ignored_reasons = ["no_blocks"]
        for reason in ignored_reasons:
            self._tally.ignored += 1
            self._tally.add_reason(safe_reason(reason))
        events: list[RawEvent] = []
        for kind, tool_name, target_paths, command_text, result_ok in drafts:
            events.append(
                self._event(
                    session_id=session_id,
                    cwd=cwd,
                    moment=moment,
                    kind=kind,
                    tool_name=tool_name,
                    target_paths=target_paths,
                    command_text=command_text,
                    result_ok=result_ok,
                    model=_message_str(record, "model"),
                    eref=eref,
                )
            )
        return events

    def _drafts_for(
        self, record: Mapping[str, object], cwd: str
    ) -> tuple[list[_EventDraft], list[str]]:
        """产出事件草稿与 ignored 的 reason 清单（每条一项）。

        本方法不碰计数器：只交草稿与原因，计数统一在 `_build_events` 一处发生——
        上一版两边各记一半，导致 system 子类型被错标成 thinking_block。
        """
        blocks = content_blocks(record.get("message"))
        record_type = _as_str(record.get("type")) or ""
        drafts: list[_EventDraft] = []
        ignored: list[str] = []
        if record_type == "user":
            results = [block for block in blocks if block.get("type") == "tool_result"]
            if results:
                drafts = [
                    (EventKind.TOOL_RESULT, None, (), None, not bool(block.get("is_error")))
                    for block in results
                ]
            elif any(block.get("type") == "text" for block in blocks):
                drafts = [(EventKind.USER_PROMPT, None, (), None, None)]
        elif record_type == "assistant":
            ignored = ["thinking_block"] * sum(
                1 for block in blocks if block.get("type") == "thinking"
            )
            if any(block.get("type") == "text" for block in blocks):
                drafts.append((EventKind.ASSISTANT_MESSAGE, None, (), None, None))
            for block in blocks:
                if block.get("type") != "tool_use":
                    continue
                paths, command_text = self._tool_inputs(block.get("input"), cwd)
                drafts.append(
                    (EventKind.TOOL_CALL, _as_str(block.get("name")), paths, command_text, None)
                )
        elif record_type == "system":
            # 分派表与 mapping.MAPPED_TYPES 是同一份知识：classify_record 只放行这三类，
            # 所以此处不存在“未知 type”落入路径。若以后 MAPPED_TYPES 加了新类型而这里没接，
            # 那行会落到 `_build_events` 的 no_blocks 计数里（可见），不会被静默吞掉。
            if _as_str(record.get("subtype")) in LIFECYCLE_SUBTYPES:
                drafts = [(EventKind.LIFECYCLE, None, (), None, None)]
            else:
                ignored = ["system_subtype"]
        return drafts, ignored

    def _event(
        self,
        *,
        session_id: str,
        cwd: str,
        moment: datetime,
        kind: EventKind,
        tool_name: str | None,
        target_paths: tuple[str, ...],
        command_text: str | None,
        result_ok: bool | None,
        model: str | None,
        eref: ERef,
    ) -> RawEvent:
        self._tally.parsed += 1
        payload = {
            "host": HOST,
            "session_id": session_id,
            "kind": str(kind),
            "tool_name": tool_name,
            "target_paths": list(target_paths),
            "result_ok": result_ok,
            "ref": eref.digest,
        }
        return RawEvent(
            host=HOST,
            session_id=session_id,
            seq=self._tally.parsed,
            ts=moment,
            kind=kind,
            cwd=cwd,
            evidence_ref=eref,
            fingerprint=fingerprint(payload),
            tool_name=tool_name,
            target_paths=target_paths,
            command_text=command_text,
            model=model,
            result_ok=result_ok,
        )

    def _tool_inputs(self, raw_input: object, cwd: str) -> tuple[tuple[str, ...], str | None]:
        if not isinstance(raw_input, Mapping):
            return (), None
        paths: list[str] = []
        for key in PATH_INPUT_KEYS:
            value = _as_str(raw_input.get(key))
            if not value:
                continue
            if is_self_artifact(value):
                self._count(LineDisposition.PARSED, SELF_ARTIFACT_REASON, self_artifact=True)
                continue
            try:
                paths.append(norm_path(value, cwd) if cwd else value)
            except AfterMatterError:
                self._count(LineDisposition.PARSED, "outside_workspace", outside=True)
        command_text = next(
            (text for key in COMMAND_INPUT_KEYS if (text := _as_str(raw_input.get(key)))),
            None,
        )
        return tuple(paths), command_text

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
        if flags.get("outside"):
            self._tally.outside_path_count += 1
        self._tally.add_reason(safe_reason(reason))


def _read_bytes(path: str) -> bytes:
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        # 断开异常链：OSError 文本含主机绝对路径。
        raise ParseError("session_unreadable", context={"kind": type(exc).__name__}) from None


def _source_path(ref: SessionRef, sessions_root: Path) -> str:
    """引用路径写成"相对源根"，主机绝对路径不进 ERef。"""
    try:
        return norm_path(ref.path, sessions_root)
    except AfterMatterError:
        return Path(ref.path).name


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _message_str(record: Mapping[str, object], key: str) -> str | None:
    message = record.get("message")
    if isinstance(message, Mapping):
        return _as_str(message.get(key))
    return None
