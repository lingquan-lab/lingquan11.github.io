#!/usr/bin/env python3
"""把站上文章转成发知乎、掘金用的 Markdown。只读源文件，输出到 _export/（不提交）。

    python3 .claude/skills/lingquan-blog/scripts/export_post.py _posts/<文章>.md --platform juejin|zhihu [--tables keep|image]

输出 _export/<文章>/<platform>.md，并打印标题、标签、封面图地址，照着填进平台的发文页面。

做了哪些转换（只改导出副本，站上的文章不动；文字内容一字不改）：
  - 去掉 front matter；标题、标签、封面单独打印
  - 站内路径（/assets/...、/posts/...）改成 https://lingquan11.github.io/... 完整地址，平台才能显示图片、点得开链接
  - 去掉 kramdown 专用写法：{: .dark } 那张图删掉（平台是白底），{: .light } 等属性标记删掉
  - 表格、公式块、列表前后补空行；表格分隔行统一成 |---|
  - 独占一段的 $$公式$$ 改成三行写法（$$ / 公式 / $$），段落里的 $$公式$$ 改成 $公式$
  - 文末加原文链接
  - --tables image：每张表格画成白底 PNG（table-1.png …）放在同一目录，正文里换成图片。
    平台的表格排版不理想（列太多、被压窄、导入后错位）时用；图片要在平台编辑器里手动上传替换。
    表格下方会保留一行「表格原文见博客」的链接，方便读者复制数据。

先跑 lint_markdown.py：源文件有 E 级错误时，本脚本拒绝导出（导出也会是坏的）。
"""
import argparse
import re
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lint_markdown import is_table_line, lint, split_cells  # noqa: E402
from make_chart import text_width  # noqa: E402

SITE = "https://lingquan11.github.io"
FONT = "'Noto Sans CJK SC','Noto Serif CJK SC','PingFang SC','Microsoft YaHei',sans-serif"


def parse_front(text: str):
    if not text.startswith("---"):
        return {}, text
    end = text.index("\n---", 3)
    head, body = text[3:end], text[end + 4:].lstrip("\n")
    meta = {}
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', head, re.M)
    meta["title"] = m.group(1) if m else ""
    m = re.search(r"^tags:\s*\[(.*?)\]", head, re.M)
    meta["tags"] = [t.strip() for t in m.group(1).split(",")] if m else []
    m = re.search(r"^image:\s*\n\s+path:\s*(\S+)", head, re.M) or re.search(r"^image:\s*(\S+)", head, re.M)
    meta["image"] = m.group(1) if m else ""
    return meta, body


def permalink(post: Path) -> str:
    y, mo, d, slug = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.md$", post.name).groups()
    return f"{SITE}/{y}/{mo}/{d}/{slug}/"


def absolutize(line: str) -> str:
    return re.sub(r"\]\((/[^)\s]*)", lambda m: "](" + SITE + m.group(1), line)


def strip_md(s: str) -> str:
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"[*_`]{1,3}", "", s)
    return s.replace("\\|", "|").strip()


def table_png(rows: list[list[str]], path: Path):
    """白底表格图：表头加粗、灰底，细线分隔。"""
    size, pad, lh = 15, 14, 34
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    widths = [max(text_width(r[c], size) for r in rows) + pad * 2 for c in range(ncol)]
    W, H = int(sum(widths)) + 2, lh * len(rows) + 2
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="{FONT}" font-size="{size}">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>', f'<rect x="1" y="1" width="{W - 2}" height="{lh}" fill="#f2f2f2"/>']
    for i, r in enumerate(rows):
        y, x = 1 + lh * i, 1
        for c, cell in enumerate(r):
            weight = ' font-weight="700"' if i == 0 else ""
            out.append(f'<text x="{x + pad:.1f}" y="{y + lh / 2 + size * 0.36:.1f}" fill="#111111"{weight}>{escape(cell)}</text>')
            x += widths[c]
        out.append(f'<line x1="1" x2="{W - 1}" y1="{y + lh}" y2="{y + lh}" stroke="{"#9a9a9a" if i == 0 else "#dddddd"}"/>')
    out.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" fill="none" stroke="#cccccc"/></svg>')
    svg = path.with_suffix(".svg")
    svg.write_text("\n".join(out), encoding="utf-8")
    subprocess.run(["rsvg-convert", "-z", "2", str(svg), "-o", str(path)], check=True)
    svg.unlink()


