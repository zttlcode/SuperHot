# Twitter / X 监控接入

本次扩展复用已有账户、每用户 TikHub Key、私有监控、APScheduler worker 和内容表。平台接入使用当前固定的 TikHub SDK v2.2.0 的 `twitter_web` 资源，不需要另装爬虫或单独克隆 SDK。

## 用户流程与范围

- 支持 `x.com`、`twitter.com` 的作者主页和具体帖子链接，兼容 `www`、`mobile.twitter.com` 及 `/i/web/status/ID`。不展开 `t.co`，不把搜索页、首页或任意网址交给远程解析。
- 主页链接通过 `fetch_user_profile(screen_name=...)` 识别作者；帖子链接通过 `fetch_tweet_detail(tweet_id=...)` 获取实际作者，不信任链接中写出的用户名。
- 作者确认记录归属于当前用户，30 分钟内有效；确认后以平台和稳定用户 ID 监控。用户名变化不改变监控身份。
- 定时使用 `fetch_user_post_tweet(rest_id=..., cursor=...)`，默认保存原创、引用帖；回复、纯转发和推广条目不进入内容流。
- 引用作者与引用文字作为独立关联展示，不混合引用对象的媒体。纯文字保留正文、换行及可用的长文全文；没有媒体时仅提供复制及查看原帖。
- 按平台筛选仍受当前用户权限约束。不同成员各自保存记录、使用自己的 Key，不跨用户合并监控或调用凭据。

## 代码与数据

| 文件 | 责任 |
| --- | --- |
| `backend/app/providers/base.py` | SDK 生命周期、通用错误处理与响应外层校验 |
| `backend/app/providers/links.py` | 官方链接识别与平台判断 |
| `backend/app/providers/tiktok.py` | 原有 TikTok 解析和分页 |
| `backend/app/providers/twitter.py` | Twitter 作者、时间线、推文、引用和媒体归一化 |
| `backend/app/providers/assets.py` | 稳定素材标识与对外摘要 |
| `backend/app/providers/registry.py` | 根据平台选择适配器 |
| `backend/app/worker.py` | 共用派发、凭据隔离、基线、去重、分页与失败退避 |
| `backend/app/main.py` | 平台筛选、作品摘要及素材下载接口 |
| `backend/app/media.py` | 按平台校验 CDN、逐步校验重定向、受限转发 |
| `scripts/sdk_probe.py` | SDK 升级前同时检查两平台的方法签名和离线解析样例 |

统一适配器提供 `resolve(link)`、`list_posts(author_id, provider_data, cursor)` 和 `detail(post_id)`。分页返回 `(posts, next_cursor, has_more)`；初始游标为 `None`，适配器负责平台转换。Twitter 游标原样传递，禁止转为整数；检测重复或缺失的下一页游标。

监控增加 `platform` 和 `provider_data`，唯一键为 `(owner_id, platform, author_id)`。旧数据默认 `tiktok`，旧 `sec_uid` 保留供兼容读取，游标列扩大为 `Text`。帖子仍使用 `(monitor_id, platform_id)` 去重，增加 `post_type` 和 `references`；平台从所属监控取得，避免重复存储造成不一致。所有平台 ID 在数据库和浏览器 JSON 中使用字符串。

`Post.assets` 继续保存 JSON，每项含 `id`、`kind`、`url`、`preview`、`mime_type`、`order`、可用尺寸和 `downloadable`。视频下载地址由解析器从变体中选出，不把缩略图当成视频文件；原始上游对象不会直接传给前端。

`GET /api/posts` 返回逐素材摘要，隐藏下载 URL。新下载路由是 `GET /api/posts/{post_id}/assets/{asset_id}/download`：先校验作品及素材归属，再使用本人 Key 刷新详情，按稳定 ID 匹配素材。旧的序号下载路由保留兼容，也先把旧序号转换为保存的素材 ID，避免刷新后数组顺序变化导致错配。

## 媒体与调用边界

