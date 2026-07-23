# API and Interfaces

## Training baseline projection

`get_training_baseline_view(db_path, target_date=None, now=None,
planned_rest_dates=(), sync_context=None)` returns today's status, typical
training-day baselines, rolling seven-day load, a fourteen-day distribution,
and baseline maturity. `build_training_baseline_view(connection, ...)` is the
dependency-injected form used by tests. Status values include `not_synced`,
`sync_error`, `no_training_yet`, `planned_rest`, `confirmed_no_training`, and
`training_present`.

## Local Coach CLI

`python -m src.local_coach.engine` selects the latest deterministic score date.
`--date`, `--all`, and `--dry-run` select one day, all days, or validation without
writes. Output contains safe aggregate counts only and performs no HTTP request.

> Polar, Kubios, SQLite, Dashboard, and future AI contracts.
> This document describes implemented code, not a guarantee of external service availability.
> Verified: 2026-07-10.

## 范围

- 本文记录项目当前使用的外部与内部接口。
- 外部接口包括 Polar OAuth。
- 外部接口包括 Polar AccessLink v3。
- 外部接口包括 Polar AccessLink v4。
- 文件接口包括 Kubios CSV。
- 内部接口包括 SQLite 表契约。
- 展示接口包括 Streamlit Dashboard。
- 未来接口包括 AI API。
- 本文不保存任何真实凭据。
- 核验日期为 2026-07-10。

## Polar OAuth

- 授权服务地址为 https://auth.polar.com/oauth/authorize。
- Token 地址为 https://auth.polar.com/oauth/token。
- 授权方式为 Authorization Code。
- 客户端认证使用 HTTP Basic。
- redirect URI 来自 POLAR_REDIRECT_URI。
- 本地默认 callback 为 /oauth2_callback。
- 请求包含随机 state。
- callback 必须校验 state。
- authorization code 不写入日志。
- token 保存到受控本地文件。

## 当前 Scope

- training_sessions:read 用于训练 sessions。
- activity:read 用于活动。
- sleep:read 用于睡眠。
- nightly_recharge:read 用于 Nightly Recharge。
- continuous_samples:read 用于连续样本。
- profile:read 用于账户信息。
- scope 由空格连接。
- 新增 scope 必须核对 Polar 应用权限。
- invalid_scope 应记录安全错误参数。
- 不得在文档中记录用户授权 token。

## Token 生命周期

- access_token 从 token 文件读取。
- expires_at 用于本地过期判断。
- 检查时预留 leeway。
- 过期时尝试 refresh_token。
- 刷新使用 grant_type refresh_token。
- 刷新结果保留旧 refresh token 作为兼容。
- 新 expires_at 减去安全余量。
- 刷新失败抛 PolarTokenRefreshError。
- 缺少 refresh token 要求重新 OAuth。
- 任何日志不得打印 token 值。

## Polar v3 基础

- Base URL 为 https://www.polaraccesslink.com/v3。
- 普通 GET 由 PolarClient.get 封装。
- POST 由 PolarClient.post 封装。
- Authorization 使用 Bearer。
- Accept 使用 application/json。
- 默认 timeout 为 30 秒。
- 204 返回 None。
- 空 body 返回 None。
- HTTP 错误抛 PolarAPIError。
- 错误 body 只保留有限长度。

## Polar v3 用户接口

- 用户账户可访问 /users/{user_id}。
- 无已知 user id 时尝试 /users/physical-info。
- register_user 使用 POST /users。
- member-id 来自配置或默认本地标识。
- 用户 id 可从 token 元数据读取。
- 用户 id 可从本地 user 文件读取。
- 用户接口错误不应阻塞其他端点导入。
- 账户响应保存为 polar_user_account.json。
- 账户信息不进入 Recovery Score。
- 用户标识不得在 Dashboard 展示。

## Polar v3 活动接口

- 当前 fetch 主路径调用 /users/activities。
- 支持 from 日期参数。
- 支持 to 日期参数。
- 支持 steps 布尔参数。
- 支持 activity_zones 布尔参数。
- 支持 inactivity_stamps 布尔参数。
- 布尔参数转换为 true 或 false 文本。
- 响应保存 polar_daily_activity.json。
- 导入支持多种容器键。
- 活动字段进入 raw 表后再聚合。

## Polar v3 训练兼容接口

- 兼容方法调用 /exercises。
- 可请求 samples。
- 可请求 zones。
- 可请求 route。
- 三个参数使用布尔文本。
- 当前主要训练列表使用 v4。
- v3 方法保留兼容和诊断。
- 训练响应不得直接进入 Dashboard。
- 外部字段先保留 raw_json。
- 接口变化由 Polar Client 层吸收。

