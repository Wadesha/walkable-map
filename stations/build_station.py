#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线管线：为一个火车站生成「站周 2km 步行友好专题」真实数据。
数据来源（真实）：
  - 路网 / POI：OpenStreetMap via Overpass API
  - 高程 / 坡度：Open-Meteo Elevation API
计算（真实为主，部分相对归一）：
  - 可达性 / 吸引力：基于真实步行路网的最短路径距离（Dijkstra）到各类 POI
  - 连通性：路网交叉口密度（站内切面 min-max 归一）
  - 舒适性：真实 DEM 坡度（站内切面 min-max 归一）
  - 安全性：距主干道距离（站内切面 min-max 归一）
  - 综合：0.30·可达 + 0.18·连通 + 0.17·舒适 + 0.15·安全 + 0.20·吸引
仅用 Python 标准库（urllib / json / heapq / math）。
输出 stations/data/<id>.json，schema 与子站渲染一致。

本文件同时被批处理脚本 batch_stations.py 调用：compute_station(id) 返回 out 字典，
并在 out 中额外写入：
  - friendly_areas：连通聚类得到的「友好区域」列表（无 POI 重加权 ≥ 阈值 的相邻格子成片）
  - friendly_threshold：聚类阈值
每个友好区域含 size(格数)、score_avg、centroid(经纬度)、cells([i,j]...)、edges(边界线段, geo)
"""
import sys, json, math, urllib.request, urllib.parse, heapq, os, time

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
ELEV_API = "https://api.open-meteo.com/v1/elevation"

# 与子站一致的演示站点；此处为「我们指定的区域」：以北京南站为锚，扩展到主要高铁站。
# 坐标为各站大致中心（足以框定站周 2km 研究范围）。
STATIONS = {
    "beijing":   {"city":"北京","country":"中国","name":"北京南站","lng":116.3782,"lat":39.8714},
    "shanghai":  {"city":"上海","country":"中国","name":"上海虹桥站","lng":121.3190,"lat":31.1940},
    "guangzhou": {"city":"广州","country":"中国","name":"广州南站","lng":113.2700,"lat":22.9900},
    "shenzhen":  {"city":"深圳","country":"中国","name":"深圳北站","lng":114.2180,"lat":22.6100},
    "chengdu":   {"city":"成都","country":"中国","name":"成都东站","lng":104.1410,"lat":30.6310},
    "wuhan":     {"city":"武汉","country":"中国","name":"武汉站","lng":114.4250,"lat":30.5980},
    "xian":      {"city":"西安","country":"中国","name":"西安北站","lng":108.9380,"lat":34.3800},
    "nanjing":   {"city":"南京","country":"中国","name":"南京南站","lng":118.7960,"lat":31.9550},
    "hangzhou":  {"city":"杭州","country":"中国","name":"杭州东站","lng":120.2130,"lat":30.2900},
    "zhengzhou": {"city":"郑州","country":"中国","name":"郑州东站","lng":113.7690,"lat":34.7580},
    "tokyo":     {"city":"东京","country":"日本","name":"东京站","lng":139.7670,"lat":35.6810},
    "seoul":     {"city":"首尔","country":"韩国","name":"首尔站","lng":126.9700,"lat":37.5540},
    "paris":     {"city":"巴黎","country":"法国","name":"巴黎北站","lng":2.3550,"lat":48.8800},
    "london":    {"city":"伦敦","country":"英国","name":"国王十字站","lng":-0.1230,"lat":51.5320},
    "berlin":    {"city":"柏林","country":"德国","name":"柏林中央站","lng":13.3690,"lat":52.5250},
    "newyork":   {"city":"纽约","country":"美国","name":"宾州车站","lng":-73.9940,"lat":40.7500},
    "moscow":    {"city":"莫斯科","country":"俄罗斯","name":"莫斯科站","lng":37.6530,"lat":55.7760},
}

W_ACCESS = {"park":1.0,"metro":1.2,"shop":0.9,"school":0.7,"hospital":0.8}
QUERY_R_M = 2200          # 拉取范围（覆盖 2km + 余量）
GRID_HALF = 1000          # 专题半径 2km
CELL_M = 160
N = 13                    # 每边格数 → 13x13 ≈ 169 格

# 友好区域聚类阈值（无 POI 重加权后的好走度）
FRIENDLY_THRESH = 65
# 无 POI 的「好走度」权重（在已存子分上重加权，使总和=1）
W_PFOI = {"access":0.30/0.80,"conn":0.18/0.80,"comfort":0.17/0.80,"safety":0.15/0.80}

def poi_free_score(p):
    return (W_PFOI["access"]*p["access"] + W_PFOI["conn"]*p["conn"]
            + W_PFOI["comfort"]*p["comfort"] + W_PFOI["safety"]*p["safety"])

def hav(lng1,lat1,lng2,lat2):
    R=6371000; r=math.pi/180
    dLat=(lat2-lat1)*r; dLng=(lng2-lng1)*r
    a=math.sin(dLat/2)**2+math.cos(lat1*r)*math.cos(lat2*r)*math.sin(dLng/2)**2
    return 2*R*math.asin(math.sqrt(a))

def overpass(q, tries=3):
    last=None
    for ep in OVERPASS_ENDPOINTS:
        for attempt in range(tries):
            try:
                data=urllib.parse.urlencode({"data":q}).encode()
                req=urllib.request.Request(ep,data=data,headers={"User-Agent":"walkable-map-demo/1.0"})
                with urllib.request.urlopen(req,timeout=180) as resp:
                    return json.load(resp)
            except Exception as e:
                last=e
                print(f"    Overpass {ep} 尝试 {attempt+1} 失败: {e}")
                time.sleep(3)
    raise last or RuntimeError("overpass failed")

def elev_batch(points):
    """points: list of (lat,lng). 返回 dict (roundlat6,roundlng6)->elev。Open-Meteo 每次最多 100 点。"""
    out={}
    for i in range(0,len(points),100):
        chunk=points[i:i+100]
        lat=",".join(str(p[0]) for p in chunk)
        lng=",".join(str(p[1]) for p in chunk)
        url=f"{ELEV_API}?latitude={lat}&longitude={lng}"
        req=urllib.request.Request(url,headers={"User-Agent":"walkable-map-demo/1.0"})
        with urllib.request.urlopen(req,timeout=60) as resp:
            j=json.load(resp)
        for p,e in zip(chunk,j.get("elevation",[])):
            out[(round(p[0],6),round(p[1],6))]=e
    return out

def classify(tags):
    if not tags: return None
    lvl=tags.get("leisure")
    if lvl in ("park","garden"): return "park"
    ry=tags.get("railway")
    if ry in ("station","halt","stop","tram_stop") or tags.get("station")=="subway": return "metro"
    if "shop" in tags: return "shop"
    am=tags.get("amenity")
    if am in ("hospital","clinic","dentist"): return "hospital"
    if am in ("school","university","college","kindergarten"): return "school"
    if am: return "shop"   # 其余便民设施视为商业目的地
    return None

def coords_of(el):
    """兼容 Overpass geometry 的两种格式：[{lat,lon}] 或 [[lon,lat]]。"""
    g=el.get("geometry")
    if not g: return []
    out=[]
    for c in g:
        if isinstance(c,dict):
            out.append((c["lon"],c["lat"]))
        elif isinstance(c,list):
            out.append((c[0],c[1]))
    return out

def build_graph(ways, skip=("motorway","motorway_link")):
    adj={}
    nodes={}
    def nid(lon,lat):
        k=(round(lon,5),round(lat,5)); return k
    for w in ways:
        hw=w.get("tags",{}).get("highway")
        if hw in skip: continue
        geo=coords_of(w)
        if len(geo)<2: continue
        pts=[(round(c[0],5),round(c[1],5)) for c in geo]
        for p in pts: nodes[p]=p
        for a,b in zip(pts,pts[1:]):
            d=hav(a[0],a[1],b[0],b[1])
            adj.setdefault(a,[]).append((b,d))
            adj.setdefault(b,[]).append((a,d))
    return adj, nodes

def dijkstra(adj, src):
    dist={src:0.0}; pq=[(0.0,src)]
    while pq:
        d,u=heapq.heappop(pq)
        if d>dist.get(u,1e18): continue
        for v,w in adj.get(u,[]):
            nd=d+w
            if nd<dist.get(v,1e18):
                dist[v]=nd; heapq.heappush(pq,(nd,v))
    return dist

def nearest_node(nodes, lng, lat):
    best=None; bd=1e18
    for n in nodes:
        d=hav(n[0],n[1],lng,lat)
        if d<bd: bd=d; best=n
    return best, bd

# 街道"好走度"（与目的地无关，只看街道本身）：路型 + 坡度 + 离主干道
ROAD_BASE={"footway":92,"path":90,"pedestrian":90,"living_street":88,"residential":82,
           "service":68,"unclassified":70,"tertiary":62,"tertiary_link":60,
           "secondary":52,"secondary_link":50,"primary":38,"primary_link":36,
           "trunk":30,"trunk_link":28}
def road_walk(hw, slope_deg, major_dist):
    base=ROAD_BASE.get(hw,60)
    comfort=max(0,100-slope_deg*6)
    safety=max(0,min(100, major_dist/300.0*100)) if major_dist<9999 else 80
    return round(0.40*base+0.35*comfort+0.25*safety)

def compute_station(sid):
    st=STATIONS.get(sid)
    if not st:
        raise SystemExit("unknown station: "+sid)
    lng0,lat0=st["lng"],st["lat"]
    mLat=111320.0; mLng=111320.0*math.cos(lat0*math.pi/180)
    dLat=QUERY_R_M/mLat; dLng=QUERY_R_M/mLng
    S=lat0-dLat; Nn=lat0+dLat; W=Lng0=lng0-dLng; E=lng0+dLng
    bbox=f"{S:.5f},{W:.5f},{Nn:.5f},{E:.5f}"

    print(f"[{sid}] [1/5] Overpass 拉取路网+POI: {st['name']} bbox={bbox}")
    q=("""[out:json][timeout:180];
