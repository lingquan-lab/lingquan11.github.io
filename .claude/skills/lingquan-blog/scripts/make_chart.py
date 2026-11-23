#!/usr/bin/env python3
"""按网站配色生成柱状图（SVG，深色/浅色各一张）。只用标准库。

    python3 .claude/skills/lingquan-blog/scripts/make_chart.py <规格.json> <输出前缀>

输出 <前缀>.dark.svg 和 <前缀>.light.svg。文章里这样插入（Chirpy 按当前模式只显示其一）：

    ![图注](/assets/img/posts/<文章>/<名字>.dark.svg){: .dark }
    ![图注](/assets/img/posts/<文章>/<名字>.light.svg){: .light }

规格文件（JSON）字段：
  title        标题（必填）
  subtitle     副标题：测法、机器等（建议写，README 要求数字标明机器、尺寸和测法）
  source       出处，显示在左下角（必填，例如「数据：《矩阵乘法复盘（上）》表1」）
  categories   横轴分组，例如 ["n=64", "n=128", "n=256"]
  series       [{ "name": "...", "values": [...] }, ...]，1～4 个系列
  ordered      系列是否有先后顺序（如块大小 16/32/64）。true 用单色深浅渐变；
               false 且多于 1 个系列时拒绝生成（本站只有一种强调色，无序多系列请拆成多张图）
  format       数值格式，Python format 语法，例如 "{:.2f}×"、"{:+.1f}%"
  label        要标数值的系列名列表；省略则单系列全标、多系列不标（避免满屏数字）
  y_label      纵轴说明（可选）

配色经 dataviz 校验：单系列 深色 #76b900（8.7:1）/ 浅色 #5a8f00（3.9:1）；
有序多系列 深色 #3f6a00→#5e9a00→#8fd400、浅色 #7fb12a→#558800→#2f5200（ordinal 检查全部通过）。
柱子直角，与网站风格一致。
"""
import json
import math
import sys
from html import escape
from pathlib import Path

W, H = 720, 420
FONT = "'Source Sans Pro','Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,'SFMono-Regular','JetBrains Mono',Menlo,Consolas,monospace"

THEMES = {
    "dark": {
        "surface": "#000000", "text": "#f2f2f2", "text2": "#b5b5b5", "muted": "#8a8a8a",
        "grid": "#222222", "axis": "#4a4a4a", "accent": "#76b900",
        "single": "#76b900", "ramp": {1: ["#76b900"], 2: ["#4f8500", "#8fd400"], 3: ["#3f6a00", "#5e9a00", "#8fd400"],
                                         4: ["#3f6a00", "#558c00", "#6fb000", "#8fd400"]},
    },
    "light": {
        "surface": "#ffffff", "text": "#111111", "text2": "#444444", "muted": "#6b6b6b",
        "grid": "#ececec", "axis": "#9a9a9a", "accent": "#76b900",
        "single": "#5a8f00", "ramp": {1: ["#5a8f00"], 2: ["#7fb12a", "#2f5200"], 3: ["#7fb12a", "#558800", "#2f5200"],
                                         4: ["#7fb12a", "#609600", "#467200", "#2f5200"]},
    },
}


def text_width(s: str, size: float, mono: bool = False) -> float:
    """粗略估算文字宽度（CJK 按 1em；等宽字体其余按 0.62em，比例字体按 0.56em），用于避免重叠。"""
    return sum(size if ord(c) > 0x2E80 else size * (0.62 if mono else 0.56) for c in s)


def nice_ticks(lo: float, hi: float, n: int = 5):
    span = hi - lo or abs(hi) or 1
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while v <= hi + step * 1e-9:
        ticks.append(round(v, 10))
        v += step
    if ticks[-1] < hi:
        ticks.append(round(ticks[-1] + step, 10))
    return ticks


def fmt_tick(v: float) -> str:
    return f"{v:,.0f}" if abs(v) >= 10 or v == int(v) else f"{v:g}"