## Polar v4 基础

- Base URL 为 https://www.polaraccesslink.com/v4/data。
- v4 GET 由 PolarClient.get_v4 封装。
- Authorization 使用 Bearer。
- Accept 使用 application/json。
- 默认 timeout 为 30 秒。
- 日期参数按端点需要转换。
- 完整 URL 允许直接传入。
- 相对路径自动拼接。
- 204 和空 body 返回 None。
- HTTP 错误抛 PolarAPIError。

## v4 Training Sessions

- 路径为 /training-sessions/list。
- from 转换为当天 00:00:00。
- to 转换为当天 23:59:59。
- 日期时间参数名为 from 与 to。
- 响应保存 polar_training_sessions.json。
- 导入提取 sport。
- 导入提取 start_time。
- 导入提取 duration 与 calories。
- session external_id 优先使用来源 id。
- 数据进入 polar_training_sessions_raw。

## v4 Activity

- 客户端方法路径为 /activity/list。
- from 与 to 使用日期格式。
- 方法为 get_daily_activity。
- 当前 fetch 编排仍使用 v3 daily activity。
- v4 方法可用于未来切换。
- 切换前需要对返回结构补充测试。
- 响应必须先保存 raw 层。
- 不能让 Dashboard 直接调用。
- 字段映射变化只修改客户端与导入层。
- 评分不依赖具体 API 版本。

## v4 Sleep

- 列表路径为 /sleeps。
- 无 features 时仅返回可用睡眠日期。
- 详情仍使用 /sleeps，但每次只请求一天，并传入 sleep-result、
  original-sleep-result、sleep-evaluation 与 sleep-score features。
- from 为包含日期，to 为下一天的排除日期。
- 响应保存 polar_sleep.json。
- 导入提取 asleepDuration、sleepSpan、sleep score、深睡和 REM 阶段。
- 数据进入 polar_sleep_raw。
- 缺失睡眠不阻塞其他抓取。

## v4 Nightly Recharge

- 列表路径为 /nightly-recharge-results。
- 单日路径为 /nightly-recharge-results/{date}。
- from 与 to 使用日期。
- 响应保存 polar_nightly_recharge.json。
- 导入提取 ans status。
- 导入提取 HRV RMSSD。
- 导入提取 resting HR。
- 导入提取 respiration rate。
- 数据进入 polar_nightly_recharge_raw。
- 字段别名兼容在 import 层处理。

## v4 Cardio Load

- 列表路径为 /cardio-load。
- 单日路径为 /cardio-load/{date}。
- 日期范围路径为 /cardio-load/date。
- 范围参数转换为日期时间。
- 响应保存 polar_cardio_load.json。
- 导入提取 cardio_load。
- 导入提取 strain。
- 导入提取 tolerance。
- 导入提取 status。
- 当前尚未进入日指标或评分。

## v4 Continuous HR

- 路径为 /continuous-samples。
- from 与 to 使用日期，to 为排除日期。
- features 必须包含 heart-rate-samples。
- 同日多设备响应保留样本最完整的设备流，避免重复计算。
- 响应保存 polar_continuous_heart_rate.json。
- 数据进入 polar_continuous_hr_raw。
- 样本完整内容保留 raw_json。
- Dashboard 按入睡与醒来时间过滤样本，计算睡眠平均和最低心率。
- scope 需要 continuous_samples:read。

## 请求错误契约

- PolarAPIError 保存 path。
- PolarAPIError 保存 status_code。
- PolarAPIError 保存有限 body。
- safe_error_payload 不包含 token。
- fetch 可把安全错误摘要保存到 raw 文件。
- 401 通常需要检查 token。
- 403 通常需要检查 scope 或 consent。
- 404 可能表示端点或日期无数据。
- 429、常见 5xx 与瞬时 TLS/连接错误使用有界 GET 退避重试。
- 5xx 不应删除已有本地数据。

## Local scheduler adapter

- `scripts/run_scheduled_sync.py` 是 LaunchAgent、手动验证与 Catch-Up 共享的
  本地适配器，不是公共 HTTP API。
- `trigger_type` 仅允许 `manual`、`scheduled`、`catch_up`。
- Scheduler 不复制 Fetch、Import、算法或报告逻辑。
- 输出只包含安全摘要与错误码，不包含凭据或原始健康 payload。

## Raw 文件接口

