#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 stations/cities.json：供总览图(overview.html)消费的每城汇总。
- 扫描 data/*.json，计算每城均值好走度(score)与友好区域总格数(friendly)。
- 始终包含 build_station.STATIONS 全部 17 城；有数据的标 hasDetail=True（静态 svg 存在）。
- 无数据城 score=null / hasDetail=False，总览图显示为灰色"待计算"。
后台批处理每算完一站可重跑本脚本刷新；也可由 batch_stations.build_gallery 同步骤调用。
"""
import os, json, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_station

data_dir = os.path.join(HERE, "data")
static_dir = os.path.join(HERE, "static")

def score_of(sid):
    dpath = os.path.join(data_dir, f"{sid}.json")
    if not os.path.exists(dpath):
        return None, 0, False
    try:
        d = json.load(open(dpath, encoding="utf-8"))
        cells = d["cells"]["features"]
        sc = round(sum(c["properties"]["score"] for c in cells) / len(cells), 1)
        fr = sum(a["size"] for a in d.get("friendly_areas", []))
        has = os.path.exists(os.path.join(static_dir, f"{sid}.svg"))
        return sc, fr, has
    except Exception as e:
        print("  [gen_cities] 读", sid, "失败:", e)
        return None, 0, False

cities = []
for sid, st in build_station.STATIONS.items():
    sc, fr, has = score_of(sid)
    cities.append({
        "id": sid, "city": st["city"], "country": st["country"], "name": st["name"],
        "lng": st["lng"], "lat": st["lat"],
        "score": sc, "friendly": fr, "hasDetail": has,
    })

cities.sort(key=lambda r: (r["country"], r["city"]))
out = {"generated": "2026-08-04", "total": len(cities), "cities": cities}
with open(os.path.join(HERE, "cities.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print(f"cities.json 写出: {len(cities)} 城 ｜ 有精细图: {sum(1 for c in cities if c['hasDetail'])} ｜ "
      f"已算分: {sum(1 for c in cities if c['score'] is not None)}")
