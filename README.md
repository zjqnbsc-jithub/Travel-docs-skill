# Travel Docs Skill

> **仓库简介**
>
> 基于实际路径以及途径地天气预报的旅游路线规划技能。输出包括：给旅客自己使用的含详细信息的行程地图、每日降雨与行程合成图、旅客手册，以及给司机或导游的行程地图和司机日程表。
>
> **Description (English)**
>
> Travel route planning skill based on real road routes and the weather forecast for each stop along the way. Outputs include: a detailed itinerary map for the travellers themselves, a daily rainfall-and-itinerary composite map, a guest handbook, plus a route-only itinerary map and a driver's schedule for the driver or guide.

> 面向**全球任何目的地、任意出行方式**（自驾、自由行、铁路、渡轮、包车或混合）的多日旅行规划 Agent Skill，
> 把一次规划固化成**固定 6 件交付物**：两张地图、一份天气 PDF、三份 Excel。
> 路线、里程、坐标、天气结论全部来自真实数据源（Nominatim / OSRM / 目的地气象机构官方图），不靠记忆、不靠估算。

本仓库是 `Travel Docs` skill 的整合版：**与原 skill 保持同一思路与同一 6 件契约，唯一的核心升级在天气图**——当目的地附近没有小区域天气图、只能用大区域图（如全国天气图）时，按三级阶梯出图：

**小区域节选 → 定位底 + 官方采样填色**（详见下文「天气图三级阶梯」）。

## 适用范围

- **地域**：全球任何地方——流程与脚本不绑定国家（坐标用 Nominatim、路网用 OSRM、底图用 Natural Earth，均为全球服务；天气源按 `weather.md` 的来源原则取目的地气象机构官方图）。
- **出行方式**：自驾、自由行、铁路、渡轮、包车及其组合——Step 0 先确认出行方式与体力限制，再规划。
- **产出**：无论何种方式，交付物恒为同样 6 件、同样文件名、同样表结构（格式是契约）。

## 6 件交付物

| # | 文件 | 受众 |
|---|------|------|
| 1 | `plan-{slug}-final.png` 游客版地图（路线 + 逐日面板 + 预算） | 游客 |
| 2 | `map-{slug}-route-only.png` 路线版地图（无日期/价格/个人信息） | 司机 / 第三方 |
| 3 | `weather_route_{start}_to_{end}.pdf` 每日一页官方预报图叠路线 | 游客 |
| 4 | `司机行程单-Driver-Schedule-{date_suffix}.xlsx` | 司机 |
| 5 | `游客手册-{date_suffix}.xlsx`（8 个工作表） | 游客 |
| 6 | `行程中英对照-{date_suffix}.xlsx` | 司机 + 游客 |

**恰好 6 个文件**是契约：缺一个包不完整，多一个说明私造了格式。

## 天气图三级阶梯（本 skill 的核心升级）

**问题**：官方预报图常常只有大区域版（如全国 24–168h 降水图），目的地在图上只占 ~20 像素——裁剪放大是锯齿马赛克，看不清就等于猜。

**解法**（`skill/references/weather.md` → *Legibility ladder*，逐级上探，能停则停）：

| 级 | 底图 | 适用条件 | 出处要求 |
|---|------|---------|---------|
| 1 | 官方图原样 | 目的地清晰可读（≳40px） | 图本身 |
| 2 | **小区域节选** | 裁剪+放大后海岸线/图例仍可辨 | 横幅注明节选 + 原图 URL/起报时次 |
| 3 | **定位底 + 官方采样填色** | 节选也糊（全国图上目的地 ~20px） | 横幅注明采样 + 完整出处链写入 `weather._note` |

第 3 级的做法（源自本案例）：

