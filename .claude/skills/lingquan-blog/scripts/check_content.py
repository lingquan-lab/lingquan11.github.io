#!/usr/bin/env python3
"""正文守卫 + 标签词表检查。由 verify.sh 调用，也可单独运行：

    python3 .claude/skills/lingquan-blog/scripts/check_content.py [基准引用，默认 origin/main]

1. 正文守卫：基准里已存在的每篇文章，front matter 之后的内容必须与基准逐字节一致。
2. 标签：所有文章的标签都在 README「标签词表」里。
任何一项不通过时退出码为 1。
"""
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import load_vocab, parse_front_matter  # noqa: E402


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def git_raw(*args, cwd) -> str:
    """按原始字节读取后解码，不做换行符转换，这样 CRLF/LF 的变化也能被发现。"""
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True).stdout
    return out.decode("utf-8")


def read_raw(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:  # newline="" 关闭换行符转换
        return f.read()


def body_of(text: str) -> str:
    return parse_front_matter(text)[1]


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    root = Path(git("rev-parse", "--show-toplevel", cwd=Path.cwd()).strip())
    ok = True

    base_posts = [l for l in git("ls-tree", "--name-only", f"{base}:_posts", cwd=root).splitlines() if l.endswith(".md")]
    print(f"== 正文守卫（对比 {base}）")
    for name in base_posts:
        cur = root / "_posts" / name
        if not cur.exists():
            print(f"  ✗ {name}：在基准里存在，现在被删除或改名了（文章网址和评论都会断）")
            ok = False
            continue
        old = body_of(git_raw("show", f"{base}:_posts/{name}", cwd=root))
        new = body_of(read_raw(cur))
        if old == new:
            print(f"  ✓ {name}  {hashlib.sha256(new.encode()).hexdigest()[:12]}")
        else:
            print(f"  ✗ {name}：正文与基准不同。正文不允许改动，除非仓主明确授权（需在 PR 里逐处列出）")
            ok = False
    new_posts = sorted(p.name for p in (root / "_posts").glob("*.md") if p.name not in base_posts)
    for name in new_posts:
        body = body_of(read_raw(root / "_posts" / name))
        print(f"  + {name}（新文章）正文 SHA-256 {hashlib.sha256(body.encode()).hexdigest()}")

    print("== 标签词表")
    vocab = load_vocab(root)
    if vocab is None:
        print("  ! README 里没找到「标签词表」，跳过")
    else:
        for p in sorted((root / "_posts").glob("*.md")):
            tags = parse_front_matter(p.read_text(encoding="utf-8"))[0].get("tags") or []
            tags = tags if isinstance(tags, list) else [tags]
            unknown = [t for t in tags if t not in vocab]
            if unknown:
                print(f"  ✗ {p.name}：词表外标签 {unknown}")
                ok = False
            else:
                print(f"  ✓ {p.name}：{tags or '（无标签）'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
