#!/usr/bin/env python3
"""把仓主发来的图片处理成可以上站的文件（需要 ImageMagick，可读 HEIC/JPG/PNG）。

    python3 .claude/skills/lingquan-blog/scripts/prep_image.py <输入> <输出.webp> --kind cover|avatar|inline
        [--rotate 90|-90|180] [--crop WxH+X+Y] [--fit [--pad white]] [--gravity center]

  cover   文章封面：裁成 1200×630（1.91:1，Chirpy 推荐比例，也是分享卡片比例）
  avatar  侧边栏头像：裁成 512×512 正方形
  inline  正文配图：宽度超过 1600 才缩小，不裁切

始终会：按 EXIF 方向转正 → 去掉全部元数据（EXIF/GPS/相机信息等）→ 存为 WebP（质量 82）。
最后检查输出文件里不再有 EXIF，有就报错退出。
--gravity 决定裁切保留哪部分：center（默认）、north（偏上）、south、east、west 等。
--rotate  先旋转（顺时针度数，-90 为逆时针）。照片拍歪、方向不对时用；旋转后先看一眼文字是否正着。
--crop    在转正、旋转之后、缩放之前先裁出一块区域（原图像素，ImageMagick 几何格式），
          用于截图只取有内容的部分（例如波形区），或裁掉画面里的他人标志、私人信息。
--fit     不裁切，整张缩进目标尺寸，空白处用 --pad 颜色补齐（默认 white）。适合宽幅图表做封面，
          裁切会切掉坐标轴或标题时用。

为什么要去元数据：手机照片常带拍摄地点（GPS）和设备信息，仓库和网站都是公开的。
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SIZES = {"cover": (1200, 630), "avatar": (512, 512)}


def im() -> list[str]:
    if shutil.which("magick"):
        return ["magick"]
    if shutil.which("convert"):
        return ["convert"]
    sys.exit("需要 ImageMagick（magick 或 convert）。Debian/Ubuntu：sudo apt-get install imagemagick")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--kind", required=True, choices=["cover", "avatar", "inline"])
    ap.add_argument("--gravity", default="center")
    ap.add_argument("--rotate", type=int, choices=[90, -90, 180])
    ap.add_argument("--crop", help="WxH+X+Y，原图像素")
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--pad", default="white")
    a = ap.parse_args()

    src, dst = Path(a.src), Path(a.dst)
    if not src.exists():
        sys.exit(f"找不到输入文件 {src}")
    if dst.suffix.lower() != ".webp":
        sys.exit("输出请用 .webp 后缀")
    dst.parent.mkdir(parents=True, exist_ok=True)

    cmd = im() + [str(src), "-auto-orient", "-strip"]
    if a.rotate:
        cmd += ["-rotate", str(a.rotate)]
    if a.crop:
        cmd += ["-crop", a.crop, "+repage"]
    if a.kind in SIZES:
        w, h = SIZES[a.kind]
        if a.fit:
            cmd += ["-resize", f"{w}x{h}", "-background", a.pad, "-gravity", "center", "-extent", f"{w}x{h}"]
        else:
            cmd += ["-resize", f"{w}x{h}^", "-gravity", a.gravity, "-extent", f"{w}x{h}"]
    else:
        cmd += ["-resize", "1600x>"]
    cmd += ["-quality", "82", str(dst)]
    subprocess.run(cmd, check=True)

    ident = ["magick", "identify"] if im() == ["magick"] else ["identify"]
    info = subprocess.run(ident + ["-format", "%wx%h|%[EXIF:*]", str(dst)], capture_output=True, text=True).stdout
    size, _, exif = info.partition("|")
    if exif.strip():
        dst.unlink(missing_ok=True)
        sys.exit("输出文件里仍有 EXIF 元数据，已删除输出，请检查 ImageMagick 版本")
    print(f"{dst}  {size}  {dst.stat().st_size // 1024} KB  元数据已清除")


if __name__ == "__main__":
    main()