def convert(body: str, post_url: str, outdir: Path, tables: str) -> str:
    lines, out, i, in_fence, nt = body.split("\n"), [], 0, False, 0

    def blank():
        if out and out[-1].strip():
            out.append("")

    while i < len(lines):
        line = lines[i].rstrip("\r")
        if re.match(r"^\s{0,3}(```|~~~)", line):
            if not in_fence:
                blank()
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue
        if re.search(r"\{:\s*\.dark\s*\}\s*$", line):  # 深色版图片：平台白底，删掉
            i += 1
            continue
        line = re.sub(r"\{:[^}]*\}\s*$", "", line).rstrip()  # 其他 kramdown 属性标记
        if re.fullmatch(r"\s*\{:[^}]*\}\s*", lines[i]):
            i += 1
            continue
        line = absolutize(line)
        if is_table_line(line):
            block = []
            while i < len(lines) and is_table_line(lines[i]):
                block.append(absolutize(lines[i].rstrip()))
                i += 1
            nt += 1
            blank()
            if tables == "image":
                rows = [[strip_md(c) for c in split_cells(r)] for k, r in enumerate(block) if k != 1]
                png = outdir / f"table-{nt}.png"
                table_png(rows, png)
                out.append(f"![表格{nt}]({png.name})")
                out.append("")
                out.append(f"（表格{nt}的文字版见[博客原文]({post_url})）")
            else:
                ncol = len(split_cells(block[0]))
                block[1] = "|" + "---|" * ncol
                out.extend(block)
            out.append("")
            continue
        m = re.fullmatch(r"\s*\$\$(.+?)\$\$\s*", line)
        alone = not (out and out[-1].strip()) and not (i + 1 < len(lines) and lines[i + 1].strip())
        if m and alone:  # 独占一段 = kramdown 里的公式块
            out +=["$$", m.group(1).strip(), "$$", ""]
            i += 1
            continue
        line = re.sub(r"(?<!\$)\$\$(?!\$)(.+?)(?<!\$)\$\$(?!\$)", r"$\1$", line)  # 段落里的行内公式
        if re.match(r"^\s{0,3}([-*+]|\d+\.)\s", line) and out and out[-1].strip() \
                and not re.match(r"^\s*([-*+]|\d+\.)\s", out[-1]) and not out[-1].startswith("    "):
            blank()
        out.append(line)
        i += 1
    while out and not out[-1].strip():
        out.pop()
    out += ["", "---", "", f"> 本文首发于我的个人博客「零醛·技术实录」，原文与后续更新：{post_url}", ""]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("post")
    ap.add_argument("--platform", required=True, choices=["juejin", "zhihu"])
    ap.add_argument("--tables", default="keep", choices=["keep", "image"])
    a = ap.parse_args()
    post = Path(a.post)
    errors, _, _ = lint(post)
    if errors:
        sys.exit(f"源文件有 {len(errors)} 个排版错误，先运行 lint_markdown.py 看清楚并按流程修好再导出")
    if a.tables == "image" and not shutil.which("rsvg-convert"):
        sys.exit("--tables image 需要 rsvg-convert（Debian/Ubuntu：sudo apt-get install librsvg2-bin）")
    meta, body = parse_front(post.read_text(encoding="utf-8"))
    outdir = Path("_export") / post.stem
    outdir.mkdir(parents=True, exist_ok=True)
    url = permalink(post)
    md = convert(body, url, outdir, a.tables)
    dst = outdir / f"{a.platform}.md"
    dst.write_text(md, encoding="utf-8")
    print(f"已导出：{dst}")
    print(f"标题：{meta['title']}")
    print(f"标签：{'、'.join(meta['tags'])}（平台标签体系不同，按平台已有标签挑相近的）")
    if meta["image"]:
        print(f"封面：{SITE}{meta['image']}（平台要 JPG/PNG 的话：convert cover.webp cover.png）")
    if a.tables == "image":
        print(f"表格图：{outdir}/table-*.png，导入后在编辑器里逐张上传替换")
    print(f"原文链接：{url}")


if __name__ == "__main__":
    main()
