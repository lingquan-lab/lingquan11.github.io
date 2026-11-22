# 站点图标与分享图源文件（不发布）

- `../assets/img/favicons/favicon.svg`：主图标（带斜杠的零），其余尺寸由它导出
- `maskable.svg`：PWA 512 maskable 图标（图形缩进安全区）
- `social-preview.svg`：链接分享卡片 1200×630，字体 Noto Sans CJK SC

重新导出（需 librsvg、ImageMagick、fonts-noto-cjk）：

```bash
cd assets/img/favicons
rsvg-convert -w 96  favicon.svg -o favicon-96x96.png
rsvg-convert -w 180 favicon.svg -o apple-touch-icon.png
rsvg-convert -w 192 favicon.svg -o web-app-manifest-192x192.png
rsvg-convert -w 512 ../../../_design/maskable.svg -o web-app-manifest-512x512.png
for s in 16 32 48; do rsvg-convert -w $s favicon.svg -o /tmp/ico-$s.png; done
convert /tmp/ico-16.png /tmp/ico-32.png /tmp/ico-48.png favicon.ico
cd ../ && rsvg-convert -w 1200 ../../_design/social-preview.svg -o social-preview.png
```