- 图片、视频、动图按每项素材独立处理，混合内容不依赖整帖 `kind` 推断文件类型。
- 视频优先选取可用 MP4 中码率最高的变体；动图保留类型标记，有 MP4 时下载 MP4，不转换为 GIF。
- 仅有 HLS 或没有直链时保留预览，按钮显示不可下载。单素材仍限制 256 MB，实际文件扩展名按响应 MIME 确定。
- Twitter 下载仅允许已验证的 `pbs.twimg.com`、`video.twimg.com`，保留 HTTPS、公网地址和每次重定向校验。TikHub Key 不发送给素材 CDN。
- 每次下载刷新一次详情；定时检查优先使用列表里的信息，不为每条作品额外查询详情。运行记录仍是监控任务汇总，不代表逐次 API 调用或扣费流水。
- 后端转发媒体，不长期保存；浏览器接收为 Blob 后保存到当前电脑，大文件会使用一定浏览器内存。

## 迁移与验证

迁移 `b6e2d9a14f03` 在启动 API / worker 前执行。SQLite 批量重建监控表时，迁移连接暂时关闭外键执行并随后检查引用完整性，避免重建父表触发已有作品、运行记录的级联删除。已有部署应先执行 README 中的一致性备份，再停止旧进程、启动新版。测试覆盖有用户、密钥、监控、作品、运行记录和待确认作者的旧库升级，以及降级后再次升级；存在 Twitter 监控时阻止删除平台字段的降级。

`backend/tests/fixtures/twitter_timeline.json` 是合成的 GraphQL 形状样例；`twitter_compact_timeline.json` 依据 2026-10-20 的真实响应字段布局制作，作者与作品 ID、正文、日期、链接和游标均已替换。两种样例同时用于 SDK 离线兼容检查。自动化测试还覆盖紧凑列表、长文字、引用归属、回复/转发过滤、纯文字、图文、视频、动图、混合素材、分页游标、权限与 CDN；SDK HTTP 合约测试通过 MockTransport 运行真实 SDK，不调用收费服务。浏览器测试使用独立 QA 数据库模拟外部采集及媒体响应，不写入日常数据。

官方文档的推文响应示例未给出完整 `data` 内容，SDK 返回 `Any`，因此不能仅凭签名保证线上字段结构。解析器支持已列出的时间线及紧凑列表形状；不认识的列表或时间线指令会报错，避免把结构变化显示成“成功但没有更新”。2026-10-20 已完成一条实际监控的真实请求和基线入库；真实媒体下载、跨页增量的线上稳定性、地区差异、Linux 与 PostgreSQL 仍需目标环境验证。

## 紧凑时间线结构与本次修复

实际 `fetch_user_post_tweet` 返回的 `data` 使用 `timeline: [...]` 和单独的 `pinned` 对象，不是 GraphQL `instructions`，也不是 `tweets` 列表。`next_cursor` 用于翻页，`prev_cursor` 不作为下一页游标；置顶帖与普通列表重复时按作品 ID 去重。

紧凑帖子的 `media` 可能是空列表，也可能是按 `video`、`photo` 等类型分组的对象。分组中的元素不一定带 `type`，适配器从分组补全类型，再选择 MP4；空的 `entities` 列表不会被误当作异常。

作者对象可能仅有 `rest_id`，`screen_name`、`name`、`avatar` 均为 `null`。采集时按该稳定 ID 校验作者归属，不要求显示字段完整；从帖子链接添加作者且缺少用户名时，再用用户 ID 查询资料以完成确认。`quoted`、`reply_to`、`retweeted` 和 `retweeted_tweet` 分别用于引用、回复与转发识别；回复和转发先排除，引用媒体不合并到当前帖子。

官方参考：[SDK 接口表](https://github.com/TikHub/TikHub-API-Python-SDK/blob/main/docs/reference.md)、[TikHub 推文详情](https://docs.tikhub.io/191321709e0)、[X 媒体对象](https://docs.x.com/x-api/fundamentals/data-dictionary#media)。X 的对象文档用于设计参考，不等于 TikHub 的响应契约。
