# 图片与图表：封面、头像、正文配图、数据图

仓主 2026-11-23 采纳了「文章配封面图」「以后的文章多用图表」「换头像」三项。图片由仓主提供，维护者负责处理、放置和接入。

## 共同规则

- **每张图都先过 `scripts/prep_image.py`。** 它会去掉 EXIF/GPS 等元数据（手机照片常带拍摄地点，仓库和网站都是公开的）、按方向转正、裁到需要的尺寸、存成 WebP。不要把仓主发来的原图直接提交。
- **只用仓主给的图或仓主的公开材料**（仓库里的截图、波形、报告）。不从网上找图，不用 AI 生成"示意图"冒充实验结果。
- **画面里不能有私人信息**：桌面上的聊天窗口、文件路径里的真实姓名以外的信息、学号、宿舍或家里的环境细节等。有的话先告诉仓主，裁掉或换图。
- 文件放在 `assets/img/` 下，见各节。文件名用英文小写加连字符。

## 1. 文章封面

Chirpy 读文章 front matter 里的 `image` 字段：首页卡片右侧显示缩略图，文章页顶部显示大图（`alt` 会作为图注显示在大图下方）。

```bash
python3 .claude/skills/lingquan-blog/scripts/prep_image.py 原图.jpg \
  assets/img/posts/<文章文件名去掉.md>/cover.webp --kind cover [--gravity north]
```

然后在**这篇文章的 front matter** 里加（放在 `tags` 之后）：

```yaml
image:
  path: /assets/img/posts/<文章文件名去掉.md>/cover.webp
  alt: 一句话说明图里是什么，例如「达芬奇Pro开发板上板实测」
```

- **授权范围**：仓主采纳「配封面图」，并且为某篇文章发来了图，就等于授权给**这篇**文章加 `image` 字段。只加这一个字段，不动其他 front matter，正文更不能动（`verify.sh` 的正文守卫会检查）。
- **选什么图最好**：真实的工作素材最能打动导师：开发板实拍、Vivado/OpenROAD 的时序或版图截图、仿真波形、性能对比图。纯装饰图不如没有。
- **裁切**：1200×630 是横幅。主体偏上（例如开发板在照片上半部分）就加 `--gravity north`，裁完一定要打开看一眼，确认主体没被裁掉。
- **加了封面之后要检查**：首页卡片的图文排版、置顶大卡片（`zq-featured`）的效果、文章页顶部大图，深浅两种模式和手机宽度都要看。
- 仓主的 front matter 规则同样适用：以后新文章要不要封面、用哪张，由仓主决定。

## 2. 侧边栏头像

```bash
python3 .claude/skills/lingquan-blog/scripts/prep_image.py 原图.jpg assets/img/avatar.webp --kind avatar [--gravity north]
```

再把 `_config.yml` 的 `avatar` 改成 `/assets/img/avatar.webp`（原来是 GitHub 头像的外链）。头像放进仓库后，不再依赖 github.com 加载。

- 头像是否用真人照片完全由仓主决定，不要替他选。
- 侧边栏头像有方形绿框（样式里的 `#avatar`）；正方形构图、主体居中效果最好。

## 3. 正文配图

仓主在写文章时想放图，可以把图发给维护者处理：

```bash
python3 .claude/skills/lingquan-blog/scripts/prep_image.py 原图.png assets/img/posts/<文章>/<名字>.webp --kind inline
```

把处理后的路径交给仓主，由**仓主**写进正文：`![图注](/assets/img/posts/<文章>/<名字>.webp)`。存量文章的正文不动；仓主明确授权在某处插图时，才由维护者插入，并在 PR 里写明位置和授权。

## 4. 数据图表

脚本：`scripts/make_chart.py`，只用 Python 标准库，输出 SVG（深色、浅色各一张）。配色已经过 dataviz 校验，和网站一致。

**流程**

1. 数据只能来自仓主的文章、仓库里的原始数据（CSV、日志）或仓主直接给的数字。照抄，不重新计算、不四舍五入成更好看的数。
2. 先想清楚这张图要说明什么，再选画法：
   - 跨数量级的原始耗时（0.02 ms 到 11 ms）不要直接画，最小的柱子会看不见；改画比值（加速比）或相对变化（%）。
   - 一张图只用一根纵轴。两种量纲不同的数据，拆成两张图。
   - 本站只有一种强调色，所以**多系列必须是有序的**（例如块大小 16/32/64），脚本用同一种绿由浅到深表示顺序；无序的多个系列拆成多张单系列图，脚本会拒绝生成。
   - 多系列时不要给每根柱子都标数，只标故事的主角（`label` 字段）；单系列时全部标出。
3. 写规格文件，放在 `_design/charts/<名字>.json`（下划线目录不会被发布，规格和数据都留在这里，以后能重画）。字段说明见脚本开头。`subtitle` 写测法和机器，`source` 写出处，二者都是 README「数字标明机器、尺寸和测法」的要求。
4. 生成：
   ```bash
   python3 .claude/skills/lingquan-blog/scripts/make_chart.py _design/charts/<名字>.json \
     assets/img/posts/<文章文件名去掉.md>/<名字>
   ```
   得到 `<名字>.dark.svg` 和 `<名字>.light.svg`。用 `rsvg-convert` 转成 PNG 打开看一遍：标题、图例、轴说明不重叠，标签不压柱子，负值标签可读。
5. 交给仓主插入正文（两行一起用，Chirpy 会按当前模式只显示其中一张）：
   ```markdown
   ![图注](/assets/img/posts/<文章>/<名字>.dark.svg){: .dark }
   ![图注](/assets/img/posts/<文章>/<名字>.light.svg){: .light }
   ```
   图下方最好保留原来的数据表格，读者可以核对确切数值。

**现成样例**：`_design/charts/` 里有两份根据《矩阵乘法复盘（上）》表1、表3 做的规格（循环顺序加速比；分块相对 ikj 的耗时变化），生成的图在 `assets/img/posts/2026-11-22-cpp-matmul-retrospective-1/`。是否插进那篇文章由仓主决定。

## 交付

图片和图表也走 PR。PR 描述里列出：每张图的来源（仓主哪天发来的、或数据出自哪里）、处理参数（`--kind`、`--gravity`）、改了哪篇文章的哪个 front matter 字段，并附上深浅两种模式的截图说明。
