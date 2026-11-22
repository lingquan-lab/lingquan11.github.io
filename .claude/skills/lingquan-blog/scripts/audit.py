#!/usr/bin/env python3
"""零醛·技术实录 站点体检（只读）。

在博客仓库根目录运行：
    python3 .claude/skills/lingquan-blog/scripts/audit.py [--offline] [--today YYYY-MM-DD]

只读：不改文件、不推送，也不访问 GoatCounter。输出一份 Markdown 报告，
分为「需要仓主处理」「维护者可直接处理」「正常」「没能检查」四节。
远程检查依赖已登录的 gh（lingquan-lab），查不了的项归入「没能检查」。
阈值和含义见 references/audit-and-reminders.md。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

UPSTREAM = "lingquan11/lingquan11.github.io"
OWNER = "lingquan11"
CATEGORIES = ["项目实录", "深研自述"]
HEADINGS_RULE_SINCE = dt.date(2026, 11, 22)  # README 写入「用##小标题分段」的日期
CADENCE_WARN, CADENCE_STRONG = 7, 14
REDLINE_WINDOW_DAYS = 30
ABOUT_STALE_DAYS = 60
PR_STALE_DAYS = 3

OWNER_SEC, MAINT_SEC, OK_SEC, SKIP_SEC = "owner", "maint", "ok", "skip"


class Report:
    def __init__(self, ignores: set[str]):
        self.items: dict[str, list[str]] = {OWNER_SEC: [], MAINT_SEC: [], OK_SEC: [], SKIP_SEC: []}
        self.ignores = ignores
        self.ignored = 0

    def add(self, sec: str, check: str, text: str, key: str | None = None):
        if f"check:{check}" in self.ignores or (key and key in self.ignores):
            self.ignored += 1
            return
        self.items[sec].append(f"[{check}] {text}")

    def render(self, today: dt.date) -> str:
        titles = {
            OWNER_SEC: "需要仓主处理",
            MAINT_SEC: "维护者可直接处理",
            OK_SEC: "正常",
            SKIP_SEC: "没能检查",
        }
        out = [f"# 站点体检 {today.isoformat()}", ""]
        for sec in (OWNER_SEC, MAINT_SEC, OK_SEC, SKIP_SEC):
            out.append(f"## {titles[sec]}（{len(self.items[sec])}）")
            out += [f"- {t}" for t in self.items[sec]] or ["- （无）"]
            out.append("")
        if self.ignored:
            out.append(f"_按 audit-ignore.txt 跳过 {self.ignored} 项。_")
        return "\n".join(out)


# ---------- 工具 ----------

def run(cmd: list[str], cwd: Path, timeout: int = 60) -> str:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=True).stdout


def gh_json(args: list[str], cwd: Path):
    return json.loads(run(["gh", *args], cwd) or "null")


def git_date(path: str, cwd: Path) -> dt.date | None:
    try:
        s = run(["git", "log", "-1", "--format=%cs", "--", path], cwd).strip()
        return dt.date.fromisoformat(s) if s else None
    except Exception:
        return None


def parse_front_matter(text: str) -> tuple[dict, str]:
    """极简 front matter 解析：只支持本仓库用到的 `key: value` 和 `key: [a, b]`。"""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text
    fm: dict = {}
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
        else:
            fm[key] = val.strip("'\"")
    return fm, "\n".join(lines[end + 1:])


def load_ignores(skill_dir: Path) -> set[str]:
    f = skill_dir / "audit-ignore.txt"
    if not f.exists():
        return set()
    out = set()
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def load_vocab(root: Path) -> list[str] | None:
    readme = root / "README.md"
    if not readme.exists():
        return None
    text = readme.read_text(encoding="utf-8")
    m = re.search(r"^## 标签词表\s*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        return None
    block = m.group(1)
    # 只取「已批准标签」到下一个空行段落之间的列表项
    m2 = re.search(r"已批准标签[：:]\s*\n((?:\s*-\s+.+\n?)+)", block)
    items = m2.group(1) if m2 else block
    return [re.sub(r"^\s*-\s+", "", l).strip() for l in items.splitlines() if re.match(r"^\s*-\s+", l)]


# ---------- 本地检查 ----------

def check_posts(root: Path, today: dt.date, rep: Report):
    posts = []
    for p in sorted((root / "_posts").glob("*.md")):
        fm, body = parse_front_matter(p.read_text(encoding="utf-8"))
        m = re.match(r"(\d{4}-\d{2}-\d{2})-", p.name)
        date = dt.date.fromisoformat((fm.get("date") or m.group(1))[:10]) if (fm.get("date") or m) else None
        posts.append({"file": p.name, "fm": fm, "body": body, "date": date})

    if not posts:
        rep.add(OWNER_SEC, "cadence", "站上还没有任何文章。")
        return posts

    # 更新节奏
    latest = max(posts, key=lambda x: x["date"] or dt.date.min)
    days = (today - latest["date"]).days if latest["date"] else None
    title = latest["fm"].get("title", latest["file"])
    if days is None:
        rep.add(SKIP_SEC, "cadence", "无法确定最新文章日期。")
    elif days > CADENCE_STRONG:
        rep.add(OWNER_SEC, "cadence", f"距上一篇文章《{title}》已 {days} 天（README 约定一周一篇左右），断更明显。")
    elif days > CADENCE_WARN:
        rep.add(OWNER_SEC, "cadence", f"距上一篇文章《{title}》已 {days} 天，该写下一篇了。")
    else:
        rep.add(OK_SEC, "cadence", f"最新文章《{title}》，{days} 天前。")

    # 栏目覆盖与合法性
    counts = {c: 0 for c in CATEGORIES}
    for x in posts:
        cats = x["fm"].get("categories")
        cats = cats if isinstance(cats, list) else ([cats] if cats else [])
        for c in cats:
            if c in counts:
                counts[c] += 1
            else:
                rep.add(OWNER_SEC, "category-invalid", f"{x['file']} 的分类「{c}」不在约定的两栏内（{'/'.join(CATEGORIES)}）。")
        if not cats:
            rep.add(OWNER_SEC, "category-invalid", f"{x['file']} 没有分类。")
    for c, n in counts.items():
        if n == 0:
            rep.add(OWNER_SEC, "category-empty", f"「{c}」栏目还没有文章，读者点进去是空的。", key=f"category:{c}")
    rep.add(OK_SEC, "category-count", "、".join(f"{c} {n} 篇" for c, n in counts.items()))

    # 标签
    vocab = load_vocab(root)
    if vocab is None:
        rep.add(SKIP_SEC, "tags", "README 里没找到「标签词表」，无法核对标签。")
    else:
        bad = 0
        for x in posts:
            tags = x["fm"].get("tags")
            tags = tags if isinstance(tags, list) else ([tags] if tags else [])
            if not tags:
                rep.add(OWNER_SEC, "tags-missing", f"{x['file']} 没有标签。请从词表选 2～3 个。", key=f"tags:{x['file']}")
                bad += 1
            unknown = [t for t in tags if t not in vocab]
            if unknown:
                rep.add(OWNER_SEC, "tags-unknown", f"{x['file']} 用了词表外的标签 {unknown}：换成词表内的，或者批准后补进词表。", key=f"tags:{x['file']}")
                bad += 1
        if not bad:
            rep.add(OK_SEC, "tags", f"{len(posts)} 篇文章的标签都在词表内（词表 {len(vocab)} 个）。")

    # 小标题（仅约定生效之后的文章）
    for x in posts:
        if x["date"] and x["date"] >= HEADINGS_RULE_SINCE and not re.search(r"^## ", x["body"], re.M):
            rep.add(OWNER_SEC, "headings", f"{x['file']} 没有用 ## 小标题分段，文章页不会生成目录。", key=f"headings:{x['file']}")

    # 内容红线粗筛（近 N 天）
    for x in posts:
        if not x["date"] or (today - x["date"]).days > REDLINE_WINDOW_DAYS:
            continue
        b = x["body"]
        has = {
            "代码": bool(re.search(r"^```", b, re.M)),
            "公式": "$$" in b or bool(re.search(r"(?<!\$)\$[^$\n]+\$(?!\$)", b)),
            "表格/数据": bool(re.search(r"^\|.+\|\s*$", b, re.M)),
        }
        if not any(has.values()):
            rep.add(OWNER_SEC, "redline", f"{x['file']}：没检测到代码块、公式或表格，可能不满足内容红线（代码/公式/数据/原理至少两样）。脚本只能粗筛，请人工判断。", key=f"redline:{x['file']}")

    # 置顶
    pinned = [x["file"] for x in posts if str(x["fm"].get("pin", "")).lower() == "true"]
    if len(pinned) > 1:
        rep.add(OWNER_SEC, "pin", f"置顶了 {len(pinned)} 篇：{pinned}，首页第一屏会被占满，建议只留一篇代表作。")
    elif not pinned:
        rep.add(OWNER_SEC, "pin", "没有置顶文章。建议置顶一篇代表作，导师进首页第一眼就能看到。")
    else:
        rep.add(OK_SEC, "pin", f"置顶：{pinned[0]}")
    return posts


def parse_projects(root: Path):
    f = root / "_tabs" / "projects.md"
    if not f.exists():
        return None, []
    text = f.read_text(encoding="utf-8")
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    out = []
    for s in sections:
        title, _, rest = s.partition("\n")
        out.append({
            "title": title.strip(),
            "status": (re.search(r"^\*\*(.+?)\*\*", rest, re.M) or [None, ""])[1],
            "text": rest,
            "repos": re.findall(r"github\.com/lingquan11/([\w.-]+)", rest),
        })
    return text, out


def check_projects_local(root: Path, today: dt.date, rep: Report):
    text, projects = parse_projects(root)
    if text is None:
        rep.add(SKIP_SEC, "projects", "没有 _tabs/projects.md。")
        return []
    for p in projects:
        if "进行中" not in p["status"]:
            continue
        m = re.search(r"计划(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日", p["text"])
        if not m:
            continue
        year = int(m.group(1)) if m.group(1) else today.year
        try:
            due = dt.date(year, int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if due < today:
            rep.add(OWNER_SEC, "project-overdue", f"项目页「{p['title']}」写着计划 {due.isoformat()} 前收尾，现在已过期，状态仍是「进行中」。是完成了、延期了，还是暂停了？")
    about = git_date("_tabs/about.md", root)
    if about:
        age = (today - about).days
        if age > ABOUT_STALE_DAYS:
            rep.add(OWNER_SEC, "about-stale", f"关于页 {age} 天没更新，「现在在做的」可能已经过时。")
        else:
            rep.add(OK_SEC, "about-stale", f"关于页 {age} 天前更新。")
    return projects


# ---------- 远程检查 ----------

def check_remote(root: Path, today: dt.date, projects: list, rep: Report):
    try:
        login = run(["gh", "api", "user", "--jq", ".login"], root).strip()
    except Exception:
        rep.add(SKIP_SEC, "remote", "gh 不可用或未登录，跳过所有远程检查。")
        return
    if login == OWNER:
        rep.add(OWNER_SEC, "account", "当前 gh 登录的是仓主真实账号 lingquan11。按约定维护者不应使用这个账号，请换回 lingquan-lab。")

    # 仓库：未上站 / 项目页过时
    try:
        repos = gh_json(["api", f"users/{OWNER}/repos?per_page=100&type=owner"], root)
        linked = {r for p in projects for r in p["repos"]}
        page_date = git_date("_tabs/projects.md", root)
        for r in repos:
            name = r["name"]
            if r.get("fork") or r.get("archived") or r.get("private") or name == f"{OWNER}.github.io":
                continue
            if name not in linked:
                created = r.get("created_at", "")[:10]
                rep.add(OWNER_SEC, "repo-not-listed", f"公开仓库 {name}（{created} 创建）还没上项目页。要放上站吗？不放的话告诉维护者，记进忽略清单。", key=f"repo:{name}")
            elif page_date and r.get("pushed_at"):
                pushed = dt.date.fromisoformat(r["pushed_at"][:10])
                if pushed > page_date:
                    rep.add(MAINT_SEC, "project-outdated", f"{name} 在 {pushed} 有推送，晚于项目页最后修改（{page_date}），按 add-project.md 第 3 节核对是否需要更新。", key=f"repo:{name}")
        rep.add(OK_SEC, "repos", f"检查了 {len(repos)} 个仓库。")
    except Exception as e:
        rep.add(SKIP_SEC, "repos", f"读取仓主仓库列表失败：{e}")

    # 部署
    try:
        runs = gh_json(["run", "list", "--repo", UPSTREAM, "--branch", "main", "--workflow", "Build and Deploy", "--limit", "1",
                        "--json", "conclusion,status,createdAt,url"], root)
        if runs:
            r0 = runs[0]
            if r0["status"] == "completed" and r0["conclusion"] != "success":
                rep.add(MAINT_SEC, "deploy", f"main 最近一次部署失败（{r0['createdAt'][:10]}）：{r0['url']}。网站停在上一个版本，立即排查。")
            else:
                rep.add(OK_SEC, "deploy", f"最近一次部署：{r0['status']}/{r0['conclusion'] or '-'}（{r0['createdAt'][:10]}）")
    except Exception as e:
        rep.add(SKIP_SEC, "deploy", f"读取部署记录失败：{e}")

    # Pages 设置
    try:
        bt = run(["gh", "api", f"repos/{UPSTREAM}/pages", "--jq", ".build_type"], root).strip()
        if bt != "workflow":
            rep.add(OWNER_SEC, "pages", f"Pages 部署方式是「{bt}」，应为 GitHub Actions（workflow）。请到 Settings → Pages 改回来，否则两套部署会抢着发布。")
        else:
            rep.add(OK_SEC, "pages", "Pages 部署方式：GitHub Actions。")
    except Exception as e:
        rep.add(SKIP_SEC, "pages", f"读取 Pages 设置失败：{e}")

    # 待审 PR
    try:
        prs = gh_json(["pr", "list", "--repo", UPSTREAM, "--state", "open", "--author", login,
                       "--json", "number,title,createdAt,url"], root)
        for pr in prs:
            age = (today - dt.date.fromisoformat(pr["createdAt"][:10])).days
            if age > PR_STALE_DAYS:
                rep.add(OWNER_SEC, "pr-waiting", f"PR #{pr['number']}「{pr['title']}」已等待审阅 {age} 天：{pr['url']}")
        if not prs:
            rep.add(OK_SEC, "pr-waiting", "没有待审阅的 PR。")
    except Exception as e:
        rep.add(SKIP_SEC, "pr-waiting", f"读取 PR 列表失败：{e}")

    # 评论：最新一条不是仓主的
    try:
        q = """query($o:String!,$n:String!){repository(owner:$o,name:$n){discussions(first:50,orderBy:{field:UPDATED_AT,direction:DESC}){nodes{title url comments(last:1){totalCount nodes{author{login} createdAt url replies(last:1){nodes{author{login} createdAt}}}}}}}}"""
        data = gh_json(["api", "graphql", "-f", f"query={q}", "-F", f"o={OWNER}", "-F", f"n={OWNER}.github.io"], root)
        pending = 0
        for d in data["data"]["repository"]["discussions"]["nodes"]:
            if not d["comments"]["totalCount"]:
                continue
            c = d["comments"]["nodes"][0]
            last = (c["replies"]["nodes"] or [c])[-1]
            who = (last.get("author") or {}).get("login", "?")
            if who != OWNER:
                pending += 1
                rep.add(OWNER_SEC, "comments", f"「{d['title']}」的评论区最新一条来自 {who}（{last['createdAt'][:10]}），还没回复：{c['url']}")
        if not pending:
            rep.add(OK_SEC, "comments", "没有待回复的评论。")
    except Exception as e:
        rep.add(SKIP_SEC, "comments", f"读取评论失败：{e}")

    # 静态资源包 vs starter
    try:
        ours = run(["git", "ls-tree", "HEAD", "assets/lib"], root).split()[2]
        starter = gh_json(["api", "repos/cotes2020/chirpy-starter/contents/assets/lib"], root)["sha"]
        if ours != starter:
            rep.add(MAINT_SEC, "assets-lib", f"assets/lib 子模块在 {ours[:7]}，chirpy-starter 已指向 {starter[:7]}。按 maintenance.md 第 2 节第 4 步同步。")
        else:
            rep.add(OK_SEC, "assets-lib", f"assets/lib 与 chirpy-starter 一致（{ours[:7]}）。")
    except Exception as e:
        rep.add(SKIP_SEC, "assets-lib", f"无法比较静态资源包：{e}")


def check_theme_version(root: Path, rep: Report):
    local = None
    lock = root / "Gemfile.lock"
    if lock.exists():
        m = re.search(r"^\s+jekyll-theme-chirpy \(([\d.]+)\)", lock.read_text(encoding="utf-8"), re.M)
        local = m.group(1) if m else None
    try:
        with urllib.request.urlopen("https://rubygems.org/api/v1/versions/jekyll-theme-chirpy/latest.json", timeout=20) as r:
            latest = json.load(r)["version"]
    except Exception as e:
        rep.add(SKIP_SEC, "theme", f"无法查询 Chirpy 最新版本：{e}")
        return
    if local is None:
        rep.add(SKIP_SEC, "theme", f"本地没有 Gemfile.lock（先 bundle install），Chirpy 最新版是 {latest}。")
    elif tuple(map(int, latest.split("."))) > tuple(map(int, local.split("."))):
        rep.add(MAINT_SEC, "theme", f"Chirpy 有新版本 {latest}（本地 {local}）。线上部署已经会用到 7.x 新版，按 maintenance.md 第 2 节尽快核对覆盖文件。")
    else:
        rep.add(OK_SEC, "theme", f"Chirpy {local} 已是最新。")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="只做本地检查")
    ap.add_argument("--today", help="以指定日期作为今天（测试用），格式 YYYY-MM-DD")
    args = ap.parse_args()

    try:
        root = Path(run(["git", "rev-parse", "--show-toplevel"], Path.cwd()).strip())
    except Exception:
        sys.exit("请在博客仓库内运行。")
    if not (root / "_posts").is_dir():
        sys.exit(f"{root} 看起来不是博客仓库（没有 _posts/）。")

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    skill_dir = Path(__file__).resolve().parent.parent
    rep = Report(load_ignores(skill_dir))

    check_posts(root, today, rep)
    projects = check_projects_local(root, today, rep)
    if args.offline:
        rep.add(SKIP_SEC, "remote", "--offline：跳过仓库、部署、Pages、PR、评论、主题版本检查。")
    else:
        check_remote(root, today, projects, rep)
        check_theme_version(root, rep)
    print(rep.render(today))


if __name__ == "__main__":
    main()
