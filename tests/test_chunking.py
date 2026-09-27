"""切块器测试：标题路径、表格完整性、长节拆分。"""

from app.services.chunking import split_markdown


def test_heading_path_is_built() -> None:
    md = "# 政策\n\n## 运费\n\n满 99 元包邮。\n"
    chunks = split_markdown(md, max_chars=100)
    assert any(c.heading_path == "政策 > 运费" for c in chunks)
    assert any("满 99 元包邮" in c.content for c in chunks)


def test_table_stays_in_one_chunk() -> None:
    md = "# 退换货\n\n## 时效\n\n| 环节 | 时间 |\n|---|---|\n| 退货 | 7 天 |\n| 换货 | 15 天 |\n"
    # max_chars 故意设得很小，逼它尽量拆块
    chunks = split_markdown(md, max_chars=10)
    table_chunks = [c for c in chunks if "| 环节 | 时间 |" in c.content]
    assert len(table_chunks) == 1
    assert "| 换货 | 15 天 |" in table_chunks[0].content


def test_long_section_splits_into_multiple_chunks() -> None:
    body = "\n\n".join(f"段落{i} " + "x" * 80 for i in range(6))
    md = f"# H\n\n## S\n\n{body}\n"
    chunks = split_markdown(md, max_chars=120)
    same_section = [c for c in chunks if c.heading_path == "H > S"]
    assert len(same_section) > 1


def test_empty_text_returns_no_chunks() -> None:
    assert split_markdown("", max_chars=100) == []
    assert split_markdown("\n\n  \n", max_chars=100) == []
