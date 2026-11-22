#!/usr/bin/env bash
# 交 PR 前的自动检查。在博客仓库内运行：
#   .claude/skills/lingquan-blog/scripts/verify.sh [基准引用，默认 origin/main]
# 1) 生产构建（不能有 warning/error） 2) htmlproofer（与线上部署参数相同）
# 3) 正文守卫 + 标签词表（check_content.py） 4) 列出构建出的标签页
# 任何一步失败，退出码非 0。浏览器检查不在这里，见 references/pr-and-checks.md 3.2。
set -uo pipefail

BASE="${1:-origin/main}"
ROOT="$(git rev-parse --show-toplevel)" || { echo "请在博客仓库内运行"; exit 2; }
cd "$ROOT"
HERE="$ROOT/.claude/skills/lingquan-blog/scripts"
export BUNDLE_PATH="${BUNDLE_PATH:-vendor/bundle}"
fail=0

echo "== 准备"
git rev-parse --verify -q "$BASE" >/dev/null || { echo "  ✗ 找不到基准 $BASE，先 git fetch origin"; exit 2; }
if [ -z "$(ls -A assets/lib 2>/dev/null)" ]; then
  echo "  初始化 assets/lib 子模块"; git submodule update --init -q || { echo "  ✗ 子模块初始化失败"; exit 2; }
fi
bundle check >/dev/null 2>&1 || bundle install --quiet || { echo "  ✗ bundle install 失败"; exit 2; }

echo "== 生产构建"
LOG="$(mktemp)"
rm -rf _site
if JEKYLL_ENV=production bundle exec jekyll build >"$LOG" 2>&1; then
  if grep -iE 'warn|error' "$LOG"; then echo "  ✗ 构建有 warning/error（见上）"; fail=1; else echo "  ✓ 构建通过，无 warning"; fi
else
  cat "$LOG"; echo "  ✗ 构建失败"; fail=1
fi

if [ -d _site ]; then
  echo "== htmlproofer"
  if bundle exec htmlproofer _site --disable-external \
      --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/" >"$LOG" 2>&1; then
    echo "  ✓ 通过"
  else
    cat "$LOG"; echo "  ✗ 未通过"; fail=1
  fi
fi

echo
python3 "$HERE/check_content.py" "$BASE" || fail=1

if [ -d _site/tags ]; then
  echo "== 构建出的标签页"
  find _site/tags -mindepth 1 -maxdepth 1 -type d -printf '  %f\n' | sort
fi

echo
if [ "$fail" = 0 ]; then echo "全部自动检查通过。别忘了浏览器检查（pr-and-checks.md 3.2）。"; else echo "有检查未通过，先修好再交 PR。"; fi
rm -f "$LOG"
exit "$fail"
