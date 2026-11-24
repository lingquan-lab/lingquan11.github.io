#!/usr/bin/env python3
"""检查文章 Markdown 里 kramdown（本站渲染器）会渲染坏、但编辑器预览看不出来的写法。只读，不改文件。

    python3 .claude/skills/lingquan-blog/scripts/lint_markdown.py [文章.md ...] [--site _site]

不给文件就检查 _posts/ 全部文章。给了 --site，还会拿构建结果核对：源文件里每张表格，
页面里都必须有对应的 <table>；页面正文里不能出现塌掉的表格文本（例如「|—|—|」）。

为什么需要它：编辑器、GitHub、掘金用的是 GFM，表格前后不空行也能显示；本站的 kramdown
不行，整张表会塌成一段竖线文字，「---」还会被转成破折号「—」。2026-11-24《1×4脉动阵列
乘加单元》的 4 张表就是这样坏的。

错误（必须改，退出码 1）：
  E1 表格上一行不是空行（标题、正文紧挨着表格都不行）
  E2 表格下一行不是空行（紧跟的文字会让整张表失效）
  E3 表格第二行不是分隔行 |---|---|（或分隔行里有破折号「—」「–」等）
  E4 用了全角竖线「｜」画表格
  E5 （需 --site）源文件的表格数和页面里的 <table> 数对不上，或页面里有塌掉的表格文本
警告（看一眼，确认没问题即可）：
  W1 某行的列数和表头不一致（单元格里有没转义的 |，要写成 \\|）
  W2 独占一行的 $$ 紧跟在正文后面（kramdown 会把整段公式当行内公式）
"""
import re
import sys
from pathlib import Path

SEP_CELL = re.compile(r"^\s*:?-+:?\s*$")
FENCE = re.compile(r"^\s{0,3}(```|~~~)")


def split_cells(line: str) -> list[str]:
    s = re.sub(r"`[^`]*`", "x", line.strip())  # 行内代码里的 | 不算分隔
    s = s.replace("\\|", "x")
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return s.split("|")


def is_table_line(line: str) -> bool:
    s = line.lstrip()
    return len(line) - len(s) <= 3 and s.startswith("|") and s.count("|") >= 2


def body_lines(path: Path) -> list[tuple[int, str]]:
    """返回 (行号, 内容)，跳过 front matter 和代码块。"""
    lines = path.read_text(encoding="utf-8").split("\n")
    out, i, in_fence = [], 0, False
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        i += 1
    for n in range(i, len(lines)):
        line = lines[n].rstrip("\r")
        if FENCE.match(line):
            in_fence = not in_fence
            out.append((n + 1, "```"))  # 代码块边界当作非空行
            continue
        out.append((n + 1, "```" if in_fence else line))
    return out


def lint(path: Path):
    errors, warns, tables = [], [], 0
    rows = body_lines(path)
    k = 0
    while k < len(rows):
        n, line = rows[k]
        if line.lstrip().startswith("｜") and line.count("｜") >= 2:
            errors.append((n, "E4", "用了全角竖线「｜」，表格要用半角「|」"))
        if line.strip() == "$$" and k > 0 and rows[k - 1][1].strip() and rows[k - 1][1].strip() != "$$":
            # 只看开头的 $$：往前数同一段落里的 $$ 个数
            j, count = k - 1, 0
            while j >= 0 and rows[j][1].strip():
                count += rows[j][1].strip() == "$$"
                j -= 1
            if count % 2 == 0:
                warns.append((n, "W2", "$$ 公式块前面要空一行，否则会被当成行内公式"))
        if not is_table_line(line):
            k += 1
            continue
        start = k
        while k < len(rows) and is_table_line(rows[k][1]):
            k += 1
        block = rows[start:k]
        tables += 1
        if start > 0 and rows[start - 1][1].strip():
            errors.append((n, "E1", "表格上面要空一行（现在紧挨着：" + rows[start - 1][1].strip()[:30] + "）"))
        if k < len(rows) and rows[k][1].strip():
            errors.append((rows[k][0], "E2", "表格下面要空一行（现在紧跟着：" + rows[k][1].strip()[:30] + "）"))
        if len(block) < 2 or not all(SEP_CELL.match(c) for c in split_cells(block[1][1])):
            bad = block[1][1].strip()[:40] if len(block) > 1 else "（只有一行）"
            errors.append((block[0][0], "E3", f"表格第二行必须是 |---|---| 分隔行，现在是：{bad}"))
        ncol = len(split_cells(block[0][1]))
        for rn, rl in block[1:]:
            c = len(split_cells(rl))
            if c != ncol:
                warns.append((rn, "W1", f"这一行 {c} 列，表头 {ncol} 列；单元格里的 | 要写成 \\|"))
    return errors, warns, tables


def page_for(post: Path, site: Path) -> Path | None:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md$", post.name)
    if not m:
        return None
    y, mo, d, slug = m.groups()
    return site / y / mo / d / slug / "index.html"


def check_render(post: Path, site: Path, src_tables: int):
    page = page_for(post, site)
    if not page or not page.exists():
        return [(0, "E5", f"找不到构建结果 {page}")]
    html = page.read_text(encoding="utf-8")
    m = re.search(r'<div class="content">(.*?)<div class="post-tail-wrapper', html, re.S)
    content = m.group(1) if m else html
    errs = []
    got = len(re.findall(r"<table\b(?![^>]*rouge-table)", content))  # 代码块行号用的 rouge-table 不算
    if got != src_tables:
        errs.append((0, "E5", f"源文件有 {src_tables} 张表格，页面里渲染出 {got} 张"))
    for para in re.findall(r"<p>(.*?)</p>", content, re.S):
        if re.search(r"\|\s*[—–-]{1,3}\s*\|", para):
            errs.append((0, "E5", "页面里有塌掉的表格文本：" + " ".join(re.sub(r"<[^>]+>", "", para).split())[:50]))
    return errs


def main():
    args = sys.argv[1:]
    site = None
    if "--site" in args:
        i = args.index("--site")
        site = Path(args[i + 1])
        del args[i:i + 2]
    files = [Path(a) for a in args] or sorted(Path("_posts").glob("*.md"))
    n_err = n_warn = 0
    print("== Markdown 渲染检查（kramdown）" + ("，含构建结果核对" if site else ""))
    for f in files:
        errors, warns, tables = lint(f)
        if site:
            errors += check_render(f, site, tables)
        n_err += len(errors)
        n_warn += len(warns)
        if not errors and not warns:
            print(f"  ✓ {f.name}（{tables} 张表格）")
            continue
        print(f"  {'✗' if errors else '!'} {f.name}（{tables} 张表格）")
        for n, code, msg in sorted(errors + warns):
            print(f"      {code} 第{n}行：{msg}" if n else f"      {code} {msg}")
    if n_err:
        print(f"  ✗ {n_err} 个错误，站上会渲染坏。改法见 references/publish-post.md「排版检查」")
    elif n_warn:
        print(f"  ! {n_warn} 个警告，确认无误即可")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
