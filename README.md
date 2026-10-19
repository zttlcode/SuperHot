# SuperHot

面向内部团队的内容助手。提供邀请码注册登录、每用户 TikHub Key、私有 TikTok / Twitter（X）/ 抖音作者监控、更新内容流、文案复制与图片/视频下载。

## 本机直接运行

当前 Windows 已准备好 `SuperHot-dev` Conda 环境、依赖和前端构建产物，**不需要 Docker 或额外安装数据库**。

```powershell
cd D:\github\SuperHot
.\start.ps1
```

打开 [http://127.0.0.1:8765](http://127.0.0.1:8765)。保持启动终端运行，按 `Ctrl+C` 关闭 API 和后台监控。关闭网页不会停止监控，退出启动器或电脑关机会停止。

也可在另一个 PowerShell 运行 `.\stop.ps1`，让启动器统一关闭 API 与监控。Linux 对应 `sh stop.sh`。

首次启动生成私有 `.env` 和 `.runtime/encryption.key`。在另一个 PowerShell 查看团队邀请码：

```powershell
cd D:\github\SuperHot
& 'D:\anaconda3\envs\SuperHot-dev\python.exe' scripts/admin.py invite
```

首位持邀请码注册的成员成为系统管理员。注册后先在「个人设置」保存自己的 TikHub Key，再添加监控并确认作者和间隔。不要把真实 Key 发到聊天或写进代码。

## 已实现

- 邀请码注册、登录、HttpOnly 会话、退出、密码修改及其他会话撤销。
- 私有监控和作品记录；每用户 Key 经 Fernet 加密保存，API 只返回掩码。
- TikTok / Twitter（X）/ 抖音主页、作品链接识别作者后确认，检查间隔 1–168 小时；支持按平台筛选监控和内容。
- 首次历史基线、新作品与未读标记、搜索、筛选、分页及文案复制。
- 暂停、恢复、手动检查、间隔修改、删除监控及运行记录。
- 独立 APScheduler/asyncio worker、数据库租约、作品去重、分页补查、失败退避、崩溃恢复和单 worker 进程锁。
- 视频和逐张图片下载到当前电脑；按需刷新地址，受控流式转发，不长期归档媒体。单素材限 256 MB。
- Twitter 纯文字、图文、视频、MP4 动图与混合素材；原创和引用帖监控，保留引用归属，按稳定素材 ID 下载。
- 抖音官方分享短链及整段分享消息识别作者；视频与图文分别展示下载素材，图文背景音乐不作为视频下载。
- 中文/英文、个人 IANA 时区、深色官网和浅色工作台。
- 管理员查看成员及 SDK 版本；独立启动器隔离安装候选环境，离线验证后切换 API/worker，失败回退；保留上一版供手动回退。
- Windows/Linux 安装与启动脚本、Alembic 迁移、依赖锁定、SQLite 一致性备份。

会员、支付、AIGC、音频、ASR、自动归档及其他平台不在本版范围。

## Twitter / X 使用与升级

1. 在「个人设置」保存本人的 TikHub Key，各平台共用本人填写的 Key。
2. 点击「添加监控」，粘贴 `https://x.com/用户名`、`https://twitter.com/用户名` 或 `/用户名/status/帖子ID` 形式的完整帖子链接。系统自动识别平台；暂不展开 `t.co` 短链接。
3. 确认返回的作者，设置 1–168 小时检查间隔。帖子链接用于识别该帖的实际作者，随后监控作者的新内容。
4. 在「监控对象」或「更新内容」选择平台筛选；纯文字帖子可以复制正文，有素材的帖子按每项类型显示下载按钮。

Twitter 当前采集原创与引用帖，排除回复、纯转发和推广条目。引用帖保留被引用作者及文字，不把对方的素材并入当前作者。首次检查建立历史基线；置顶旧帖按 ID、发布时间去重，不因出现在首位就认定为新更新。

图片按实际格式保存；视频优先选择上游返回的最高码率 MP4 变体；动图有 MP4 直链时按 MP4 保存。只有 HLS 分片地址或缺少直链的素材会显示不可下载，本版不合并分片、不转码，也不采集外链页面中的媒体。每次点击下载会刷新一次作品详情，消耗本人对应 API 额度。

已有部署升级前，先按下文备份命令生成一致性备份。运行 `.\stop.ps1` 后等待原启动终端退出，再运行 `.\start.ps1`；启动器会自动执行 Alembic 迁移，将现有监控归属为 TikTok，并保留用户、Key、作品与运行记录。不要在旧版 API / worker 仍运行时手动迁移数据库。

实现与验证说明见 [Twitter 接入文档](docs/twitter-monitoring.md)。

## 抖音使用与升级

1. 点击「添加监控」，粘贴抖音作者主页、具体视频 / 图文链接，或者包含 `https://v.douyin.com/.../` 的整段分享消息。系统自动识别平台并展开官方短链。
2. 点击「识别作者」，核对作者资料并确认检查间隔。粘贴作品链接时识别该作品的作者，确认后监控该作者后续发布的内容。
3. 首次检查保存首批可见作品为历史内容；后续按配置间隔检查新作品。两处列表的「平台」筛选均可选择「抖音」。
4. 打开作品详情复制文案、下载视频或逐张下载图片。图文按图片处理，不会把配乐或合成播放字段当成作品视频。保存位置由浏览器决定。

抖音复用现有 Key、私有权限和后台任务，不需要安装新服务或复制 SDK 源码。作者识别、周期检查、点击下载时刷新作品详情，都会消耗本人 TikHub 额度。当前作品列表固定使用 App V3 的 `lite` 通道，每页最多 20 条；不会因请求失败自动再调用另一条收费接口。

已有部署完成更新后运行 `.\stop.ps1`，等待原启动终端退出，再运行 `.\start.ps1`；此次抖音扩展复用现有数据库字段，无新增迁移。直接运行本机开发产物的用户刷新网页即可看到入口。接口结构异常会保留失败状态，不当成“作者没有更新”。

接口选择、支持的链接和验证边界见 [抖音接入文档](docs/douyin-monitoring.md)。

## 验证与边界

2026-10-19 在原生 Windows 上通过：

- Python 3.13.16、TikHub 2.2.0、APScheduler 3.11.3 的安装、导入和依赖检查。
- 后端 19 项检查：权限与凭据隔离、CSRF/来源校验、历史基线、增量去重、暂停/手动、租约恢复、分页上限、退避、SDK 版本门禁和升级失败回退。
- 浏览器流程：真实注册与 Key 保存；模拟 TikHub 响应下的作者确认、监控操作、内容流和下载；语言、320–1440px 布局及退出。
- TypeScript 检查、Vite 构建、Alembic 初始迁移和模型一致性检查。

**完整媒体下载和大规模运行仍待实测。** 2026-10-20 已使用已保存的成员 Key 完成 Twitter 作者时间线的真实请求与基线入库验证，以及抖音作者资料、20 条作品、单条视频详情和真实 MP4 前 64 KiB 的流式转发验证。抖音图文使用合成样例验证，尚无真实图文样本。浏览器验收使用独立数据库，日常数据库不含测试账户和示例监控。SDK 更新通过离线及故障模拟验证，尚未进行真实新版本切换。Linux、PostgreSQL 和 Docker 尚未实际验证。

用户在网页中填写真实 Key。识别、监控和下载刷新详情会消耗该用户额度；接口不可用、媒体权限、地区限制或新字段结构可能需要继续适配，界面会显示失败状态。

Twitter 扩展测试同时使用合成 GraphQL 响应和从实测结构制作的脱敏紧凑响应，覆盖原生 SDK 的 HTTP 请求、平台路由、用户隔离、正文与媒体解析、稳定素材 ID 下载和旧 SQLite 迁移。紧凑响应包含 `pinned`、`timeline` 数组、`next_cursor`、分组媒体及用户名为空的作者信息；按稳定作者 ID 过滤归属，回复和转发在正文解析前排除，不把引用对象的媒体并入当前帖子。

2026-10-20 扩展验证：后端 **56 项测试通过**，SDK v2.2.0 离线兼容检查通过；此前 TypeScript / Vite 构建及独立 QA 浏览器流程通过 TikTok 回归、Twitter 作者确认与平台筛选、纯文字、引用、图片 / 视频 / 动图下载、无直链状态、中英文及 320–1440px 布局检查。自动化测试不调用 TikHub 收费接口；本次问题复现和修复后的真实监控重试使用了对应成员的 Key。

2026-10-20 抖音扩展：后端 **86 项测试通过**，SDK v2.2.0 离线兼容检查及 TypeScript / Vite 构建通过。新增官方短链校验、原生 App V3 响应解析、视频 / 图文素材区分、分页去重、稳定图片 ID、跨平台筛选及用户隔离回归；真实响应样例已替换账号、作品与素材内容后纳入测试。独立 QA 浏览器流程通过三平台回归、抖音分享消息确认作者、视频与两张图片下载，以及 320px 详情 / 内容流布局检查，浏览器素材响应使用模拟数据。

## 目录与数据库

```text
backend/app/         FastAPI、模型、TikHub 适配、监控 worker
backend/app/providers/ 平台注册、链接识别、TikTok / Twitter / 抖音数据与素材适配
backend/migrations/ Alembic 迁移
backend/tests/      后端及升级回退检查
frontend/src/       React + TypeScript + Tailwind + Motion
frontend/tests/     浏览器验收（外部 API 模拟）
scripts/run.py      进程启动、异常重启、SDK 更新执行器
scripts/admin.py    邀请码查看、本地密码恢复
scripts/backup.py   SQLite 及密钥备份
.env                私有配置，不进入 Git
.runtime/           数据库、加密密钥、日志、版本环境，不进入 Git
```

当前默认 SQLite，启用 WAL，每套部署只运行一个 worker。SQLAlchemy 已保留 PostgreSQL 驱动与连接入口：先安装并创建数据库，再配置 `DATABASE_URL=postgresql+psycopg://...`。**修改连接地址不会自动搬迁 SQLite 数据。** 多设备共用 PostgreSQL 的多 worker 模式不属于当前已验证范围。

### 使用 DB Browser for SQLite 查看数据库

[DB Browser for SQLite](https://sqlitebrowser.org/) 是免费、开源的 SQLite 可视化工具，可以像查看表格一样浏览记录，也支持查看表结构、筛选数据、执行 SQL 和导出 CSV。

1. 从[官方下载页](https://sqlitebrowser.org/dl/)下载 **64 位 Windows 安装版**；也可以选择免安装 ZIP 版，解压后运行。
2. 至少启动一次 SuperHot，生成数据库。打开 DB Browser for SQLite，点击「打开数据库 / Open Database」，选择项目根目录下的 `.runtime/superhot.db`。本机默认完整路径为 `D:\github\SuperHot\.runtime\superhot.db`，其他设备按实际项目路径选择。
3. 在「数据库结构 / Database Structure」中查看表、字段和索引；在「浏览数据 / Browse Data」中选择表，查看、排序和筛选记录。
4. 如需自定义查询，切换到「执行 SQL / Execute SQL」，输入 SQL 并执行。

打开本地 SQLite 文件不需要填写服务器地址、端口或数据库账号密码。如果配置了 `SUPERHOT_RUNTIME` 或 `DATABASE_URL`，请根据实际配置定位数据库；本教程适用于 SQLite 文件。

常用业务表：

| 表名 | 内容 |
| --- | --- |
| `users` | 注册用户、个人设置及加密后的 TikHub Key |
| `monitors` | 用户添加的监控对象、检查间隔和运行状态 |
| `posts` | 已采集的作品内容、媒体地址及新内容 / 已读标记 |
| `runs` | 监控任务运行记录，包括执行时间、结果和新增作品数 |

例如，查询最近 50 条监控运行记录：

```sql
SELECT *
FROM runs
ORDER BY started_at DESC
LIMIT 50;
```

`started_at` 等时间字段使用 Unix 时间戳（秒）。如需在查询结果中显示当前电脑的本地时间：

```sql
SELECT datetime(started_at, 'unixepoch', 'localtime') AS started_local,
       status, new_count, pages, message
FROM runs
ORDER BY started_at DESC
LIMIT 50;
```

`runs` 记录一次监控任务的执行结果，并非逐次 TikHub API 调用日志或扣费流水。需要数据库副本时，使用下文「配置、日志与备份」中的 `scripts/backup.py` 生成一致性备份。

## 其他 Windows 设备准备

安装 Python 3.13 和 Node.js（建议 24 LTS）后获取仓库：

```powershell
.\setup.ps1
.\start.ps1
```

安装脚本优先使用已有 `D:\anaconda3\envs\SuperHot-dev`，否则用 Python 3.13 创建 `.venv`。可设置 `SUPERHOT_PYTHON` 指向自己的解释器，不改动其他 Conda 环境。

本机工具：Conda `D:\anaconda3`，解释器 `D:\anaconda3\envs\SuperHot-dev\python.exe`，Node.js `24.14.0`，npm `11.9.0`。原 `SuperHot`（Python 3.15）环境保留。

也可在项目根目录运行 `conda env create -f environment.yml`。完整依赖固定在 `backend/requirements.txt` 和 `frontend/package-lock.json`；`backend/requirements.in` 固定直接依赖，SDK 更新会同步后端版本文件。

## Linux 准备（待目标机验证）

需要 Python 3.13、venv 支持和 Node.js：

```sh
sh setup.sh
sh start.sh
```

Node 仅用于安装/构建，日常由 Python 服务前端产物。Docker 留到后续部署阶段。

## 配置、日志与备份

`.env.example` 列出配置。默认仅监听 `127.0.0.1:8765`。以后对团队网络开放时，配置实际 `SUPERHOT_ORIGINS`、HTTPS、`SUPERHOT_SECURE_COOKIE=true` 和进程管理；本地设置不自动作为公网生产配置。

- API 日志：`.runtime/api.log`；监控日志：`.runtime/worker.log`。
- 更新构建日志：`.runtime/releases/<任务 ID>/build.log`。
- 接口文档：[http://127.0.0.1:8765/api/docs](http://127.0.0.1:8765/api/docs)。

忘记密码时，本机交互式恢复（密码不放进命令行）：

```powershell
& 'D:\anaconda3\envs\SuperHot-dev\python.exe' scripts/admin.py reset-password --email you@example.com
```

SQLite 一致性备份：

```powershell
& 'D:\anaconda3\envs\SuperHot-dev\python.exe' scripts/backup.py
```

`backups/` 被 Git 忽略，备份含数据库、配置及解密密钥，按私有数据保管。恢复前停止启动器，再恢复 `.runtime/superhot.db`、`.runtime/encryption.key` 和 `.env`。只复制数据库而丢失密钥会导致原 Key 无法解密。

SDK 更新只接受已核实的官方版本，不接受自定义命令、任意仓库或包名。主版本变化、Python 不兼容、依赖/签名/健康检查失败会阻止切换或触发回退；离线检查不保证线上行为。切换前暂停派发并等待在途监控结束，统一重启 API/worker。全员共用 SDK 版本，Key 不参与安装或构建日志。

## 开发与测试

```powershell
# 终端一
.\start.ps1
# 终端二：热更新开发服务，/api 代理到后端
cd frontend
npm run dev
```

```powershell
& 'D:\anaconda3\envs\SuperHot-dev\python.exe' -m pytest backend/tests -q
& 'D:\anaconda3\envs\SuperHot-dev\python.exe' scripts/sdk_probe.py 2.2.0
cd frontend
npm run build
```

`frontend/tests/smoke.cjs` **只能指向独立 QA 实例**，会注册测试账号。通过 `SUPERHOT_RUNTIME`、`DATABASE_URL`、`SUPERHOT_PORT`、`SUPERHOT_ORIGINS`、`SUPERHOT_INVITE_CODE` 启动隔离实例，再设置 `BASE_URL`、`TEST_INVITE_CODE` 运行。默认测试地址为 `127.0.0.1:8766`；外部 TikHub 路径由浏览器模拟。Windows 使用已安装 Chrome，其他环境可设置 `CHROME_PATH`，或安装 Playwright Chromium。

设计背景：[产品方案](docs/product-plan.md)、[监控方案](docs/monitoring.md)、[SDK 更新方案](docs/sdk-updates.md)。当前实现与验证边界以此 README 为准。
