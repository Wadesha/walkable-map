#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量离线管线（后台持续执行）：对我们指定的火车站区域，逐一用真实数据计算「友好区域」，
渲染成零依赖静态图（方案 C），并上传到 GitHub Pages 作为有限展示。

行为：
- 遍历 build_station.STATIONS 中指定的站点（或命令行传入子集）。
- 每站：compute_station → 写 data/<id>.json → render_static.render → 写 static/<id>.svg/.html。
- 上传 data json / svg / html 到仓库（Contents API，token 仅走 Authorization 头，从本地记忆读取，不进文件/不回显）。
- 每完成一站重建 static/index.html 画廊（有限展示页）并上传。
- 断点续跑：已存在且含 friendly_areas 的 data json 跳过（可用 --force 重算）。
- 慢速节奏：站间暂停，Overpass 失败则跳过并继续，确保持续不间断。
"""
import sys, os, json, time, base64

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_station, render_static

OWNER = "Wadesha"
REPO = "walkable-map"
API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents"

def load_token():
    mem = open("/Users/wade/.workbuddy/MEMORY.md", encoding="utf-8").read()
    m = __import__("re").search(r"ghp_[A-Za-z0-9]+", mem)
    if not m:
        raise SystemExit("token not found in memory")
    return m.group(0)

TOKEN = load_token()
H = {"Authorization": "token " + TOKEN, "Accept": "application/vnd.github+json",
     "User-Agent": "walkable-map-batch", "Content-Type": "application/json"}

def upload(rel_path, msg):
    url = API + "/" + rel_path
    import urllib.request
    req = urllib.request.Request(url, headers=H)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode())
        sha = j.get("sha")
    except Exception as e:
        # 404 = 不存在，可新建
        if getattr(e, "code", None) == 404:
            sha = None
        else:
            print(f"  [upload GET {rel_path}] 跳过: {e}")
            return False
    content = open(os.path.join(HERE, "..", rel_path) if rel_path.startswith("stations/")
                   else os.path.join(HERE, rel_path), "rb").read()
    body = {"message": msg, "content": base64.b64encode(content).decode()}
    if sha:
        body["sha"] = sha
    data = json.dumps(body).encode()
    req2 = urllib.request.Request(url, data=data, headers=H, method="PUT")
    try:
        with urllib.request.urlopen(req2, timeout=30) as resp:
            j2 = json.loads(resp.read().decode())
        print(f"  [upload] {rel_path} -> {resp.status} {j2.get('commit',{}).get('sha','')[:8]}")
        return True
    except Exception as e:
        print(f"  [upload PUT {rel_path}] 失败: {e}")
        return False

def build_gallery():
    data_dir = os.path.join(HERE, "data")
    rows = []
    for fn in sorted(os.listdir(data_dir)):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(data_dir, fn), encoding="utf-8"))
        except Exception:
            continue
        sid = d["id"]
        fa = d.get("friendly_areas", [])
        ntot = sum(a["size"] for a in fa)
        rows.append((sid, d.get("city",""), d.get("name",""), d.get("country",""),
                     len(d["cells"]["features"]), len(fa), ntot))
    items = "\n".join(
        f'<li><a href="{sid}.html">{city} · {name}</a>（{country}）— '
        f'{nc} 街区 ｜ 友好区域 {na} 片（{ntot} 格）</li>'
        for (sid, city, name, country, nc, na, ntot) in rows)
    html = (f'<!doctype html><html lang="zh"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>火车站步行好走度 · 静态图画廊（方案 C）</title>'
            f'<style>body{{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;'
            f'max-width:820px;margin:32px auto;padding:0 16px;color:#111827;background:#f7f9fb}}'
            f'h1{{font-size:22px}}ul{{line-height:1.9}}a{{color:#0f7a3d;text-decoration:none}}'
            f'a:hover{{text-decoration:underline}}.note{{color:#6b7280;font-size:13px}}</style></head>'
            f'<body><h1>火车站站周 2km 步行好走度 · 静态图画廊</h1>'
            f'<p class="note">方案 C：零依赖静态图（无 MapLibre / 无在线底图瓦片 / 无 JS / 无 POI）。'
            f'后台真实数据预计算：OSM 建筑/绿地底图离线烤入作地理参照，街区底色与街道按「好走度」着色。共 {len(rows)} 站。</p>'
            f'<ul>{items}</ul>'
            f'<p class="note"><a href="../stations/">返回交互专题（方案 A）</a> ｜ '
            f'<a href="https://github.com/Wadesha/walkable-map">GitHub 仓库</a></p></body></html>')
    with open(os.path.join(HERE, "static", "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return len(rows)

def run(ids, force=False, pause=10):
    done = 0
    for sid in ids:
        dpath = os.path.join(HERE, "data", f"{sid}.json")
        if (not force) and os.path.exists(dpath):
            try:
                if "friendly_areas" in json.load(open(dpath, encoding="utf-8")):
                    print(f"[{sid}] 已存在（含友好区域），跳过")
                    continue
            except Exception:
                pass
        print(f"=== 开始 {sid} ===")
        try:
            out = build_station.compute_station(sid)
        except Exception as e:
            print(f"[{sid}] 计算失败，跳过: {e}")
            time.sleep(pause)
            continue
        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        try:
            render_static.render(sid)
        except Exception as e:
            print(f"[{sid}] 渲染失败: {e}")
        # 上传该站三件套
        upload(f"stations/data/{sid}.json", f"data: {sid} real + friendly areas")
        upload(f"stations/static/{sid}.svg", f"static svg: {sid}")
        upload(f"stations/static/{sid}.html", f"static html: {sid}")
        # 重建画廊并上传
        n = build_gallery()
        upload("stations/static/index.html", f"gallery update ({n} stations)")
        done += 1
        print(f"[{sid}] 完成（已处理 {done} 站），暂停 {pause}s\n")
        time.sleep(pause)
    print(f"全部完成：处理 {done} 站。")

def main():
    args = sys.argv[1:]
    force = "--force" in args
    ids = [a for a in args if a != "--force"]
    if not ids:
        ids = list(build_station.STATIONS.keys())
    run(ids, force=force, pause=12)

if __name__ == "__main__":
    main()
