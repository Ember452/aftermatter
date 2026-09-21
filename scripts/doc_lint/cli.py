"""doc-lint CLI（对齐 architecture/cli.md 输出契约：--json stdout 纯净、诊断走 stderr）。

退出码（architecture/cli.md 契约子集）：0 无违规 / 1 有违规 / 4 内部错误。
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

from ._core import Finding
from . import check_all


def _repo_root_from(here: Path) -> Path:
    """从 scripts/doc_lint/ 反推仓库根。向上找 pyproject.toml。

    找不到即抛错，绝不猜测路径——猜错会静默扫描空目录产出"全绿"假象。
    """
    current = here.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(
        "未能通过向上查找 pyproject.toml 定位仓库根；请用 --root 显式指定。"
    )


def _format_text(findings: list[Finding]) -> str:
    if not findings:
        return "doc-lint: OK (no violations)\n"
    lines = [f"doc-lint: {len(findings)} violation(s)\n"]
    for f in findings:
        loc = f"{f.path}" + (f":{f.line}" if f.line else "")
        lines.append(f"  [{f.rule}] {loc}\n    {f.message}")
        if f.hint:
            lines.append(f"    hint: {f.hint}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="doc_lint",
        description="AfterMatter 文档一致性检查（ADR-0011）",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="仓库根路径（默认自动定位）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="stdout 输出机器可读 JSON（诊断走 stderr），供 CI 消费",
    )
    parser.add_argument(
        "--fix-hint",
        action="store_true",
        help="附带修复建议输出（不影响退出码）",
    )
    args = parser.parse_args(argv)

    try:
        root = args.root.resolve() if args.root else _repo_root_from(Path(__file__))
        findings = check_all(root)
    except Exception:  # 内部错误 → exit 4，与"有违规"=1 区分（architecture/cli.md 契约）
        traceback.print_exc(file=sys.stderr)
        if args.json:
            print(json.dumps(
                {"error": "doc-lint internal error", "violation_count": None},
                ensure_ascii=False,
            ))
        print("doc-lint: internal error (traceback on stderr)", file=sys.stderr)
        return 4

    findings.sort(key=lambda f: (str(f.path), f.rule, f.line or 0))

    if not args.fix_hint:
        findings = [
            Finding(path=f.path, rule=f.rule, line=f.line, message=f.message, hint=None)
            for f in findings
        ]

    if args.json:
        payload = {
            "root": str(root),
            "violation_count": len(findings),
            "violations": [f.to_dict() for f in findings],
        }
        # 契约：stdout 纯 JSON，人类信息走 stderr
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"doc-lint: {len(findings)} violation(s)", file=sys.stderr)
    else:
        sys.stdout.write(_format_text(findings))

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
