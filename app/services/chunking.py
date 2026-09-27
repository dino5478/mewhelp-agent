"""文档切块：按 Markdown 标题层级与表格结构切分。

设计要点：
- 用标题路径（如「退换货政策 > 七天无理由退货」）给每块打上定位信息；
- 表格行「| ... |」被视为一个整体，绝不拆散（否则条件会被切断）；
- 段落按空行聚合，再按 max_chars 打包，超长时拆成多块。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Chunk:
    content: str
    heading_path: str


def _is_table_row(line: str) -> bool:
    return line.strip().startswith("|")


def _split_blocks(lines: list[str]) -> list[str]:
    """把若干行聚合成块：连续表格行=一个表格块；段落以空行分隔。"""
    blocks: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            text = "\n".join(buf).strip()
            if text:
                blocks.append(text)
            buf.clear()

    for line in lines:
        if _is_table_row(line):
            if buf and not _is_table_row(buf[-1]):
                flush()
            buf.append(line)
        else:
            if buf and _is_table_row(buf[-1]):
                flush()
            if line.strip() == "":
                flush()
            else:
                buf.append(line)
    flush()
    return blocks


def _pack(blocks: list[str], heading_path: str, max_chars: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    cur = ""
    for block in blocks:
        if not cur:
            cur = block
        elif len(cur) + 2 + len(block) <= max_chars:
            cur += "\n\n" + block
        else:
            chunks.append(Chunk(cur, heading_path))
            cur = block
    if cur:
        chunks.append(Chunk(cur, heading_path))
    return chunks


def split_markdown(text: str, max_chars: int = 500) -> list[Chunk]:
    """按标题分节 -> 每节切块；返回带标题路径的 Chunk 列表。"""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    stack: list[tuple[int, str]] = []
    cur: list[str] = []

    def flush_section() -> None:
        if cur:
            heading_path = " > ".join(title for _, title in stack)
            sections.append((heading_path, list(cur)))
            cur.clear()

    for line in lines:
        match = _HEADING_RE.match(line)
        if match:
            flush_section()
            level = len(match.group(1))
            title = match.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            cur.append(line)
    flush_section()

    chunks: list[Chunk] = []
    for heading_path, sec_lines in sections:
        blocks = _split_blocks(sec_lines)
        if not blocks:
            continue
        chunks.extend(_pack(blocks, heading_path, max_chars))
    return chunks