- 底图换成行程区域的**矢量定位图**（Natural Earth 数据，如 `118.8–122.2E / 30.2–32.2N`，1600×1000，目的地与参照城市清晰可辨）；
- 陆面填色 = **官方大区域图在该点实际采到的色值**（如白 `#FFFFFF`=0mm、浅绿 `#A6EA90`=0-10mm，取自官方图例，不自造颜色）；
- 图上保留官方图例 + 一行采样说明，横幅保留 model/起报时次/时区换算/红线说明，`weather._note` 记原图 URL、检索时间与采样方法；
- **verdict 不随级变**——每一级都用同一套逐像素采样，只换底图；出处链一句话说不清，就是降级过头了。

**禁止**：把 20px 区域插值放大当图用；凭记忆或天气 App 图标配色。

## 核心原则（原 skill 6 条 + 天气 1 条）

1. 坐标必须 geocode 核对，绝不凭记忆写经纬度
2. 里程必须 OSRM 实算，绝不直线距离拍脑袋（误差 40%+）
3. 价格必须检索并标注估算日期与汇率
4. 规划前先问体力/步行限制
5. 天气结论必须逐像素采样官方图，不得凭记忆或天气 App 图标做 go/no-go
6. 司机件永远不含预算与乘客个人信息
7. **（新增）目的地在唯一可用的图上读不清 → 走三级阶梯，不放大糊图、不猜色**

## 目录结构

```
.
├── README.md                 # 本文件
├── CHANGELOG.md              # 版本号更新记录
├── VERSION                   # 当前版本号
├── LICENSE                   # MIT
├── .gitignore
├── docs/
│   ├── lessons-learned.md    # 案例复盘：问题 → 解决方法（含 skill 范围外的过程记录）
│   └── case-taihu.md         # 案例：6 天环太湖自驾
└── skill/                    # Skill 本体（可直接放入 Agent skills 目录）
    ├── SKILL.md              # 主流程：6+1 条非协商项 + 7 步工作流（含天气阶梯）
    ├── references/
    │   ├── deliverables.md   # 6 件契约：文件名/工作表/样式/版本纪律
    │   ├── maps.md           # 制图规范 + 核单
    │   ├── weather.md        # 官方图采样 + ★Legibility ladder 三级阶梯
    │   └── example.md        # 匿名参考包（仅结构）
    └── scripts/
        ├── geocode.py        # Nominatim 正/反查 + --check 全表核对（全球）
        ├── route.py          # OSRM 里程/时长/几何（全球路网）
        ├── fetch_basemap.py  # Natural Earth 底图（全球）
        ├── build_maps.py     # 两张 PNG 地图
        ├── mk_xlsx.py        # 三份 Excel
        ├── build_weather_pdf.py  # 天气图标注 + 打包 PDF
        └── trip.example.json # 带注释的配置模板
```

> `skill/` 中除天气阶梯相关改动外，与原 skill 保持一致（详见 CHANGELOG）。

## 快速开始

依赖：Python 3 + `matplotlib` `openpyxl` `pillow`；网络可访问 OSRM、Nominatim、Natural Earth 镜像。

```bash
# 1. 复制模板为 trip.json，按 _note 填好（坐标来自 geocode）
python skill/scripts/geocode.py --check trip.json

# 2. 底图 + 真实路网几何
python skill/scripts/fetch_basemap.py "China"   # 任意国家英文名
python skill/scripts/route.py trip.json

# 3. 生成 6 件（顺序固定）
python skill/scripts/build_maps.py trip.json        # 文件 1 + 2
python skill/scripts/mk_xlsx.py trip.json           # 文件 4 + 5 + 6
python skill/scripts/build_weather_pdf.py trip.json # 文件 3，最后
```

Windows 控制台如遇中文输出报 `cp1252 UnicodeEncodeError`，先设 `$env:PYTHONIOENCODING='utf-8'`、`$env:PYTHONUTF8='1'`、`chcp 65001`。

## 版本

当前版本见 [`VERSION`](VERSION)，更新记录见 [`CHANGELOG.md`](CHANGELOG.md)。

## 许可

[MIT](LICENSE)
