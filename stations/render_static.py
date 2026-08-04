#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线静态渲染（方案 C）：把一个火车站的预计算数据渲染成**零依赖 SVG 图片**。

特点：
- 输出是纯 SVG（矢量图），网页用 <img> 直接放，无需 MapLibre / 底图瓦片 / JS。
- 全部计算在后台完成，运行时零算力、零外部请求、国内绝对打得开。
- 按用户要求：**不包含 POI**。街区"好走度"去掉「吸引力」维度（POI 丰富度），
  仅用 街道本身相关的维度重加权：可达/连通/舒适/安全（已存于数据 properties）。
- 街道按真实好走度 walk（路型+坡度+离主干道，与 POI 无关）着色。

用法：
    python3 render_static.py beijing
产出：
    stations/static/<id>.svg   （图片本体，可直接 <img> 或打开）
    stations/static/<id>.html  （零 JS 预览页，内嵌说明）
"""
import sys, json, os, math

# ---- 无 POI 的街区"好走度"权重（在已存子分上重加权，使总和=1）----
# 原始：0.30·可达 +0.18·连通 +0.17·舒适 +0.15·安全 +0.20·吸引
# 去「吸引」后其余和=0.80，归一：
W = {"access": 0.30/0.80, "conn": 0.18/0.80, "comfort": 0.17/0.80, "safety": 0.15/0.80}

# 红→黄→绿 色阶（与子站一致）
STOPS = [(0, (215, 48, 39)), (50, (254, 224, 139)), (100, (26, 152, 80))]

def color(v):
    v = max(0, min(100, v))
    for i in range(len(STOPS) - 1):
        a, ca = STOPS[i]; b, cb = STOPS[i + 1]
        if a <= v <= b:
            t = (v - a) / (b - a) if b != a else 0
            r = round(ca[0] + (cb[0] - ca[0]) * t)
            g = round(ca[1] + (cb[1] - ca[1]) * t)
            bl = round(ca[2] + (cb[2] - ca[2]) * t)
            return f"rgb({r},{g},{bl})"
    return "rgb(26,152,80)"

def cell_score(p):
    return (W["access"] * p["access"] + W["conn"] * p["conn"]
            + W["comfort"] * p["comfort"] + W["safety"] * p["safety"])

def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else "beijing"
    here = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(here, "data", f"{sid}.json")
    if not os.path.exists(data_path):
        print("缺少数据文件:", data_path, "（请先运行 build_station.py", sid, "）")
        sys.exit(1)
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    lng0, lat0 = data["center"]
    lat0r = math.radians(lat0)
    def to_m(lng, lat):
        mx = (lng - lng0) * 111320 * math.cos(lat0r)
        my = (lat - lat0) * 111320
        return mx, my

    # 收集所有点定界
    xs, ys = [], []
    cell_pts = []   # (mx,my, score, props)
    for c in data["cells"]["features"]:
        poly = c["geometry"]["coordinates"][0]
        sc = cell_score(c["properties"])
        proj = [to_m(*pt[:2]) for pt in poly]
        for (mx, my) in proj:
            xs.append(mx); ys.append(my)
        cell_pts.append((proj, sc, c["properties"]))
    road_pts = []   # (list of (mx,my), walk, hw)
    for r in data.get("roads", {}).get("features", []):
        coords = r["geometry"]["coordinates"]
        proj = [to_m(*pt[:2]) for pt in coords]
        for (mx, my) in proj:
            xs.append(mx); ys.append(my)
        road_pts.append((proj, r["properties"]["walk"], r["properties"].get("hw", "")))

    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    spanx = maxx - minx or 1
    spany = maxy - miny or 1

    # 画布
    Wpx, Hpx = 1200, 1240
    M = 40
    Htop, Hbot = 72, 120
    usableW = Wpx - 2 * M
    usableH = Hpx - Htop - Hbot
    scale = min(usableW / spanx, usableH / spany)
    drawW, drawH = spanx * scale, spany * scale
    ox = (Wpx - drawW) / 2
    oy = Htop + (usableH - drawH) / 2

    def P(mx, my):
        return (ox + (mx - minx) * scale, oy + (maxy - my) * scale)

    # ---- 组装 SVG ----
    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wpx} {Hpx}" '
               f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">')
    out.append(f'<rect x="0" y="0" width="{Wpx}" height="{Hpx}" fill="#f7f9fb"/>')
    out.append(f'<text x="{Wpx/2}" y="36" text-anchor="middle" font-size="22" font-weight="700" fill="#111827">'
               f'{data["name"]} · 站周 2km 步行好走度（静态图 · 无 POI）</text>')
    out.append(f'<text x="{Wpx/2}" y="58" text-anchor="middle" font-size="13" fill="#6b7280">'
               f'后台预计算 · 零依赖图片 · 街区底色与街道颜色均按「好走度」着色</text>')

    # 街道（先画，置于底层）
    out.append('<g stroke-linecap="round" stroke-linejoin="round">')
    for proj, walk, hw in road_pts:
        if len(proj) < 2:
            continue
        d = "M" + " L".join(f"{P(mx,my)[0]:.1f},{P(mx,my)[1]:.1f}" for (mx, my) in proj)
        w = 0.7 + walk / 100 * 1.5
        out.append(f'<path d="{d}" fill="none" stroke="{color(walk)}" '
                   f'stroke-width="{w:.2f}" stroke-opacity="0.92"/>')
    out.append('</g>')

    # 街区底色（半透明覆盖）
    out.append('<g>')
    for proj, sc, props in cell_pts:
        pts = " ".join(f"{P(mx,my)[0]:.1f},{P(mx,my)[1]:.1f}" for (mx, my) in proj)
        out.append(f'<polygon points="{pts}" fill="{color(sc)}" fill-opacity="0.45" '
                   f'stroke="#ffffff" stroke-width="0.3" stroke-opacity="0.5"/>')
    out.append('</g>')

    # 友好区：街区好走度 top5
    top = sorted(cell_pts, key=lambda x: x[1], reverse=True)[:5]
    out.append('<g>')
    for proj, sc, props in top:
        cx = sum(mx for (mx, my) in proj) / len(proj)
        cy = sum(my for (mx, my) in proj) / len(proj)
        px, py = P(cx, cy)
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="13" fill="#1a9850" '
                   f'stroke="#ffffff" stroke-width="2.5"/>')
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="#ffffff"/>')
        lx = px + 16; ly = py - 14
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="12" font-weight="700" '
                   f'fill="#1a6b3a" stroke="#ffffff" stroke-width="3" paint-order="stroke">步行友好区</text>')
    out.append('</g>')

    # 图例
    lg_x, lg_y, lg_w, lg_h = (Wpx - 320) / 2, Hpx - 86, 320, 16
    grad = " ".join(f"{i}% {color(i)}" for i in (0, 25, 50, 75, 100))
    out.append(f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">'
               + "".join(f'<stop offset="{s.split("%")[0]}%" stop-color="{c}"/>'
                         for s, c in zip([f"{i}%" for i in (0,25,50,75,100)],
                                         [color(i) for i in (0,25,50,75,100)]))
               + '</linearGradient></defs>')
    out.append(f'<rect x="{lg_x}" y="{lg_y}" width="{lg_w}" height="{lg_h}" fill="url(#g)" '
               f'stroke="#d1d5db" stroke-width="1"/>')
    for frac, lab in ((0, "0 差"), (0.5, "50 中"), (1, "100 优")):
        tx = lg_x + lg_w * frac
        anchor = "start" if frac == 0 else ("middle" if frac == 0.5 else "end")
        out.append(f'<text x="{tx:.1f}" y="{lg_y + lg_h + 16}" text-anchor="{anchor}" '
                   f'font-size="12" fill="#374151">{lab}</text>')
    out.append(f'<text x="{Wpx/2}" y="{lg_y + lg_h + 40}" text-anchor="middle" '
               f'font-size="12.5" fill="#374151">街区底色 + 街道颜色 = 步行好走度（绿=好走 / 红=不好走）</text>')
    out.append(f'<text x="{Wpx/2}" y="{lg_y + lg_h + 60}" text-anchor="middle" '
               f'font-size="11.5" fill="#9ca3af">'
               f'真实数据：{len(cell_pts)} 街区 + {len(road_pts)} 条真实街道（OSM 路网 + DEM 坡度）· 不含 POI</text>')

    out.append('</svg>')
    svg = "\n".join(out)

    # 写出
    sdir = os.path.join(here, "static")
    os.makedirs(sdir, exist_ok=True)
    svg_path = os.path.join(sdir, f"{sid}.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    # 零 JS 预览页
    html = (f'<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{data["name"]} 步行好走度（静态图）</title>'
            f'<style>body{{margin:0;background:#eef2f5;display:flex;flex-direction:column;'
            f'align-items:center;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif}}'
            f'img{{max-width:100%;height:auto;box-shadow:0 4px 20px rgba(0,0,0,.12);margin:16px}}'
            f'p{{color:#6b7280;font-size:13px;margin:0 0 24px}}</style></head>'
            f'<body><img src="{sid}.svg" alt="{data["name"]} 步行好走度静态图">'
            f'<p>方案 C：零依赖静态图，无 MapLibre、无底图瓦片、无 JS、无 POI。</p></body></html>')
    html_path = os.path.join(sdir, f"{sid}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"写出: {svg_path}  ({len(svg)} 字节)")
    print(f"写出: {html_path}  ({len(html)} 字节)")
    print(f"街区 {len(cell_pts)} ｜ 街道 {len(road_pts)} ｜ 友好区 top5 分数 "
          f"{[round(t[1]) for t in top]}")

if __name__ == "__main__":
    main()
