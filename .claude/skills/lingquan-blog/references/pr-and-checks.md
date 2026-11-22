# 交付：分支、PR 与自查

仓主审阅 PR 时，需要一眼看清改了什么、怎么验证过、哪些东西保证没动。下面的流程就是为了让他审得快、合得放心。

## 1. 开分支

```bash
git fetch origin
git checkout -b <类型>/<简短说明> origin/main     # 永远从最新的 main 切
```

| 类型前缀 | 用于 |
|---|---|
| `content/` | 文章上站、front matter、项目页、标签 |
| `feat/` | 新功能、样式改动 |
| `fix/` | 修 bug |
| `upgrade/` | 主题或依赖升级 |
| `chore/` | 维护性改动（文档、skill、日志） |

一个 PR 只做一件事。仓主可能只想合其中一部分，混在一起他就只能整个退回。

**依赖还没合并的 PR**：PR 的目标只能是原仓的 `main`，没法在 fork 的分支之间叠加。如果新工作依赖一个还没合并的 PR，就基于那个分支开发，并在 PR 描述第一行写「请先合并 #N」。前一个合并之后，这个 PR 里就只剩它自己的改动了。

## 2. 提交

- 提交身份用 `lingquan-lab`：`git config user.name lingquan-lab`，邮箱用它的 GitHub noreply 地址（`gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"'`）。
- 提交说明用中文：第一行概括，下面按条列出改动。按你所在环境的署名规则追加署名行。
- 推送：`git push -u fork <分支>`。`fork` 远程指向 `https://github.com/lingquan-lab/lingquan11.github.io.git`，没有就先 `git remote add`。

## 3. 自查（交 PR 之前）

### 3.1 自动检查
```bash
.claude/skills/lingquan-blog/scripts/verify.sh            # 默认与 origin/main 对比
```
它会做这些检查，任何一项失败都不要交 PR：
- 生产构建（`JEKYLL_ENV=production`），不能有 warning 或 error
- htmlproofer（参数与线上部署时相同）
- **正文守卫**：每篇文章 front matter 之后的内容必须与 `origin/main` 完全一致。新增的文章不受影响
- 所有文章的标签都在 README 词表里
- 列出构建出的标签页和每篇文章的标签，方便核对

确实需要改正文时（仓主明确授权），守卫会失败。这时在 PR 描述里逐处列出改动，并写明是谁、什么时候授权的。

### 3.2 浏览器检查（有浏览器时必须做）

```bash
python3 -I -m http.server 4000 -b 127.0.0.1 -d _site     # 在后台运行
```

在浏览器里打开 `http://127.0.0.1:4000/`，执行下面的脚本。它会以 375px 宽度逐页打开站点，深色、浅色各一遍。按需要修改 `pages` 列表，至少包含首页、项目页、关于页、标签页、本次改动涉及的每个页面：

```js
const pages=['/','/projects/','/about/','/tags/','/categories/','/archives/' /* + 本次涉及的文章 */];
const res={};
for (const mode of ['dark','light']) {
  localStorage.setItem('theme', mode); const out=[];
  for (const p of pages) {
    const f=document.createElement('iframe');
    f.style.cssText='position:fixed;left:0;top:0;width:375px;height:812px;border:0;visibility:hidden';
    document.body.appendChild(f);
    await new Promise(r=>{f.onload=r; f.src=p}); await new Promise(r=>setTimeout(r,500));
    const d=f.contentDocument;
    out.push(decodeURI(p)
      + (d.documentElement.scrollWidth>d.documentElement.clientWidth ? ' 溢出' : ' ok')
      + (d.body.innerText.includes('�') ? ' 乱码' : '')
      + (d.title.startsWith(' |') ? ' 标题为空' : ''));
    f.remove();
  }
  res[mode]=out;
}
localStorage.setItem('theme','dark'); res
```

页面多时，分成深色、浅色两次执行，避免超时。然后再看几张截图，重点看本次改动的地方。不能只看脚本数字：截图曾发现过浅色模式下卡片没有边框这类问题。

GoatCounter 的脚本会自动跳过 `127.0.0.1`，本地预览不会给仓主的统计记数（控制台会显示 `not counting because of: localhost`）。

**没有浏览器的环境**：在 PR 的检查清单里明确写"未做浏览器检查"，不要假装做过。

### 3.3 未改动文件
```bash
for p in _posts/*.md _tabs/about.md README.md; do
  [ "$(git rev-parse origin/main:$p 2>/dev/null)" = "$(git rev-parse HEAD:$p)" ] && echo "未改动 $p"
done
```

## 4. PR 描述模板

```markdown
<一两句话说明这个 PR 做什么。文章正文是否改动。>

## 改动清单
| 文件 | 类型 | 说明 |
|---|---|---|
| ... | 新增/修改 | 改了哪几行、为什么 |

## Build 检查清单
- [x] 生产构建 0 warning；htmlproofer 通过
- [x] 正文守卫通过（N 篇文章正文与 main 一致）
- [x] 375px 宽度，深色/浅色各 N 页：无溢出、无乱码、标题正确
- [x] <本次改动特有的检查，例如"首页第一张卡片是置顶文章">
- [ ] <没做到或没法验证的，照实写>

## 未改动文件清单（与 main 逐字节相同）
- ...
```

标题用中文，概括这件事。描述末尾按你所在环境的署名规则追加署名。

PR 标题、描述、评论和提交说明都是公开的。写之前检查一遍：没有仓主的私人信息，也没有暴露"这是私下得知的"之类的说法。

## 5. 交付之后

- 把 PR 链接告诉仓主，然后**停下来等他审阅**。不要合并，`lingquan-lab` 也没有权限合并。
- 仓主提了修改意见，就在同一个分支上修改后推送，并在 PR 里回复改了什么。
- 仓主合并后：
  1. `gh run watch <id> --repo lingquan11/lingquan11.github.io` 等部署完成；
  2. 抓相关页面的 HTML 核对（遇到旧版本就加查询参数绕过 CDN 缓存，不执行页面脚本）；
  3. 在 `log.md` 记一条。