(
  way["highway"](__BBOX__);
  node["amenity"](__BBOX__);
  node["shop"](__BBOX__);
  node["leisure"~"park|garden"](__BBOX__);
  node["railway"~"station|halt"](__BBOX__);
  way["amenity"](__BBOX__);
  way["shop"](__BBOX__);
  way["leisure"~"park|garden"](__BBOX__);
  way["building"](__BBOX__);
);
out geom;""").replace("__BBOX__",bbox)
    data=overpass(q)

    ways=[]; pois=[]; buildings=[]; greens=[]
    for el in data.get("elements",[]):
        t=el.get("type"); tags=el.get("tags",{})
        if t=="way" and tags.get("highway"):
            ways.append(el)
        if t=="way" and tags.get("building"):
            buildings.append(el)
        if t=="way" and tags.get("leisure") in ("park","garden"):
            greens.append(el)
        ctype=classify(tags)
        if not ctype: continue
        if t=="node" and "lat" in el:
            pll=(el["lon"],el["lat"])
        elif t=="way" and el.get("geometry"):
            g=coords_of(el)
            if not g: continue
            pll=(sum(c[0] for c in g)/len(g), sum(c[1] for c in g)/len(g))
        else:
            continue
        name=tags.get("name") or tags.get("name:en") or ctype
        pois.append({"lng":pll[0],"lat":pll[1],"type":ctype,"name":name})
    print(f"[{sid}]      路网 way 段: {len(ways)} ｜ POI: {len(pois)} ｜ 建筑: {len(buildings)} ｜ 绿地: {len(greens)}")

    bld_feats=[]; green_feats=[]
    for w in buildings:
        g=coords_of(w)
        if len(g)<3: continue
        bld_feats.append({"type":"Feature","geometry":{"type":"Polygon",
            "coordinates":[[[c[0],c[1]] for c in g]]},"properties":{}})
    for w in greens:
        g=coords_of(w)
        if len(g)<3: continue
        green_feats.append({"type":"Feature","geometry":{"type":"Polygon",
            "coordinates":[[[c[0],c[1]] for c in g]]},"properties":{}})

    print(f"[{sid}] [2/5] 构建步行图 + 高程采样")
    adj, nodes = build_graph(ways)
    print(f"[{sid}]      图节点: {len(nodes)} ｜ 边: {sum(len(v) for v in adj.values())//2}")

    corners=[]
    for i in range(N+1):
        for j in range(N+1):
            cx=lng0+(-GRID_HALF+i*CELL_M+CELL_M/2 - CELL_M/2)/mLng
            cy=lat0+(-GRID_HALF+j*CELL_M+CELL_M/2 - CELL_M/2)/mLat
            corners.append((round(cy,6),round(cx,6)))
    elev=elev_batch(list(set(corners)))
    print(f"[{sid}]      高程采样点: {len(elev)}")

    major=[]
    for w in ways:
        hw=w.get("tags",{}).get("highway","")
        if hw in ("trunk","trunk_link","primary","primary_link"):
            for c in coords_of(w):
                major.append(c)

    poi_nodes=[]
    for p in pois:
        n,_=nearest_node(nodes,p["lng"],p["lat"])
        poi_nodes.append((n,p))

    print(f"[{sid}] [3/5] 逐格计算（真实路网 Dijkstra + DEM 坡度）")
    raw={}; cell_map={}
    for i in range(N):
        for j in range(N):
            cx=lng0+(-GRID_HALF+i*CELL_M+CELL_M/2)/mLng
            cy=lat0+(-GRID_HALF+j*CELL_M+CELL_M/2)/mLat
            sn,_=nearest_node(nodes,cx,cy)
            if sn and adj:
                dist=dijkstra(adj,sn)
            else:
                dist={}
            dcat={}
            for n,p in poi_nodes:
                d=dist.get(n)
                if d is None:
                    d=hav(p["lng"],p["lat"],cx,cy)
                if p["type"] not in dcat or d<dcat[p["type"]]:
                    dcat[p["type"]]=d
            acc=0; types_in=set()
            for cat,d in dcat.items():
                if d<1400:
                    acc+=W_ACCESS.get(cat,0.9)*math.exp(-d/450)
                    if d<800: types_in.add(cat)
            access=min(100,acc*55)
            attr=min(100,len(types_in)/5*100)
            conn_cnt=0
            for n in nodes:
                if len(adj.get(n,[]))>=3 and hav(n[0],n[1],cx,cy)<300:
                    conn_cnt+=1
            esw=elev.get((round(cy-CELL_M/2/mLat,6),round(cx-CELL_M/2/mLng,6)))
            ene=elev.get((round(cy+CELL_M/2/mLat,6),round(cx+CELL_M/2/mLng,6)))
            enw=elev.get((round(cy+CELL_M/2/mLat,6),round(cx-CELL_M/2/mLng,6)))
            ese=elev.get((round(cy-CELL_M/2/mLat,6),round(cx+CELL_M/2/mLng,6)))
            slope=0.0
            if None not in (esw,ene,enw,ese):
                gx=(ese-esw)/(2*CELL_M); gy=(ene-enw)/(2*CELL_M)
                slope=math.degrees(math.atan(math.hypot(gx,gy)))
            sd=min((hav(m[0],m[1],cx,cy) for m in major), default=9999)
            raw[(i,j)]={"cx":cx,"cy":cy,"access":access,"attr":attr,
                        "conn_raw":conn_cnt,"slope":slope,"safe_raw":sd}

    def mm(vals):
        lo,hi=min(vals),max(vals)
        return (lambda v:0.0 if hi==lo else (v-lo)/(hi-lo)*100)
    conn_n=mm([v["conn_raw"] for v in raw.values()])
    slope_n=mm([v["slope"] for v in raw.values()])
    safe_n=mm([v["safe_raw"] for v in raw.values()])

    print(f"[{sid}] [4/5] 合成分数 + 生成 GeoJSON")
    cells=[]
    for (i,j),v in raw.items():
        conn=conn_n(v["conn_raw"])
        comfort=100-slope_n(v["slope"])
        safety=safe_n(v["safe_raw"])
        score=0.30*v["access"]+0.18*conn+0.17*comfort+0.15*safety+0.20*v["attr"]
        swLng=v["cx"]-CELL_M/2/mLng; swLat=v["cy"]-CELL_M/2/mLat
        dLng=CELL_M/mLng; dLat=CELL_M/mLat
        feat={
            "type":"Feature",
            "geometry":{"type":"Polygon","coordinates":[[[swLng,swLat],[swLng+dLng,swLat],[swLng+dLng,swLat+dLat],[swLng,swLat+dLat],[swLng,swLat]]]},
            "properties":{
                "center":[v["cx"],v["cy"]],
                "score":round(score),
                "access":round(v["access"]),
                "conn":round(conn),
                "comfort":round(comfort),
                "safety":round(safety),
                "attr":round(v["attr"]),
                "slope":round(v["slope"],1)
            }
        }
        cells.append(feat)
        cell_map[(i,j)]=feat
    sc=[c["properties"]["score"] for c in cells]
    print(f"[{sid}]      分数范围: {min(sc)}–{max(sc)} ｜ 均值 {sum(sc)/len(sc):.1f}")

    # 友好区域：无 POI 重加权 ≥ 阈值 的相邻格子连通聚类
    print(f"[{sid}] [4.5/5] 聚类友好区域（阈值 {FRIENDLY_THRESH}，无 POI）")
    friendly=set((i,j) for (i,j),c in cell_map.items() if poi_free_score(c["properties"])>=FRIENDLY_THRESH)
    visited=set(); areas=[]
    for start in friendly:
        if start in visited: continue
        stack=[start]; comp=[]
        while stack:
            cur=stack.pop()
            if cur in visited or cur not in friendly: continue
            visited.add(cur); comp.append(cur)
            for d in ((1,0),(-1,0),(0,1),(0,-1)):
                nb=(cur[0]+d[0],cur[1]+d[1])
                if nb in friendly and nb not in visited: stack.append(nb)
        if len(comp)<2: continue
        lngs=[]; lats=[]
        for (i,j) in comp:
            cc=cell_map[(i,j)]["properties"]["center"]
            lngs.append(cc[0]); lats.append(cc[1])
        # 边界线段（geo）：相邻友好格共享边不画，外部边画
        edges=[]
        for (i,j) in comp:
            poly=cell_map[(i,j)]["geometry"]["coordinates"][0]  # 5 点闭合
            c0,c1,c2,c3=tuple(poly[0]),tuple(poly[1]),tuple(poly[2]),tuple(poly[3])
            # 边: (c0,c1)底→邻(i,j-1); (c1,c2)右→邻(i+1,j); (c2,c3)顶→邻(i,j+1); (c3,c0)左→邻(i-1,j)
            neigh={(c0,c1):(i,j-1),(c1,c2):(i+1,j),(c2,c3):(i,j+1),(c3,c0):(i-1,j)}
            for seg,nb in neigh.items():
                if nb not in comp:
                    edges.append([list(seg[0]),list(seg[1])])
        areas.append({
            "size":len(comp),
            "score_avg":round(sum(poi_free_score(cell_map[k]["properties"]) for k in comp)/len(comp),1),
            "centroid":[round(sum(lngs)/len(lngs),6),round(sum(lats)/len(lats),6)],
            "cells":[[i,j] for (i,j) in comp],
            "edges":edges
        })
    areas.sort(key=lambda a:-a["size"])
    print(f"[{sid}]      友好区域: {len(areas)} 片 ｜ 总友好格: {sum(a['size'] for a in areas)}")

    # 街道"好走度"
    print(f"[{sid}] [4.8/5] 计算街道好走度（路型+坡度+离主干道）")
    roads=[]
    for w in ways:
        hw=w.get("tags",{}).get("highway","")
        geo=coords_of(w)
        if len(geo)<2: continue
        clat=sum(c[1] for c in geo)/len(geo); clng=sum(c[0] for c in geo)/len(geo)
        e0=elev.get((round(geo[0][1],6),round(geo[0][0],6)))
        e1=elev.get((round(geo[-1][1],6),round(geo[-1][0],6)))
        slope=0.0
        if e0 is not None and e1 is not None:
            L=hav(geo[0][0],geo[0][1],geo[-1][0],geo[-1][1])
            if L>1: slope=math.degrees(math.atan(abs(e1-e0)/L))
        md=min((hav(m[0],m[1],clng,clat) for m in major), default=9999)
        walk=road_walk(hw,slope,md)
        roads.append({"type":"Feature",
            "geometry":{"type":"LineString","coordinates":[[c[0],c[1]] for c in geo]},
            "properties":{"hw":hw,"walk":walk,"slope":round(slope,1)}})
    rw=[r["properties"]["walk"] for r in roads]
    print(f"[{sid}]      街道段: {len(roads)} ｜ 好走度范围 {min(rw)}–{max(rw)} 均值 {sum(rw)/len(rw):.1f}")

    out={
        "id":sid,"name":st["name"],"city":st["city"],"country":st["country"],
        "center":[lng0,lat0],
        "generated":"2026-08-04",
        "source":"OSM Overpass (路网/POI) + Open-Meteo elevation (坡度); 连通性/舒适/安全为站内 min-max 归一; 街道好走度=路型+坡度+离主干道; 友好区域=无POI重加权连通聚类",
        "friendly_threshold":FRIENDLY_THRESH,
        "cells":{"type":"FeatureCollection","features":cells},
        "pois":pois,
        "roads":{"type":"FeatureCollection","features":roads},
        "buildings":{"type":"FeatureCollection","features":bld_feats},
        "greens":{"type":"FeatureCollection","features":green_feats},
        "friendly_areas":areas
    }
    return out

def main():
    sid=sys.argv[1] if len(sys.argv)>1 else "beijing"
    out=compute_station(sid)
    odir=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
    os.makedirs(odir,exist_ok=True)
    opath=os.path.join(odir,f"{sid}.json")
    with open(opath,"w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False)
    fa=out["friendly_areas"]
    print(f"[5/5] 写出: {opath}  ({len(out['cells']['features'])} 格, "
          f"{len(out['pois'])} POI, 友好区域 {len(fa)} 片)")

if __name__=="__main__":
    main()
