# 长期维护

muse 长期接管网站。这一份是按周期排好的任务清单，加上主题升级和排障的做法。Claude 接手单次任务时，也按这里的流程做。

## 目录

1. 按周期的任务清单
2. 主题升级流程
3. 排障速查
4. 待仓主决定的事项
5. 可以主动提议的改进

---

## 1. 按周期的任务清单

### 每次仓主推送新文章后
- 按 `publish-post.md` A 部分做上站复查，并完成配套更新（项目页链接等）。

### 每周
- 运行 `scripts/audit.py`，按 `audit-and-reminders.md` 的模板给仓主发周报。
- 按 `add-project.md` 第 3 节，处理项目页可能过时的条目。
- **评论动态**：把新评论（谁、在哪篇、问了什么）放进周报，附上链接。**不要用 `lingquan-lab` 回复评论**：读者会以为是另一个人在代仓主说话。回复由仓主本人来写。
- 查看 `lingquan-lab` 提的 PR 有没有仓主的审阅意见，有就按意见修改。

### 每月（建议每月第一周）
- **主题版本检查**：Chirpy 出了新版本，就按第 2 节做升级。即使没出新版本，也看一眼 [Chirpy 的 releases](https://github.com/cotes2020/jekyll-theme-chirpy/releases)，了解有没有已知问题。
- **外链检查**：
  ```bash
  bundle exec htmlproofer _site --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/" --no-enforce-https
  ```
  （不加 `--disable-external`，会检查外部链接，速度慢。）失效的链接在项目页或配置里，就修掉；在文章正文里，只报告给仓主，由他决定怎么改。
- **Actions 版本**：对比 [chirpy-starter 的部署流程](https://github.com/cotes2020/chirpy-starter/blob/main/.github/workflows/pages-deploy.yml)和本仓库的 `.github/workflows/pages-deploy.yml`，上游升级了 `actions/*` 的版本就跟进（注意保留本仓库的 `submodules: true`）。
- **线上抽查**：抓首页、项目页和最新一篇文章的 HTML，确认标题、样式表、评论脚本都在（只抓 HTML，不执行脚本）。
- **Pages 设置**：`gh api repos/lingquan11/lingquan11.github.io/pages --jq .build_type` 应该是 `workflow`。

### 每季度
- 通读一遍 README 的写作约定和最近三个月的文章，看约定是否需要补充（例如某类内容反复出现，可能需要一个新标签）。整理成建议给仓主，不要自己改 README 的规矩。
- 回顾 `log.md`，把已经完成的待办划掉，把仓主的长期决定汇总到日志顶部的「长期决定」一节。
- 在手机和桌面上，用深色、浅色两种模式完整浏览一遍网站，凭肉眼找出不协调的地方。

---

## 2. 主题升级流程

**为什么要主动做**：`Gemfile` 写的是 `jekyll-theme-chirpy ~> 7.6`，并且按 Chirpy 官方做法，`Gemfile.lock` 没有提交到仓库。所以线上每次部署都会自动用最新的 7.x 版本。新版本一发布，线上就已经在用了。如果它改了我们覆盖过的文件，样式可能错位，构建也可能失败。所以要尽快核对，而不是等出了问题再查。

**步骤**（在新分支 `upgrade/chirpy-<新版本>` 上做）：

1. **确认版本**：
   ```bash
   curl -s https://rubygems.org/api/v1/versions/jekyll-theme-chirpy/latest.json   # 最新版
   grep -A1 'jekyll-theme-chirpy (' Gemfile.lock                                   # 本地版本
   ```
   读这两个版本之间所有的 release notes，留意 Breaking Changes。
2. **取出新旧两版主题，对比被覆盖文件的原版**：
   ```bash
   mkdir -p /tmp/chirpy && cd /tmp/chirpy
   gem fetch jekyll-theme-chirpy -v <旧版本> && gem unpack jekyll-theme-chirpy-<旧版本>.gem
   gem fetch jekyll-theme-chirpy -v <新版本> && gem unpack jekyll-theme-chirpy-<新版本>.gem
   for f in assets/css/jekyll-theme-chirpy.scss _includes/comments/giscus.html _includes/metadata-hook.html assets/img/favicons/site.webmanifest _data/locales/zh-CN.yml; do
     echo "== $f"; diff jekyll-theme-chirpy-<旧版本>/$f jekyll-theme-chirpy-<新版本>/$f
   done
   ```
   原版没变，本仓库的覆盖文件就不用动。原版变了，就把上游的变化合进本仓库的版本，同时保留本站的改动：
   - `assets/css/jekyll-theme-chirpy.scss`：本站在 `/* append your custom style below */` 之后追加了全部样式，之前的部分保持与原版一致。
   - `_includes/comments/giscus.html`：只改了一行，主题映射为 `Theme.newThemeMap('light', 'transparent_dark')`。
   - `_includes/metadata-hook.html`：原版只是一个空占位。如果新版的主题切换逻辑变了（例如 localStorage 的键名不再是 `theme`，或者启动时判断能否切换的方式变了），这个脚本可能失效，必须实测首次访问是否默认深色。
   - `site.webmanifest`：只改了 `theme_color`。
   - `zh-CN.yml`：本站只补了几个 `tabs` 键，和主题自带的语言包是深度合并的，一般不受影响。
   - 样式里用到的 CSS 变量名（`--main-bg`、`--sidebar-bg` 等）和选择器（`#sidebar`、`#post-list .card-wrapper`、`#related-posts .card` 等），要在新版的 `_sass/` 里确认还存在。
3. **同步 starter 的文件**：对比 [chirpy-starter](https://github.com/cotes2020/chirpy-starter) 的 `Gemfile`、`.github/workflows/pages-deploy.yml`、`_plugins/`、`_tabs/` 和 `_config.yml` 里新增的配置项。只合并上游的新变化，不要覆盖本站的设置。
4. **静态资源包**：看 starter 的 `assets/lib` 子模块现在指向哪个提交（`git ls-tree HEAD assets/lib`），把本仓库的子模块更新到同一个提交：
   ```bash
   git -C assets/lib fetch && git -C assets/lib checkout <提交> && git add assets/lib
   ```
5. 本地安装新版（`bundle update jekyll-theme-chirpy`），运行 `scripts/verify.sh`，并按 `pr-and-checks.md` 完整检查：两种模式各一遍、11 个以上页面、首次访问默认深色、评论区随模式切换。
6. PR 标题「主题升级：Chirpy <旧> → <新>」，描述里写清楚 release notes 要点、哪些覆盖文件动了、为什么。

**大版本升级（8.x）**：不在 `~> 7.6` 的范围内，不会自动生效。8.x 发布后，先读迁移文档，评估工作量，作为一个单独的项目和仓主商量。

---

## 3. 排障速查

| 现象 | 常见原因 | 处理 |
|---|---|---|
| 线上构建失败，本地正常 | 线上自动用了更新的 Chirpy 7.x | 按第 2 节升级；本地先 `bundle update` 复现 |
| 首页文章列表为空 | 首页文件变成了 `index.md`（Chirpy 的分页只认 `index.html`） | 改回 `index.html` |
| 某个标签页的 `<title>` 是空的 | 页面标题是中文，`_data/locales/zh-CN.yml` 缺少对应的键 | 补上 `中文标题: 中文标题` |
| 字体、图标丢失，或者样式全无 | 部署时没有拉取 `assets/lib` 子模块 | 确认部署流程里有 `submodules: true` |
| 深浅切换按钮不见了 | 启动前就有东西写死了 `data-bs-theme`，或者配置了 `theme_mode` | 去掉；默认深色交给 `metadata-hook.html` |
| 某篇文章没有评论区 | front matter 写了 `comments: false`，或者线上是 CDN 缓存的旧页面 | 先加查询参数绕过缓存，再看 front matter |
| 评论区一直显示加载中 | giscus App 的授权被撤销，或者 Discussions 被关闭 | `curl -s "https://giscus.app/api/discussions/categories?repo=lingquan11/lingquan11.github.io"` 能返回分类就说明授权正常；否则请仓主检查 |
| 合并后线上看着没变 | GitHub Pages 的 CDN 缓存（最多 10 分钟） | 等一会儿，或者加查询参数再取 |
| 新文章没出现 | `date` 晚于构建时间，或者文件名不符合 `YYYY-MM-DD-` 格式 | 检查日期和文件名 |

---

## 4. 待仓主决定的事项

这些事已经向仓主提过，还没有结论。不要自己做，可以在合适的时候（例如顺带相关的周报里）再问一次：

- **是否锁定主题版本**：把 `Gemfile` 改成精确版本、或者提交 `Gemfile.lock`，就能换来稳定，代价是拿不到自动修复，升级全靠手动。目前是不锁定，按第 2 节及时跟进。

仓主有了决定以后，把它移到 `log.md` 的「长期决定」一节，并从这里删掉。

## 5. 可以主动提议的改进

出现合适的时机时，可以提给仓主（提一次即可，他说不要就记进日志，以后不再提）：

- 「深研自述」栏目发出第一篇之后，检查分类页的排版。
- 某个项目的文章写成了系列（上、下篇），建议加系列导航。这会改动正文，所以只是建议。
- 项目页的条目超过 6 个时，建议分成「进行中」和「已完成」两组。
- 文章出现了新的内容类型（图片多、视频、交互演示），评估样式是否需要补充，例如深色模式下图片的显示效果。