- 目录为 data/raw。
- 文件编码为 UTF-8。
- JSON 使用 ensure_ascii=False。
- 每个抓取类别使用稳定文件名。
- 重复抓取会更新同名快照。
- raw 文件是导入边界。
- 错误摘要可能保存在同名文件。
- 导入前检查响应是否为有效列表或容器。
- raw 文件不在 Dashboard 展示。
- token 文件不属于 raw API 输出。

## Kubios Import

- 默认路径为 data/imports/kubios_morning_hrv.csv。
- 接口是本地 CSV 而非网络 API。
- 必需字段是 date。
- 可识别 measurement_time。
- 可识别 rmssd。
- 可识别 mean_hr。
- 可识别 readiness。
- header 支持规范化别名。
- 编码支持 UTF-8 BOM。
- 重复导入通过业务键 upsert。

## Kubios Header

- date 支持 date、measurement date、日期等别名。
- time 支持 time、measurement time 与 timestamp。
- rmssd 支持 rmssd ms 与 rmssd (ms)。
- mean_hr 支持 mean hr 与 heart rate。
- readiness 支持 readiness score 与 status。
- 日期时间可包含 T。
- 单独时间可与 date 拼接。
- 无效数字转换为 NULL。
- 缺少 date 列抛 KubiosImportError。
- 当前不需要 Kubios 账号信息。

## SQLite 内部接口

- connect 返回初始化后的 connection。
- init_db 建表并应用迁移。
- raw import 接受 connection。
- daily rebuild 接受可选 connection。
- baseline 计算接受 connection。
- score rebuild 接受可选 connection。
- report 读取 connection。
- dashboard_data 使用只读查询意图。
- SQL 参数使用绑定。
- 表契约详见 DATABASE.md。

## Dashboard 接口

- 启动命令为 streamlit run src/dashboard.py。
- 默认本地地址通常为 127.0.0.1:8501。
- macOS 可通过 `scripts/build_macos_app.py` 生成双击启动的本地 `.app`。
- `.app` 使用原生 AppKit/WebKit 窗口和 `src/dashboard_launcher.py`，仅绑定
  loopback；端口占用时在受控范围内顺延。
- Dashboard 不提供公共 REST API。
- Dashboard 只读取 recovery.db。
- 最新状态来自 get_latest_day。
- 7 天趋势来自 get_last_7_days。
- 30 天趋势来自 get_last_30_days。
- 个人基线来自 get_latest_baselines。
- 缺失值显示暂无数据。
- Dashboard 不接受 token 输入。

## AI Coach 设计契约（未实现）

- 状态为 Cloud Governance Approved；没有公共 endpoint、provider adapter 或外部 API。
- 必须位于 Recovery 与 Confidence Engine 下游，只读结构化持久化结果。
- 输入使用最小 allowlist：日期、score/version、deterministic factors、
  confidence/level/version、missing groups、aggregate metrics、baseline labels、
  locale/units 和隔离后的用户问题。
- token、secret、account identifier、raw_json、raw payload、数据库文件和日志禁止进入请求。
- 输出 schema 包含 summary、evidence、limitations、suggested_actions、
  questions_for_user、safety_notice 和 audit。
- audit 包含 model、prompt、output schema、safety policy、input digest 与时间版本字段。
- schema 或安全验证失败时不返回生成建议，使用确定性解释降级。
- 云端路线、closed field schema、Zero Data Retention、分层本地保留和审计表方案已批准。
- 具体 provider、model、endpoint、region 和实际 migration 执行仍需实现前批准。
- 完整权威契约见 [AI_COACH.md](AI_COACH.md)。

## API 变更规则

- 外部 API 变化先改 Polar Client。
- 返回结构变化再改 Import。
- 分析层不感知外部 URL。
- scope 变化更新 OAuth 与本文。
- 新增端点必须增加 mock 测试。
- 错误处理不得泄露凭据。
- 网络 timeout 必须显式。
- 重试策略必须避免重复副作用。
- 废弃端点需要迁移计划。
- 时间敏感结论需要核对官方文档。

## 操作命令

- OAuth：python src/polar_oauth.py。
- Fetch：python src/polar_fetch.py。
- 导入：python src/polar_import.py。
- Kubios：python src/kubios_import.py。
- 日指标：python src/daily_metrics.py。
- 基线：python src/baseline.py。
- 评分：python src/recovery_score.py。
- 报告：python src/report.py。
- Dashboard：streamlit run src/dashboard.py。
- 测试：python -m unittest discover -s tests。