def build(spec: dict, mode: str) -> str:
    t = THEMES[mode]
    cats, series = spec["categories"], spec["series"]
    if not 1 <= len(series) <= 4:
        raise SystemExit("series 只支持 1～4 个系列")
    if len(series) > 1 and not spec.get("ordered"):
        raise SystemExit("多系列且无先后顺序：本站只有一种强调色，请拆成多张单系列图，或确认系列有序后设 ordered: true")
    for s in series:
        if len(s["values"]) != len(cats):
            raise SystemExit(f"系列「{s['name']}」的数值个数与 categories 不一致")
    colors = [t["single"]] if len(series) == 1 else t["ramp"][len(series)]
    fmt = spec.get("format", "{:g}")
    labeled = set(spec.get("label", [s["name"] for s in series] if len(series) == 1 else []))

    # 自上而下逐行排：标题 → 副标题 → 图例 → 纵轴说明 → 绘图区，互不重叠
    row = 60 if spec.get("subtitle") else 39
    legend_y = row + 22 if len(series) > 1 else None
    if legend_y:
        row = legend_y
    ylabel_y = row + 22 if spec.get("y_label") else None
    if ylabel_y:
        row = ylabel_y
    top = row + 18
    left, right, bottom = 64, 24, 64
    pw, ph = W - left - right, H - top - bottom

    vals = [v for s in series for v in s["values"]]
    lo, hi = min(0, min(vals)), max(0, max(vals))
    ticks = nice_ticks(lo, hi + (hi - lo) * 0.12)  # 顶部留出数值标签的空间
    y0, y1 = ticks[0], ticks[-1]
    ypx = lambda v: top + ph * (y1 - v) / (y1 - y0)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
           f'aria-labelledby="t d" font-family="{FONT}">']
    desc = "；".join(f"{s['name']}：" + "，".join(f"{c} {fmt.format(v)}" for c, v in zip(cats, s["values"])) for s in series)
    out.append(f'<title id="t">{escape(spec["title"])}</title><desc id="d">{escape(desc)}</desc>')
    out.append(f'<rect width="{W}" height="{H}" fill="{t["surface"]}"/>')
    # 标题区：左侧绿色竖条呼应网站标题样式
    out.append(f'<rect x="24" y="22" width="4" height="22" fill="{t["accent"]}"/>')
    out.append(f'<text x="36" y="39" font-size="18" font-weight="700" fill="{t["text"]}">{escape(spec["title"])}</text>')
    if spec.get("subtitle"):
        out.append(f'<text x="36" y="60" font-size="12.5" fill="{t["text2"]}">{escape(spec["subtitle"])}</text>')
    # 图例（≥2 个系列）
    if legend_y:
        x = 36
        for s, c in zip(series, colors):
            out.append(f'<rect x="{x}" y="{legend_y - 10}" width="11" height="11" fill="{c}"/>')
            out.append(f'<text x="{x + 16}" y="{legend_y}" font-size="12.5" fill="{t["text2"]}" font-family="{MONO}">{escape(s["name"])}</text>')
            x += 16 + text_width(s["name"], 12.5, mono=True) + 24
    # 网格与纵轴刻度
    for v in ticks:
        y = ypx(v)
        is_zero = abs(v) < 1e-12
        out.append(f'<line x1="{left}" x2="{W - right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{t["axis"] if is_zero else t["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y + 4:.1f}" font-size="11.5" text-anchor="end" fill="{t["muted"]}" font-family="{MONO}">{fmt_tick(v)}</text>')
    if ylabel_y:
        out.append(f'<text x="36" y="{ylabel_y}" font-size="11.5" fill="{t["muted"]}">{escape(spec["y_label"])}</text>')
    # 柱子
    band = pw / len(cats)
    gap = 2
    bw = min(24, (band * 0.62 - gap * (len(series) - 1)) / len(series))  # 柱宽上限 24px，剩余留白
    group_w = bw * len(series) + gap * (len(series) - 1)
    zero = ypx(0)
    for i, c in enumerate(cats):
        gx = left + band * i + (band - group_w) / 2
        for j, (s, col) in enumerate(zip(series, colors)):
            v = s["values"][i]
            x = gx + j * (bw + gap)
            yv = ypx(v)
            y, h = (yv, zero - yv) if v >= 0 else (zero, yv - zero)
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(h, 1):.1f}" fill="{col}">'
                       f'<title>{escape(s["name"])} · {escape(c)}：{escape(fmt.format(v))}</title></rect>')
            if s["name"] in labeled:
                label = fmt.format(v)
                size = 13 if len(series) == 1 else 11.5
                if len(series) == 1:
                    # 单系列：数值在柱端正上方/正下方
                    lx, anchor = x + bw / 2, "middle"
                    ly = y - 7 if v >= 0 else y + h + 15
                elif j == len(series) - 1:
                    # 组内最右侧：标在柱子右侧，避免压到相邻柱
                    lx, anchor = x + bw + 4, "start"
                    ly = (y + 4) if v >= 0 else (y + h + 4)
                elif j == 0:
                    lx, anchor = x - 4, "end"
                    ly = (y + 4) if v >= 0 else (y + h + 4)
                else:
                    # 组内中间：标在整组最高处之上
                    peak = min(ypx(sv["values"][i]) for sv in series) if v >= 0 else max(ypx(sv["values"][i]) for sv in series)
                    lx, anchor = x + bw / 2, "middle"
                    ly = peak - 7 if v >= 0 else peak + 15
                out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="{size}" font-weight="700" text-anchor="{anchor}" '
                           f'fill="{t["text"]}" font-family="{MONO}">{escape(label)}</text>')
        out.append(f'<text x="{left + band * i + band / 2:.1f}" y="{top + ph + 22}" font-size="12.5" text-anchor="middle" '
                   f'fill="{t["text2"]}" font-family="{MONO}">{escape(c)}</text>')
    out.append(f'<text x="24" y="{H - 16}" font-size="11" fill="{t["muted"]}">{escape(spec["source"])}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for key in ("title", "source", "categories", "series"):
        if key not in spec:
            sys.exit(f"规格缺少必填字段 {key}")
    prefix = Path(sys.argv[2])
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for mode in ("dark", "light"):
        p = prefix.with_name(prefix.name + f".{mode}.svg")
        p.write_text(build(spec, mode), encoding="utf-8")
        print(p)


if __name__ == "__main__":
    main()
