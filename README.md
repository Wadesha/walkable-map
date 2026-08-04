[GitHub 仓库](https://github.com/Wadesha/walkable-map)

# 步行友好地图 · 原型（Walkable Map Prototype）

> 一个用来思考「怎么定义 / 组织 / 展示适合步行的区域」的可交互网页原型。
> 全部数据为**模拟生成**，仅用于演示交互与设计思路，不代表任何真实地点的步行友好度。

- 🌐 在线演示（GitHub Pages）：https://wadesha.github.io/walkable-map/
- 📦 单文件交付：`index.html`（HTML + CSS + JS 全部内联，无构建步骤）

---

## 1. 这是什么

把一片城区切成很多小方格，每个格子算出一个 **0–100 的步行友好分数**，用红→黄→绿表示（绿 = 好走，红 = 难走）。
目标不是做一个"正确"的步行指数，而是先把「定义 → 组织 → 展示」这条链路在网页上跑通，作为和规划者 / 居民讨论的**可视化沟通工具**。

核心交互：
- 点地图**任意位置** → 以该点为中心生成**等时圈**（按步行时间 + 坡度阈值能走到的范围，蓝色高亮）。
- 点某个**格子** → 弹窗给出 5 个维度的拆解分数。
- 左侧**街区排行**把整片区域切成 3×3，看哪片整体更好走。
- 控制面板可调最大步行时间、最大坡度、显示哪些设施、开关各图层。

---

## 2. 怎么定义「步行友好」（5 个维度）

“好走”不是一句话，而是 5 个可量化维度的加权组合：

| 维度 | 含义 | 原型里的模拟近似 |
|------|------|------------------|
| 可达性 | 几分钟能走到目的地 | 到各类 POI 的距离衰减求和（越近越高） |
| 连通性 | 路网密不密、街块大不大 | 噪声函数生成“路网密度”，中心略高 |
| 舒适性 | 坡度、绿荫、路面 | 噪声生成坡度；公园附近额外加“绿荫”分 |
| 安全性 | 车速、过街、照明 | 噪声生成（模拟主干道附近得分低） |
| 吸引力 | 设施种类多不多 | 800m 内覆盖的设施类型数量 / 5 |

**综合分数**（权重见第 4 节）：

```
score = 0.30·可达 + 0.18·连通 + 0.17·舒适 + 0.15·安全 + 0.20·吸引
```

用连续分数而非「好 / 坏」二分，才有对比和改进空间。分级：≥80 优 / ≥65 良 / ≥50 中 / ≥35 较差 / <35 差。

---

## 3. 数据从哪来（组织方式）

真实项目里，这部分应来自：**路网**（带属性）、**地形 DEM**（坡度）、**POI**（设施）、**土地利用**（混合度）。
本原型用**纯前端模拟**替代，方便直接打开就看效果：

- **网格**：以中心点（北京，纯示意）切出 22×22 个方格，每格约 170m（≈3.9km × 3.5km 的城区）。
- **POI**：手工摆了 8 个模拟点（公园×2、地铁×2、商铺×2、学校×1、医院×1）。
- **分数**：每个格子按上面 5 个维度分别计算，再加权合成。
- **等时圈**：从点击点出发，`步行速度 80m/分 × 时间` 得到半径，且坡度不超过阈值——满足的格子高亮。
- **空间单元**：原型用「栅格评分」表达；真实项目还可叠加「等时圈 / 路段属性 / 街区单元」等多种单元。

> ⚠️ 距离用的是**直线距离（欧几里得）**，不是真实路网步行距离；等时圈因此是“近似圆”，真实情况会被道路走向、围墙、河流切碎。这是原型的已知简化。

---

## 4. 方法学 / 评分公式（透明）

设格子中心为 `c`，POI 集合为 `P`：

- **可达性**：`access = min(100, Σ w_t · exp(-d/450)) · 55`
  `d` 为 `c` 到第 `t` 类 POI 的距离(米)，`w` = 公园 1.0 / 地铁 1.2 / 商铺 0.9 / 学校 0.7 / 医院 0.8，仅计入 1400m 内。
- **吸引力**：`attr = min(100, 800m 内覆盖的设施类型数 / 5 × 100)`。
- **连通性**：`conn = clamp(20 + 60·noise(c) + 10·(1 − min(1, 到中心距离/1500)), 0, 100)`。
- **舒适性**：`comfort = clamp(90 − 坡度°×4 − (1−noise₂)×20 + 公园附近绿荫, 0, 100)`。
- **安全性**：`safety = clamp(95 − 40·noise₃, 0, 100)`（模拟主干道附近偏低）。

其中 `noise` 是 `(sin + cos 组合 + 4) / 8` 的平滑伪随机，保证相邻格相近、整片有起伏。

---

## 5. 怎么用（交互说明）

| 操作 | 效果 |
|------|------|
| 点击地图任意处 | 以该点为中心生成等时圈（蓝色高亮 + 中心点标记） |
| 点击某个格子 | 弹窗显示 5 维拆解与综合分、模拟坡度 |
| 拖动「最大步行时间」 | 改变等时圈半径（5–20 分钟） |
| 拖动「最大可接受坡度」 | 坡度超阈值的格子被排除出等时圈 |
| 勾选设施类型 | 过滤地图上显示的 POI |
| 图层开关 | 显示/隐藏 热力图 / 等时圈 / POI / 网格边界 |
| 「清除等时圈 / 重置」 | 清空高亮与标记 |

---

## 6. 技术栈

- **地图渲染**：[MapLibre GL JS](https://maplibre.org/)（开源、无需 token）
- **底图**：CARTO Positron 浅色栅格瓦片（© OpenStreetMap contributors © CARTO）
- **数据**：纯前端模拟，GeoJSON 网格，无后端
- **部署**：GitHub Pages（单文件 `index.html` 直接托管）

---

## 7. 本地运行

方式一（最简单）：直接用浏览器打开 `index.html`。
方式二（本地服务器，推荐）：

```bash
# 在仓库目录下
python3 -m http.server 8000
# 浏览器访问 http://localhost:8000
```

> 需要联网以加载 MapLibre CDN 与 CARTO 底图瓦片。

---

## 8. 已知局限

- 距离是直线距离，不是真实路网步行距离。
- 坡度 / 安全是噪声模拟，不是真实 DEM 与事故数据。
- 没有后端，刷新即重算；真实项目应接 PostGIS + OSRM / Turf 等服务。
- 权重是拍定的，真实项目应由居民调研或文献确定。

---

## 9. 下一步

- 接真实数据（OSM 路网 + DEM + POI）替换模拟层。
- 等时圈改用真实路网（Turf.js / OSRM）。
- 增加「居民视角 vs 规划者视角」两种入口与可配置权重。
- 增加街区级改进建议（哪片缺什么设施、坡度问题在哪）。

---

## 9.1 子站：火车站 2km 步行友好专题（`stations/`）

对「有火车站的城市」逐一做站周 2km 步行友好专题，演示「静态预计算、按需加载」架构。

- 在线：https://wadesha.github.io/walkable-map/stations/
- 17 个真实坐标演示站（见 `stations/build_station.py` 的 `STATIONS` 字典，覆盖中/日/韩/俄/德/法/英/美）。其中**全部已接入真实数据**（北京南站为首个端到端打通的锚站）。
- 真实数据管线 `stations/build_station.py`（纯 Python 标准库，无需安装依赖）：Overpass 拉 OSM 路网 + POI + 建筑 + 绿地，Open-Meteo 拉 DEM 算坡度，构建步行图后用 Dijkstra 计算到各类 POI 的真实步行距离；输出 `stations/data/<id>.json`。
- 子站优先 `fetch('data/<id>.json')` 加载真实/预计算数据，缺失则回退模拟——因此总站点数不影响单次访问内存。
- 生产级扩展：百万级站点改用 PMTiles / 矢量瓦片 + 分片对象存储，网页只加载瓦片即可秒开。
- **零依赖静态图（方案 C）**：`stations/render_static.py` 把预计算数据渲染成纯 SVG 图片（`stations/static/beijing.svg` + `beijing.html`），无 MapLibre / 瓦片 / JS / POI，国内绝对打得开。决策背景见第 11 节。
- **完整技术参考与复现手册见第 12 节**（含文件职责、参数表、新增/重渲/补算命令、数据 schema、部署与坑）——后续任何更新都先读这一节。

## 10. 说明

本仓库为**原型 / 演示**用途，步行友好数据除已标注的「北京南站真实数据」外均为程序模拟，请勿用于任何真实决策。
底图版权归 OpenStreetMap 与 CARTO 所有。

---

## 11. 需求演进与方案决策记录（walkable-map）

> 需求在迭代中逐步收敛，记录于此便于后续若改变方案时回溯上下文。

### 11.1 用户诉求演进
- 初版：做可交互原型，思考「怎么定义 / 组织 / 展示适合步行的区域」，加大量解释说明，模拟数据即可，部署 GitHub Pages。
- 子站：对有火车站的全球城市逐一做「站周 2km」步行友好专题；认可「数据写死 / 静态化」以省资源，承认百万级是巨大工程，允许先模拟演示。
- 真实管线：落地北京南站真实数据端到端（OSM 路网 + POI + DEM 坡度）。
- 交互修复：子站因 CARTO 底图瓦片阻塞 MapLibre `load` 事件导致点击无反应，已改为 `styledata` + 轮询解耦底图。
- **需求收敛（关键）**：用户明确表示——不在意从车站出发的指向性路线 / 等时圈，只需要「好走」本身；并进一步确认**甚至不需要 POI**，倾向「静态图片 / 零依赖」以省资源、减少依赖。

### 11.2 已确认的需求（拍板）
1. 展示目标是「哪里好走、哪里不好走」的**静态标注**，不是导航 / 路线规划。
2. **不要等时圈、不要从车站出发的指向路线、不要步行时间 / 坡度筛选器**。
3. **不需要 POI**（设施点）。「好走度」应剥离 POI 维度，只看街道 / 区域本身。
4. 倾向**零运行时依赖**：静态图片（SVG）优先，去掉 MapLibre / 底图瓦片 / JS 这类国内易失效的依赖。

### 11.3 方案对比
| 方案 | 运行时依赖 | 交互 | 国内可用性 | 说明 |
|------|-----------|------|-----------|------|
| A 现状（交互地图） | MapLibre + CARTO + JSON | 点击明细 / 街道 | 弱（2 个 CDN 易墙） | 最花哨，依赖最多 |
| B 本地内置地图库 | 仅本地 JS（去 CARTO） | 同上 | 较强 | 仍有 JS 库，需打包库文件 |
| **C 静态 SVG/PNG（已选）** | **零** | **无（纯图）** | **最强** | 后台预渲染，网页只放 `<img>`；无 JS / 无地图库 / 无瓦片 / 无 POI |
| D PMTiles / 矢量瓦片 | 地图渲染器 | 有 | 中 | 为百万级站点规模准备，仍要渲染器 |

### 11.4 当前选定：C（零依赖静态图）
- 交付：`stations/render_static.py`（离线渲染脚本，可复用到任意站）+ `stations/static/beijing.svg`（图片本体）+ `stations/static/beijing.html`（零 JS 预览页）。
- 计算全部在后台完成：街区「好走度」用**无 POI 重加权**（可达 / 连通 / 舒适 / 安全，权重和 = 1）；街道按真实 `walk`（路型 + 坡度 + 离主干道，与 POI 无关）着色。
- 运行时：零算力、零外部请求，国内绝对打得开。
- 预览：https://wadesha.github.io/walkable-map/stations/static/beijing.html

### 11.5 后续若变更方案
- 若想恢复交互但更稳：走 B（本地内置 MapLibre，底图改用国内源如高德 / 天地图，需 key）。
- 若要做百万级全球站点：走 D（PMTiles + 分片对象存储），仍保持「后台预计算、按需加载」。
- 若「好走度」想重新纳入某维度：改 `render_static.py` 的 `W` 权重即可，无需重跑管线；若需真实步行距离维度，改 `build_station.py` 重算 `beijing.json`。
- 若需要 POI 但只想静态展示：在 `render_static.py` 中加回 POI 图层（当前刻意省略）。

### 11.6 当前后台批处理（自主执行）
- 目标：对我们「指定的一组火车站区域」逐一用真实数据算出「友好区域」，逐步渲染零依赖静态图并上传展示。
- 指定区域：`build_station.STATIONS`（以北京南站为锚，扩展到 16 个主要高铁站：上海虹桥/广州南/深圳北/成都东/武汉/西安北/南京南/杭州东/郑州东/东京/首尔/巴黎北/国王十字/柏林中央/纽约宾州/莫斯科）。
- 友好区域定义：无 POI 重加权好走度 ≥ 65 的相邻格子，连通聚类成片；输出外轮廓 `edges` 与格数，静态图以绿色粗线勾边 + 「友好区·N格」标注。
- 管线：`build_station.compute_station(id)`（含聚类）→ `render_static.render(id)`（写 svg/html）→ `batch_stations.py` 遍历上传（Contents API）+ 重建 `stations/static/index.html` 画廊页。支持断点续跑、Overpass 多端点容错重试、站间慢速暂停、失败跳过。
- 前台有限展示：画廊页 https://wadesha.github.io/walkable-map/stations/static/ （列出各站静态图链接 + 友好区域统计），后台持续补充。

### 11.7 底图演进：纯图片 → 烤入 OSM 建筑/绿地底图（2026-08-04 晚）
- 用户反馈：纯图片无底图「并非最理想」——色块/街道悬空、缺地理参照。
- 决策：**不回到 CARTO 在线瓦片**（国内易失效），而是把已下载的 OSM 全量路网 + 新增抓取的**建筑 footprint + 绿地**离线烤入 SVG 底层作地理参照。
- 实现：`build_station.py` 的 Overpass 查询新增 `way["building"]`（及 `leisure=park/garden` 绿地），存为 `buildings`/`greens` FeatureCollection；`render_static.py` 在最底层画绿地（浅绿）→ 建筑块（浅灰）→ 2km 研究圈（虚线），其上叠街区好走度半透明底色（透明度 0.30 透出肌理）+ 街道好走度着色 + 友好区轮廓。
- 仍满足：零运行时依赖、无 MapLibre、无在线瓦片、无 JS、无 POI；只是图片本身更"像真地方"。
- 代价：SVG 体积变大（北京 475KB→972KB，主要因建筑多边形）；对超密城市（东京/伦敦）建筑数可达数万，需注意体积。

### 11.8 总览导航页 + 站名标注（2026-08-04 晚）
- 用户两点诉求：(1) 详细图是否可加少量地名文字（确认可行）；(2) 先做一个「大地图动态化粗粒度网格」总览，点城市进入相应精细内容。
- 站名标注：`render_static.py` 在车站坐标处加 ★ + 站名（`data["name"]`），纯矢量文字、零依赖。路名/片区名可再加（需管线抓取 OSM `name` 字段，待用户确认范围）。
- 总览页 `stations/overview.html`（**零依赖**：无 MapLibre / 无在线瓦片 / 无 JS 地图库，仅原生 SVG + fetch `cities.json`）：
  - 等距投影世界网格（经纬网 + 赤道/本初子午线强调）作粗粒度底；
  - 17 城按「均值好走度」红→黄→绿着色，可点标记 + 右侧城市列表，点城市 → `window.open("static/<id>.html")` 进入该城静态精细图；
  - 未算完城市显示灰色"待计算"，点击提示计算中。
- 数据驱动：`gen_cities.py` 扫 `data/*.json` 产出 `stations/cities.json`（每城 score/friendly/hasDetail），始终含全部 17 城；后台每算完一站可重跑刷新。
- 入口：https://wadesha.github.io/walkable-map/stations/overview.html （画廊页 https://wadesha.github.io/walkable-map/stations/static/ 仍保留，作逐站列表）。

### 11.9 地名标注收敛：友好区内地标（≤3）+ `--render-only` 复用（2026-08-04 深夜）
- 用户收敛：详细图的地名标注**不需要"离车站最近"的地标**，只抓**友好区内**有真实名称的有效地名（排除站名自身），**最多 3 个**即可；并继续推进其余站的批处理。
- 实现：`render_static.py` 用 `ij_of(lng,lat)` 网格索引与友好区所有格子 `frij` 求交，仅取落在友好格内、有真实名称、且不等于站名的 POI，取前 3 个画 `▴名称`；同时保留最多 6 条高等级主干道路名（中点）标注、以及 ★ 站名。
- `batch_stations.py` 新增 `--render-only` 模式：跳过 Overpass 重算，直接对已有 `data/<id>.json` 用最新 `render_static` 重新渲染 svg/html 并上传、重建画廊。用于「只改渲染、不动数据」的快速迭代（如本次规则变更），避免 12 站重复拉取 OSM。
- 坐标精度：站点中心已按 OSM `railway=station` 节点/way 名称匹配回正（如北京南站回正到 116.3733, 39.8641，与真实站吻合），非 GCJ-02（OSM 本即 WGS-84）。

### 11.10 总览页重做：烤入大陆底图 + 东亚放大插图（2026-08-04 深夜）
- 用户反馈初版总览「城市重叠、无底图、不如列表」——世界等距投影下东亚 12 城挤在几十像素，既挤又无地理参照。
- 修复：(1) 烤入 Natural Earth 110m 陆地轮廓（69 个简化多边形，~69KB 内联，仍零运行时依赖、无在线瓦片）；(2) 世界图加真实大陆底图 + 经纬网，西方 5 城（莫斯科/柏林/巴黎/伦敦/纽约）分散可展开标注；(3) **东亚 12 城密集区改为独立放大插图**（经度 100–146°、纬度 20–46°，带大陆底图 + 每 5° 经纬网），标签用「按纬度排序 + 贪心纵向防重叠 + 引线」算法，实测 12 标签最小纵向间距 27px、全部落在插图内（无重叠/溢出）；世界图上东亚区用绿色虚线框 + 「见右图放大」提示，并仍画出东亚点（无标注）。(4) 保留右侧城市列表作辅助导航。
- 实现：`stations/overview.html` 重写（内联 `LAND` 常量 + `drawLand/drawGrid/placeLabels/drawDots` + 世界图/插图双投影），底图源 `stations/world_land.json`（构建期从 NE 110m 简化、舍入到 0.1°、丢弃 <2°² 小岛）。已推送 overview.html(f0be5cae) + world_land.json(716ed1bb)。
- 现状：cities.json 初版 12 城已算分+有精细图，5 城（莫斯科/柏林/巴黎/纽约/伦敦）由后台批处理 `gntyc8` 计算中。

---

## 12. 火车站站周 2km 步行友好专题 · 完整技术参考与复现手册（stations/）

> 本节能让任何人（包括未来的你）在**不翻聊天记录**的情况下，看懂实现、改参数、加城市、重渲、重新部署。
> 代码为准：本节能直接对应 `stations/` 下四个脚本 + 两个网页 + 数据文件。所有数值都来自源码（已逐行核对）。

### 12.1 架构总览

三条互相独立、可单独复用的产物，构成本专题：

| 产物 | 文件 | 运行时依赖 | 用途 |
|------|------|-----------|------|
| **单站精细静态图（方案 C）** | `static/<id>.svg` + `static/<id>.html` | **零**（纯矢量 `<img>`） | 每站一张"好走度"地图，国内绝对打得开 |
| **世界总览页** | `overview.html`（读 `cities.json`） | 仅原生 SVG + 一次 `fetch` | 粗粒度索引：点城市进对应精细图 |
| **逐站画廊** | `static/index.html` | 零 | 列出所有已算站的静态图链接 |

数据全部**后台离线预计算**，网页端不跑任何算法。完整链路：

```
build_station.py  --compute-->  data/<id>.json  --render-->  static/<id>.svg/.html
        │                                                          │
        │ (17 站遍历)                                              └──> batch_stations.py 上传 + 重建画廊
        ▼
gen_cities.py  --聚合-->  cities.json  <--fetch--  overview.html
```

坐标系统一约定：**OSM = WGS-84**（不是 GCJ-02）。所以直接把 OSM 经纬度喂给 SVG/总览页即可，无需偏移。

### 12.2 文件清单（每个文件职责）

| 文件 | 行数 | 职责 | 何时改 |
|------|------|------|--------|
| `stations/build_station.py` | ~454 | 计算管线：拉 OSM + DEM → 算格分/街道/友好区 → 写 `data/<id>.json` | 改评分公式、聚类阈值、新增车站、换数据源 |
| `stations/render_static.py` | ~295 | 渲染器：读 `data/<id>.json` → 画分层 SVG → 写 `static/<id>.svg/.html` | 改配色、图层顺序、标注规则、画布尺寸 |
| `stations/batch_stations.py` | ~169 | 批处理：遍历站→compute→render→**上传 GitHub（Contents API）**→重建画廊 | 改上传/画廊逻辑、暂停节奏、失败策略 |
| `stations/gen_cities.py` | ~48 | 扫 `data/*.json` → 生成总览用的 `cities.json` | 改总览聚合口径（均值/友好格统计）；基本不用动 |
| `stations/overview.html` | ~大 | 零依赖世界总览：内联大陆底图 + 东亚放大插图 + 点城进精细图 | 改总览范围、插图投影、标签防重叠算法 |
| `stations/world_land.json` | ~69KB | 总览底图源：Natural Earth 110m 陆地（69 多边形，0.1° 舍入，丢 <2°² 小岛） | 换更精细底图时重生成 |
| `stations/cities.json` | — | 总览数据：每城 `{id,city,country,name,lng,lat,score,friendly,hasDetail}` | **每算完/新增一站后必须重跑 `gen_cities.py`** |
| `stations/data/<id>.json` | 每站 | 单站预计算全量数据（见 §12.8 schema） | 由 `build_station.py` 产出，勿手改 |
| `stations/static/<id>.svg`/`.html` | 每站 | 单站静态图（方案 C） | 由 `render_static.py` 产出 |
| `stations/static/index.html` | — | 画廊页（列出所有已算站 + 总览入口链接） | 由 `batch_stations.build_gallery()` 重建 |

> 运行环境：仓库内已配 managed Python 3.13.12。本地跑用
> `/Users/wade/.workbuddy/binaries/python/versions/3.13.12/bin/python3 <脚本>`，
> 或直接 `python3`（系统 3.9 也够，本专题只用标准库）。**无需 pip 安装任何包。**

### 12.3 计算管线 `build_station.py`（逐步 + 关键参数）

入口：`compute_station(sid)` → 返回 `out` 字典并写 `data/<id>.json`。打印带步骤号 `[1/5]…[5/5]`。

**关键常量（源码顶部，改这里调全局）：**

| 常量 | 值 | 含义 |
|------|----|------|
| `QUERY_R_M` | `2200` | Overpass 拉取半径（覆盖 2km + 余量） |
| `GRID_HALF` | `1000` | 专题半径 = 2km |
| `CELL_M` | `160` | 单格边长（米） |
| `N` | `13` | 每边格数 → **13×13 = 169 格** |
| `FRIENDLY_THRESH` | `65` | 友好区聚类阈值（无 POI 重加权好走度 ≥ 65 的相邻格成片） |
| `W_ACCESS` | `park:1.0, metro:1.2, shop:0.9, school:0.7, hospital:0.8` | 可达性按 POI 类型加权 |
| `W_PFOI` | `access:0.30/0.80, conn:0.18/0.80, comfort:0.17/0.80, safety:0.15/0.80` | 无 POI 的"好走度"重加权（四项和 = 1.0） |

**综合分公式（含 POI 的 5 维版，用于格子的 `score` 字段）：**
```
score = 0.30·access + 0.18·conn + 0.17·comfort + 0.15·safety + 0.20·attr
```

**逐步流程：**

1. **`[1/5]` Overpass 拉取**（`overpass(q)` 函数：5 个端点 × 各 3 次重试，主节点 `overpass-api.de` 常 504）。
   查询一次性取：`way["highway"]`、`node/way["amenity"|"shop"|"leisure=park|garden"|"railway=station|halt"]`、`way["building"]`。
   数据分类为 `ways / pois / buildings / greens`。
   - **POI 命名**：`name = tags["name"] or tags["name:en"] or 类型名`（有真实名才非空）。
   - **车站回正（重要坑，见 §12.13）**：收集完元素后，遍历 `railway ∈ {station,halt,stop,tram_stop,subway_station}` 的节点/way，取其与 `STATIONS` 硬编码中心的 haversine 距离；若 `STATIONS` 里的 `name` 出现在该要素的 `name` 中则**距离减 5000m 强烈优先**，取最近者为真实中心 `lng0,lat0`。这避免了硬编码坐标漂移（北京南曾偏 700m）。
2. **`[2/5]` 构建步行图 + 高程**：`build_graph(ways)` 自写邻接表（跳过 `motorway/motorway_link`），节点 key 为 `(round(lon,5),round(lat,5))`；`dijkstra` 自写堆优化最短路。`elev_batch` 调用 Open-Meteo Elevation（每批 ≤100 点，自动分批）。主干道集合 = `trunk/trunk_link/primary/primary_link`（用于算"离主干道距离"）。
3. **`[3/5]` 逐格计算**：对 169 格，每格中心取最近图节点跑 Dijkstra，得到到各类 POI 的真实步行距离：
   - `access = min(100, Σ W_ACCESS[cat]·exp(-d/450)·55)`，仅计 d<1400m；
   - `attr = min(100, 800m 内覆盖的设施类型数 / 5 × 100)`；
   - `conn_raw` = 300m 内"交叉口密度"（邻接度 ≥3 的节点数）；
   - `slope` = 用格四角 DEM 算梯度 → 角度；
   - `safe_raw` = 到最近主干道距离。
4. **`[4/5]` 合成分数 + GeoJSON**：`conn = 站内 min-max 归一(conn_raw)`；`comfort = 100 - 站内 min-max 归一(slope)`；`safety = 站内 min-max 归一(safe_raw)`。写每格 Feature（含 5 维子分 + 坡度）。
   - **`[4.5/5]` 聚类友好区域**：取 `poi_free_score(cell) ≥ 65` 的格 → BFS 四邻连通成片（<2 格的丢弃）→ 输出每片 `size / score_avg / centroid / cells[[i,j]…] / edges`（外轮廓线段：与邻片共享边不画）。
   - **`[4.8/5]` 街道好走度**：对每条 `way`，`road_walk = 0.40·base + 0.35·comfort + 0.25·safety`，其中 `base` 来自 `ROAD_BASE` 字典（footway:92 → trunk:30），`comfort=max(0,100-坡度°×6)`，`safety=min(100, 离主干道/300×100)`（>9999 取 80）。路名抓 `name/name:en`。
5. **`[5/5]` 写出**：`data/<id>.json`（schema 见 §12.8）。

> 单次计算耗时主要取决于 Overpass 响应（国外城市常 >60s 甚至超时失败 → 见 §12.11 补算策略）。

### 12.4 静态渲染 `render_static.py`（图层与标注规则）

入口：`render_static.render(sid)` → 写 `static/<id>.svg` + `static/<id>.html`。全部用本地米制投影 `to_m(lng,lat)=( (lng-lng0)·111320·cos(lat0r), (lat-lat0)·111320 )`，再等比缩放进画布。

**画布与配色：**
- 画布 `1200×1260`，外边距 `M=40`，顶部标题区 `Htop=72`、底部图例区 `Hbot=140`；等比 `scale=min(usableW/spanx, usableH/spany)` 居中。
- 街区分色 `STOPS = (0,(215,48,39) 红) → (50,(254,224,139) 黄) → (100,(26,152,80) 绿)`（红=差，绿=优）。
- 街区"好走度"权重 `W` 与管线 `W_PFOI` 一致（access/conn/comfort/safety 四项和=1）。

**图层顺序（从底到顶，决定视觉层次 — 改渲染先看清这个）：**

| # | 图层 | 样式 | 备注 |
|---|------|------|------|
| 1 | 街区好走度底色 | `fill=color(sc)`，`fill-opacity=0.28` + 白描边 | 沉在最底，透出肌理 |
| 2 | 绿地（烤入 OSM `leisure=park/garden`） | `#bfe2ac` | 地理参照 |
| 3 | 建筑（烤入 OSM `way["building"]`） | `#c2cad6`，`fill-opacity=0.92` | **`BLD_CAP=8000`**：超密城市（东京/伦敦）按面积取前 8000 防 SVG 爆炸 |
| 4 | 街道（按 `walk` 着色） | 线宽 `0.7 + walk/100·1.5` | 最上保证可见 |
| 5 | 2km 研究圈 | 虚线 `#9aa3ad`，`stroke-dasharray="5 4"` | 最上层便于看边界 |
| 6 | 友好区外轮廓 + 标注 | 绿线 `#0f7a3d` 宽 3.2 + 文字 `友好区·N格` | 无成片时退回 top3 单格标"步行友好" |
| 7 | 站名 | ★ + `data["name"]`（黑字白描边） | 车站坐标处 |
| 8 | **地名标注** | 见下方规则 | 文字 `#3b4252` 白描边 |
| 9 | 图例 | 渐变条 + 统计文字 | 底部 |

**第 8 层"地名标注"收敛后的最终规则（用户拍板）：**
- **主干道名**：仅 `primary/primary_link/secondary/secondary_link/trunk/trunk_link/tertiary/tertiary_link` 等级，取**线段中点**，**最多 6 条**，有 `name` 才标。
- **友好区内地标**：用网格索引 `ij_of(lng,lat)` 与友好区所有格 `frij` 求交，**仅取落在友好格内、有真实名称、且 ≠ 站名** 的 POI，**最多 3 个**，画 `▴名称`。**不再取"离车站最近"的地标**（这是早期版本的错误理解，已改）。
- 站名本身永远标（第 7 层），不计入地标 3 个上限。

> 改标注规则只动 `render_static.py` 的第 8 层逻辑，然后走 §12.10 的 `--render-only` 重渲即可，无需重算数据。

### 12.5 批处理与上传 `batch_stations.py`（命令与模式）

命令行：`python3 batch_stations.py [--force] [--render-only] [id1 id2 …]`
- 不传 id → 遍历 `STATIONS` 全部 17 站。
- 默认 `pause=12` 秒（站间慢速，避免 Overpass 限流）。

| 模式 | 行为 | 何时用 |
|------|------|--------|
| **默认**（无 flag） | 若 `data/<id>.json` 已存在**且含 `friendly_areas`** → 跳过；否则 compute→render→upload→重建画廊 | 增量补算剩余城市 |
| **`--force`** | 无视已有数据，强制重算+重渲+上传 | 改了 `build_station.py` 评分/聚类逻辑后全量刷新 |
| **`--render-only`** | 跳过 Overpass，直接对已存在 `data/<id>.json` 用**最新** `render_static` 重渲 svg/html + 上传 + 重建画廊 | **只改了渲染/标注规则**（如 §12.4 地标规则），避免 17 站重复拉 OSM |

**每站上传四件套**（Contents API，PUT）：`data/<id>.json`、`static/<id>.svg`、`static/<id>.html`、`static/index.html`（画廊，每站重建一次）。
**Token 取法**（安全硬规则）：从 `/Users/wade/.workbuddy/MEMORY.md` 用正则 `ghp_[A-Za-z0-9]+` 取 **`[0]`**（无捕获组，取错会 401）；仅放 `Authorization: token <TOKEN>` 头，**绝不写进任何会被提交的文件 / 不回显 / 不进 git 历史**。详见用户级 `MEMORY.md`。

**画廊** `build_gallery()`：扫 `data/*.json` 列出每站（城市·站名·国家·街区数·友好区片数/格数），并加两个入口链接：返回交互专题 `../stations/`、进入总览 `../overview.html`。

> 后台长跑建议用 `run_in_background`：计算慢、可中断；失败城市自动跳过不崩。注意：**改了 `render_static.py` 后，必须重启批处理进程**——旧进程内存里是旧渲染器（曾因此渲出淡底图/旧地标，见 §12.13）。

### 12.6 总览数据 `gen_cities.py` + `cities.json` 结构

`gen_cities.py` 扫 `data/*.json`，**始终输出全部 17 站**（来自 `STATIONS` 字典），有数据的标 `score/friendly/hasDetail`：
- `score` = 该站所有格 `properties.score` 的**均值**（1 位小数）。
- `friendly` = 所有友好区 `size` 之和（格数）。
- `hasDetail` = `static/<id>.svg` 是否存在。

**`cities.json` schema**：
```json
{
  "generated": "2026-08-04",
  "total": 17,
  "cities": [
    {"id":"beijing","city":"北京","country":"中国","name":"北京南站",
     "lng":116.3782,"lat":39.8714,"score":62.9,"friendly":71,"hasDetail":true},
    {"id":"paris","city":"巴黎","country":"法国","name":"巴黎北站",
     "lng":2.355,"lat":48.88,"score":null,"friendly":0,"hasDetail":false}
  ]
}
```
- `score=null` + `hasDetail=false` → 总览页显示**灰色"待计算"**，点击提示计算中。
- **每次算完/新增一站后，必须重跑 `python3 gen_cities.py` 并上传 `cities.json`**，否则总览页不会刷新配色（总览页运行时 `fetch('cities.json')`）。

### 12.7 总览页 `overview.html`（架构 + 投影 + 插图）

**零运行时依赖**：无 MapLibre、无在线瓦片、无 JS 地图库；仅原生 `<svg>` + 一次 `fetch('cities.json')`。大陆底图**烤进 HTML 内联**（69 多边形，~69KB），不联网。

**世界图投影（等距圆柱）：** `x=(lng+180)/360·W`，`y=(90-lat)/180·H`。画经纬网 + 赤道/本初子午线强调。

**东亚放大插图（解决"城市重叠"的核心）：** 东亚 12 城在世界图里天然挤成一团，因此单拆一张插图：
- 投影范围 `IX0=100, IX1=146, IY0=20, IY1=46`（经度 100–146°、纬度 20–46°），插图画布 `460×420`，带大陆底图 + 每 5° 经纬网。
- 标签防重叠算法：12 城按**纬度排序** → 从上到下贪心放置，`minGap=15px` 纵向防叠 → **实测最小纵向间距 27px、全部落在插图内**（无重叠/溢出）；靠右密集的城标签甩向左（引线）。
- 世界图上东亚区用**绿色虚线框 + "见右图放大"**，并仍画出东亚点（无标注），引导用户看插图。
- 西方 5 城（莫斯科/柏林/巴黎/伦敦/纽约）在世界图上天然分散，直接标注。
- 右侧保留**城市列表**作辅助导航（按国家/城市排序）。
- 点任意标记/列表项 → `window.open("static/<id>.html")` 进入该城精细静态图；待算城点击给提示。

**底图源**：`world_land.json`（构建期从 Natural Earth 110m 简化、坐标舍入 0.1°、丢弃面积 <2°² 小岛）。若要更精细底图，重生成该文件并注入 `overview.html` 的 `LAND` 常量（注入脚本见 §12.13）。

### 12.8 数据文件 schema（`data/<id>.json`）

```jsonc
{
  "id":"beijing","name":"北京南站","city":"北京","country":"中国",
  "center":[116.3733,39.8641],          // 已由 OSM 回正后的真实车站中心
  "generated":"2026-08-04",
  "source":"OSM Overpass ... + Open-Meteo elevation ...",
  "friendly_threshold":65,
  "cells":{ "type":"FeatureCollection", "features":[        // 169 格
      {"geometry":{"type":"Polygon","coordinates":[[[lng,lat]×5]]},
       "properties":{"center":[lng,lat],"score":63,"access":..,"conn":..,
                      "comfort":..,"safety":..,"attr":..,"slope":1.2}}
  ]},
  "pois":[ {"lng":..,"lat":..,"type":"park|metro|shop|school|hospital","name":"真实名或类型名"} ],
  "roads":{ "type":"FeatureCollection","features":[
      {"geometry":{"type":"LineString","coordinates":[[lng,lat]…]},
       "properties":{"hw":"primary|secondary|…","walk":62,"slope":0.8,"name":"南新华街"}}
  ]},
  "buildings":{ "type":"FeatureCollection","features":[ {"geometry":{"type":"Polygon",...},"properties":{}} ]},
  "greens":{ "type":"FeatureCollection","features":[ {"geometry":{"type":"Polygon",...},"properties":{}} ]},
  "friendly_areas":[ {"size":71,"score_avg":..,"centroid":[lng,lat],
                      "cells":[[i,j]…],"edges":[[[lng,lat],[lng,lat]]…]} ]
}
```
- `render_static.py` 只读这个文件，不依赖任何外部服务。
- 改 `build_station.py` 后**必须重跑管线**（旧 json 不含新字段）。

### 12.9 如何新增一个车站（端到端）

1. 在 `build_station.py` 的 `STATIONS` 字典加一项：
   ```python
   "mycity": {"city":"某市","country":"某国","name":"某站","lng":116.40,"lat":39.90},
   ```
   经纬度填**大致中心即可**——管线会用 OSM `railway=station` 按 `name` 匹配回正到真实车站（见 §12.3 步骤 1），硬编码漂移会被修正。
2. 计算：`python3 build_station.py mycity` → 生成 `data/mycity.json`（看打印的 `[1/5]…[5/5]` 与分数范围/均值）。
3. 渲染预览：`python3 render_static.py mycity` → 生成 `static/mycity.svg/.html`，浏览器打开 `static/mycity.html` 检查配色/标注。
4. 刷新总览聚合：`python3 gen_cities.py`。
5. 上传 + 重建画廊（一次性完成 compute 之外的上传）：`python3 batch_stations.py --force mycity`
   （`--force` 会重算并上传 data/json+svg+html+画廊；若要省一次本地计算也可手动先算好再 `python3 batch_stations.py mycity`，它会检测到已有 json 只做 render+upload）。
6. 推送 `cities.json` 与 `overview.html` 不需单独推——`batch_stations.py` 已上传画廊；但 `cities.json` 需手动推（见 §12.5 上传方式或下方 §12.12）。

### 12.10 如何只改渲染规则后重渲（不重算）

典型场景：改了配色/图层顺序/标注规则（如 §12.4 的"友好区内最多 3 个地标"）。**不要重跑 Overpass**（慢且易失败），用 `--render-only`：

```bash
# 重渲全部 17 站（用最新 render_static.py，已有 data/* 不动）
python3 batch_stations.py --render-only
# 或只重渲部分
python3 batch_stations.py --render-only beijing tokyo seoul
```
该模式跳过 `build_station`，直接 `render_static.render(sid)` → 上传 svg/html → 重建画廊。**记得重跑 `gen_cities.py` 并推 `cities.json`**（若总览需要刷新）。

### 12.11 如何补完待算城市 / 重新计算

- 待算城（如 paris/newyork/london）显示灰色"待计算"，是因为 `data/<id>.json` 不存在（Overpass 拉取超时/被限流失败跳过）。
- 补算：`python3 batch_stations.py --force paris newyork london`（单站重试，失败仍跳过不崩）。可多跑几次，Overpass 不同端点成功率不同。
- 全量重算（改了管线公式后）：`python3 batch_stations.py --force`（遍历全部 17 站，慢，建议后台跑）。
- **重算后必做**：`python3 gen_cities.py` + 推 `cities.json`，否则总览页不更新。

### 12.12 部署与 GitHub Pages / 缓存

- **推送机制**：`batch_stations.upload()` 用 **GitHub Contents API**（`PUT /repos/Wadesha/walkable-map/contents/<path>`）。已存在文件需带 `sha`（先 GET 取）；404 视为新建。
- **站点地址**：
  - 仓库根 `index.html` → `https://wadesha.github.io/walkable-map/`（原型交互页）
  - 总览 → `https://wadesha.github.io/walkable-map/stations/overview.html`
  - 画廊 → `https://wadesha.github.io/walkable-map/stations/static/`
  - 单站 → `https://wadesha.github.io/walkable-map/stations/static/<id>.html`
- **⚠️ Pages CDN 缓存延迟**：提交后新文件可能滞后**数分钟**才在 `wadesha.github.io` 生效。排查"没更新"时：
  1. 先硬刷新（Cmd/Ctrl+Shift+R）；
  2. 用 `raw.githubusercontent.com/Wadesha/walkable-map/main/stations/static/<id>.svg` 直链绕过缓存，确认文件本身已更新；
  3. 若 raw 是最新而 Pages 旧 → 纯属 CDN 传播延迟，等几分钟即可。
- **Token 安全**：绝不在脚本/HTML/commit 里写 token；只从本地 `~/.workbuddy/MEMORY.md` 读取（见 §12.5）。

### 12.13 当前状态与已知坑（fix 记录摘要）

**当前状态（2026-08-05）：** 17 站中 **14 站已算分+有精细图**（北京/上海/广州/深圳/成都/武汉/西安/南京/杭州/郑州/首尔/东京/莫斯科/柏林）；**3 站仍待算**（巴黎/纽约/伦敦，Overpass 拉取失败跳过，总览灰色）。`cities.json` 需在每次算完新站后重跑刷新。

**踩过的坑（改东西前务必看）：**
1. **节点中心漂移**：早期 `STATIONS` 硬编码北京南 `39.8714`，偏真实站 ~700m。根因不是 GCJ-02（OSM 本就是 WGS-84），而是硬编码不准。已在 `build_station` 步骤 1 用 OSM `railway=station` 按 `name` 匹配回正（北京南→116.3733,39.8641）。**新增站只要 `name` 与 OSM 站名能对上，自动回正。**
2. **底图看不见**：建筑色 `#dfe3e8` 过淡 + 被色块蒙层盖住。修复：图层重排（街区色沉底 0.28，建筑/绿地提到上层并加深到 `#c2cad6`/`#bfe2ac`）。
3. **建筑数爆炸**：东京/伦敦建筑数万 → SVG 上 MB。加 `BLD_CAP=8000` 按面积取前 N。
4. **总览城市重叠**：世界等距投影下东亚 12 城挤成团。修复：烤入大陆底图 + 东亚独立放大插图（§12.7）。
5. **批处理用旧渲染器**：改了 `render_static.py` 后，没重启的后台批进程内存里还是旧版 → 渲出旧规则图。→ 任何渲染改动后**必须重启批进程**。
6. **Pages CDN 滞后**：见 §12.12。
7. **地标规则误解**：早期取"离车站最近的地标 5 个"，用户纠正为"**友好区内**有效地名、最多 3 个"。改动在 `render_static.py` 第 8 层（用 `ij_of` 与 `frij` 求交），见 §12.4。
8. **`--render-only` 复用**：为避免"只改标注却重拉 17 站 OSM"，加了该模式（§12.10）。

**`world_land.json` 重新生成（如需更精细底图）：**
```python
# 拉 Natural Earth 110m land → 舍入 0.1° → 丢 <2°² 小岛 → 写 world_land.json
# 再把该 JSON 注入 overview.html 的 __LAND__ 占位（或用字符串替换 LAND 常量）
```

---

> 第 11 节是"需求演进与方案决策"的历史记录（A/B/C/D 方案对比、为何选零依赖方案 C）；本第 12 节是"现在怎么动手改"的操作手册。两者配合即可无缝接手此专题的任何后续迭代。
