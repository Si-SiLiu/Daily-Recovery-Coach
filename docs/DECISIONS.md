# Architecture Decisions

## ADR-040 睡眠规律性与昨夜作息偏离分离且保持现有 UI

- 状态：Completed。
- 决策：长期规律性优先选择 SRI；无足够时间线时使用入睡、起床和实际
  睡眠时长的稳健复合评分；昨夜作息偏离独立计算并排除昨夜自身。
- 约束：使用设备无关的 `CanonicalSleepRecord`，缺失数据不得变成 0，
  24 小时钟表比较使用环形差值；本次不改变现有页面卡片结构和数据库版本。
- 参数：权重 0.35/0.45/0.20，半分阈值 60/45/60 分钟，算法版本 2.0.0；
  这些是可校准产品参数，不是临床诊断标准。

## ADR: Valid training-day baseline and separate rolling load (2026-07-22)

- **Decision:** training-day baselines use only days with metric-valid training
  observations; duration and calories maintain independent sample counts.
- **Decision:** rest, unsynced, missing, and incomplete days never become zero
  samples. Single-day state is separate from rolling seven-day load.
- **Rationale:** a normal rest day or an unfinished synchronization must not be
  rendered as a false `0 kcal` or `-100%` training decline.
- **Authority:** `src/training_baseline.py` and `tests/test_training_baseline.py`.
- **Migration:** none; existing raw and synchronized tables are reused.

## ADR: Versioned supplement product facts and candidate-only AI (2026-07-18)

- **Decision:** daily supplement intake records brand/product/quantity/unit;
  effective ingredients belong to a versioned product profile.
- **Authority:** only confirmed labels or trusted sourced profiles may produce
  ingredient totals. AI/search/OCR can produce candidates only.
- **Compatibility:** legacy active-dose columns and rows remain; migration links
  them conservatively and never merges conflicting formulas.
- **Medication:** medication is a separate product kind and cannot enter ordinary
  supplement lookup or dose-adjustment advice.

## ADR: Polar objective authority with manual training details (2026-07-18)

- **Decision:** Polar owns objective session time, duration, heart rate, calories,
  distance and raw sport; manual data supplements exercises, sets and an explicit
  displayed-sport override.
- **Linking:** exact external ID or explicit user selection only. Same date and
  approximate time may be candidates but never silent merge rules.
- **Safety:** bodyweight and assisted load are not ordinary kg volume; uncertain
  metrics remain uncalculated and never enter Recovery or Baseline in this phase.

## ADR: Food-level simple nutrition input (2026-07-18)

- **Decision:** users record food/beverage, quantity and unit; a multi-tag food
  catalog performs classification and only reliable normalization/calculation.
- **Compatibility:** legacy rows remain and are copied with original tags/units.
- **Safety:** unknown foods remain unclassified with `NULL` nutrition; no serving
  size, nutrient value or count-to-weight conversion is guessed.

## ADR: Supplement dual-dose model (2026-07-18)

- **Decision:** store consumed `quantity + unit` and optional paired
  `active_amount + active_unit`, not a universal gram dose.
- **Reason:** count, mass, volume and IU are not interchangeable; guessing
  capsule content would corrupt health records.
- **Compatibility:** legacy gram values remain quantity with `unit='g'`.
- **Consequence:** unlike units stay separate; future conversions must be
  explicit and versioned.

## ADR-038 — macOS Vision for local Kubios screenshot OCR

- Status: Accepted.
- Decision: use a compiled Swift helper backed by macOS Vision through a Python
  Adapter. Do not require Tesseract, PyObjC, a cloud OCR service, or an API key.
- Rationale: it is already available on the target Intel Mac, stays offline,
  and keeps Streamlit independent from system APIs.

## ADR-039 — Review gate and stable Kubios source priority

- Status: Accepted.
- Decision: every OCR result requires an explicit user checkbox and import
  click. CSV remains the configured default source; an explicit screenshot
  override is persisted rather than inferred from insertion order.

## ADR-040 — macOS LaunchAgent schedules the existing pipeline

- Status: Completed.
- Decision: use a user-level LaunchAgent with local `StartCalendarInterval` and
  make it call the existing pipeline adapter. Do not run a timer loop inside
  Streamlit and do not duplicate synchronization business logic.
- Consequence: the job works independently of the Dashboard process, while an
  asleep, powered-off, or logged-out Mac can still delay or miss 06:00.

## ADR-041 — One cross-process lock covers every trigger

- Status: Completed.
- Decision: acquire a kernel-backed file lock inside `PipelineRunner` for manual,
  scheduled, and catch-up entry points. Persist only diagnostic lock metadata.
- Consequence: concurrent writes are rejected safely and abnormal process exit
  cannot leave a permanent lock.

## ADR-042 — Polar wins overlapping measured manual fields

- Status: Completed.
- Decision: resolve activity and sleep measured fields per canonical field with
  Polar first; use manual only when the Polar candidate is absent.
- Consequence: user context fills gaps without being presented as device data or
  overwriting the raw source.

## ADR-043 — Confirmed activity type is a semantic override

- Status: Completed.
- Decision: only a confirmed manual activity type may outrank Polar. A confirmed
  session link in `polar_manual_session_links` is required before records merge.
- Consequence: generic device labels can be corrected without changing measured
  duration, heart rate, calories, distance, or the original classification.

## ADR-044 — Kubios morning and Polar nightly remain distinct

- Status: Completed.
- Decision: do not apply a global source ranking between Kubios and Polar.
  Morning RMSSD/Mean HR and nightly HRV/Resting HR remain separate canonical
  fields with independent policies.
- Consequence: source availability cannot silently change measurement semantics.

## ADR-045 — Persist a recomputable provenance cache

- Status: Completed.
- Decision: persist versioned canonical outputs in `resolved_daily_fields` while
  retaining query-time resolvers and all source rows.
- Consequence: Dashboard, Report, and AI Context can audit `value_source`,
  fallback, override, reason, and version; the cache can be rebuilt idempotently.

## ADR-046 — Inline edits are explicit field corrections

- Status: Completed.
- Supersedes: ADR-042 and the activity-type-only limit in ADR-043.
- Decision: a user-saved inline edit outranks the corresponding device field;
  unedited fields keep their source priority. Raw Polar and Kubios rows are
  immutable, and correction provenance remains visible.
- Consequence: editing has immediate visible meaning without destroying the
  original measurement.

## ADR-047 — Nutrition uses normalized meal events and five item positions

- Status: Completed.
- Decision: store an actual meal event separately from its category items and
  enforce positions 1–5 per category in both validation and SQLite.
- Consequence: all requested meal/category combinations remain extensible and
  auditable without a wide JSON column or fabricated nutrient totals.

> Major technical choices and their consequences.
> Initial reconstruction date: 2026-07-10

## 记录规则

- ADR 编号一旦分配不复用。
- 状态可为 Proposed、Accepted、Completed、Superseded。
- 每项决策记录上下文。
- 每项决策记录结论。
- 每项决策记录收益。
- 每项决策记录代价。
- 每项决策记录替代方案。
- 变更结论时追加新 ADR。
- 不得静默重写已实施决策的历史原因。
- 决策日期应使用 ISO 日期。
- 重大架构变化必须先记录再实施。
- 本文件不保存 secret 或个人健康值。

## ADR-001 使用 SQLite

- 状态：Completed。
- 上下文：单用户、本地优先、数据量有限，需要零运维持久化。
- 决策：选择 SQLite 作为当前主数据库。
- 主要收益：部署简单、事务可靠、Python 原生支持。
- 主要代价：并发写能力有限，未来多用户可能迁移。
- 评估过的替代方案：PostgreSQL、DuckDB、纯 JSON。

## ADR-002 使用 Streamlit

- 状态：Completed。
- 上下文：需要快速构建本地分析界面并复用 Python 数据栈。
- 决策：选择 Streamlit 作为当前 Dashboard。
- 主要收益：迭代快、原生指标和图表、适合单用户。
- 主要代价：复杂交互和移动端能力有限。
- 评估过的替代方案：Flask 模板、React、Dash。

## ADR-003 采用 Personal Baseline

- 状态：Completed。
- 上下文：HRV、心率和睡眠存在显著个体差异。
- 决策：使用个人 28 天滚动历史而非人群固定阈值。
- 主要收益：更符合个人趋势并减少跨人误判。
- 主要代价：需要至少 7 个有效历史日。
- 评估过的替代方案：固定阈值、同龄人百分位、机器学习。

## ADR-004 Recovery Engine 独立于 Dashboard

- 状态：Completed。
- 上下文：评分需要可测试、可批处理并服务多个消费者。
- 决策：算法只依赖结构化数据，不依赖 Streamlit。
- 主要收益：报告、Dashboard 和未来 API 可复用同一结果。
- 主要代价：需要额外查询与持久化边界。
- 评估过的替代方案：页面内即时计算。

## ADR-005 AI Coach 不负责计算评分

- 状态：Accepted。
- 上下文：生成式模型输出可能不稳定且难以回放。
- 决策：AI 只解释确定性评分并提出可审阅建议。
- 主要收益：评分可复现、版本可追踪、责任边界清晰。
- 主要代价：AI 表达仍需安全约束。
- 评估过的替代方案：让 LLM 直接返回 recovery_score。

## ADR-006 保留 Raw JSON

- 状态：Completed。
- 上下文：外部字段会演进且导入映射可能需要修正。
- 决策：保存完整原始响应并同时抽取常用字段。
- 主要收益：可追溯、可重放、可修复映射。
- 主要代价：占用更多空间且含敏感数据。
- 评估过的替代方案：只保存解析字段。

## ADR-007 使用日粒度分析表

- 状态：Completed。
- 上下文：恢复建议主要按天决策，多来源时间粒度不同。
- 决策：把活动、训练、睡眠和 HRV 合并为每天一行。
- 主要收益：简化基线、评分和趋势查询。
- 主要代价：会隐藏日内波动，raw 层仍保留细节。
- 评估过的替代方案：事件流、小时粒度宽表。

## ADR-008 所有导入使用 Upsert

- 状态：Completed。
- 上下文：抓取与导入任务需要重复执行。
- 决策：按来源业务键更新而非盲目插入。
- 主要收益：重跑安全并能修正同一记录。
- 主要代价：业务键设计错误会覆盖不应覆盖的数据。
- 评估过的替代方案：每次全量清空重导。

## ADR-009 评分结果版本化

- 状态：Completed。
- 上下文：算法会演进且历史日期可能使用不同输入。
- 决策：recovery_scores 保存 score_version。
- 主要收益：Dashboard 可解释版本并支持回放。
- 主要代价：仍需未来增加模型配置版本。
- 评估过的替代方案：只保留当前公式结果。

## ADR-010 基线排除当天

- 状态：Completed。
- 上下文：当天进入自身统计会造成数据泄漏并减弱偏离。
- 决策：窗口只查询 target_date 之前的数据。
- 主要收益：比较基准独立于被评估值。
- 主要代价：首批日期数据不足。
- 评估过的替代方案：包含当天的滚动平均。

## ADR-011 median + MAD 处理异常值

- 状态：Completed。
- 上下文：HRV 与训练数据可能出现尖峰且样本窗口较小。
- 决策：优先采用 robust z-score 和 MAD。
- 主要收益：对极端值比均值标准差稳定。
- 主要代价：MAD 为零时需要 fallback。
- 评估过的替代方案：IQR、winsorize、仅 z-score。

## ADR-012 本地文件保存凭据

- 状态：Completed。
- 上下文：当前是单机开发且 Polar 使用 OAuth。
- 决策：Client 配置放 .env，token 放 data/polar_tokens.json。
- 主要收益：实现直接且不进入业务表。
- 主要代价：需要本机权限和备份纪律。
- 评估过的替代方案：系统钥匙串、云密钥服务。

## ADR-013 Dashboard 只读 SQLite

- 状态：Completed。
- 上下文：展示应稳定且不受 API 延迟影响。
- 决策：所有页面查询通过 dashboard_data 读取数据库。
- 主要收益：页面快速、离线可看、外部故障隔离。
- 主要代价：数据新鲜度依赖独立抓取任务。
- 评估过的替代方案：页面加载时实时抓取。

## ADR-014 使用 unittest

- 状态：Completed。
- 上下文：项目依赖轻量且标准库测试足以覆盖当前模块。
- 决策：以 unittest discover 作为统一测试入口。
- 主要收益：无需额外 runner，CI 迁移简单。
- 主要代价：高级 fixture 能力较少。
- 评估过的替代方案：pytest、nose。

## ADR-015 配置集中到 config

- 状态：Completed。
- 上下文：基线窗口和指标清单需要可审查。
- 决策：baseline 配置保存为 JSON。
- 主要收益：算法参数可见且测试可替换。
- 主要代价：配置 schema 当前靠代码验证。
- 评估过的替代方案：散落常量、数据库配置表。

## ADR-019 使用数据库内 migration ledger

- 状态：Completed。
- 上下文：Database Schema Version 已有统一版本源，但 SQLite 内缺少可审计迁移历史。
- 决策：在 recovery.db 中新增 `schema_migrations` 治理表，保存 sequence、SemVer、name、checksum 与 applied_at。
- 主要收益：旧库基线可登记、重复初始化可验证、版本漂移快速失败、后续 Confidence migration 有明确前置。
- 主要代价：所有未来 schema 变化必须维护不可变 migration fingerprint。
- 评估过的替代方案：仅使用 config 版本、外部 JSON ledger、依赖 PRAGMA user_version。

## 待决策事项

- 是否定义正式 App Version。
- 是否批准 ADR-016 至 ADR-018 并进入 Confidence 实现。
- 是否把 Polar cardio load 纳入日指标。
- 如何聚合 continuous heart rate。
- 是否建立一键流水线命令。
- 是否建立本地调度。
- Kubios 是否存在稳定自动化来源。
- AI Coach 具体云 provider、model、endpoint 和 processing region 是什么。
- Nutrition 数据来源是什么。
- Mobile App 是否需要云端同步。
- 数据库备份保留策略是什么。
- 历史评分是否支持多版本并存。

## ADR-016 Confidence 独立于 Recovery Score

- 状态：Completed。
- 上下文：数据缺失和历史不足表示不确定性，不表示恢复状态更差。
- 决策：Confidence 作为独立确定性结果，不进入 Recovery Engine v1.0 公式。
- 主要收益：保留评分语义，同时公开结果可靠程度。
- 主要代价：需要额外计算、持久化和展示契约。
- 评估过的替代方案：直接降低 recovery_score、只显示缺失字段。

## ADR-017 使用替代信号组计算完整性

- 状态：Completed。
- 上下文：Polar 与 Kubios 可以提供同类 HRV 和心率信号。
- 决策：同类来源组成 alternative group，任一有效来源即可完成该组。
- 主要收益：不会因未使用 Kubios 而重复惩罚已有完整 Polar 数据。
- 主要代价：多来源同时存在不会提高 completeness，只提高可解释性。
- 评估过的替代方案：逐字段等权、按来源固定配额。

## ADR-018 Confidence 使用独立版本和表

- 状态：Completed。
- 上下文：Confidence 公式和 Recovery Score 公式可能独立演进。
- 决策：使用统一 SemVer `1.0.0` 和独立 `recovery_confidence` 表。
- 主要收益：版本、迁移、回放和消费者边界清晰。
- 主要代价：需要日期级关联和新的 schema migration。
- 评估过的替代方案：向 recovery_scores 追加无版本 confidence 列。

## ADR-020 AI Coach 只消费最小化结构化事实

- 状态：Accepted。
- 上下文：健康 raw payload、凭据与无关历史不应进入生成式上下文。
- 决策：未来 AI Coach 仅通过只读 allowlist context builder 消费评分、置信度、聚合指标和确定性解释；raw JSON、token 与 secret 默认拒绝。
- 主要收益：减少隐私暴露、提示注入面和跨层耦合。
- 主要代价：解释范围受结构化字段约束。
- 评估过的替代方案：发送完整数据库、发送 raw payload、允许模型自行查询工具。

## ADR-021 AI Provider 与出站数据需要单独批准

- 状态：Accepted。
- 上下文：本地模型和云模型具有不同的隐私、留存、成本与运行风险。
- 决策：设计保持 provider-neutral；在明确批准 provider、字段 allowlist、区域、留存和训练使用政策前，不实现外部 API 或出站健康数据传输。
- 主要收益：用户保留数据控制权，设计完成不等同于隐私授权。
- 主要代价：实现阶段在批准前保持 Planned。
- 评估过的替代方案：预选云模型、静默发送最小 payload、仅依赖供应商默认条款。

## ADR-022 AI 输出使用版本化审计信封和确定性降级

- 状态：Accepted。
- 上下文：生成式文本不能保证可复现，且失败时不能影响稳定评分路径。
- 决策：未来输出使用 schema、model、prompt、安全策略和输入摘要版本；验证、模型或审计失败时 fail closed 到确定性解释。
- 主要收益：输出可追溯，失败不改变 Recovery、Confidence 或 Dashboard 数据。
- 主要代价：需要未来审计存储 migration 和额外验证层。
- 评估过的替代方案：只保存文本、不保存版本、模型失败时重算评分。

## ADR-023 AI Coach 采用云端 Zero Data Retention 路线

- 状态：Accepted。
- 上下文：用户批准云端模型，但具体 provider 与 model 尚未指定。
- 决策：未来使用具备 Zero Data Retention、禁用训练和禁用人工审阅能力的云端 API；任一条件无法验证则不发送请求。
- 主要收益：获得云模型能力，同时保留明确的 fail-closed 隐私门槛。
- 主要代价：provider、endpoint、region 和 model 仍需单独批准，可能限制可用供应商。
- 评估过的替代方案：本地模型、允许供应商默认保留、先集成后补隐私审批。

## ADR-024 云端输入白名单与分层保留政策

- 状态：Accepted。
- 上下文：解释需要有限健康上下文，但身份、raw 和长期历史并非必要。
- 决策：只发送 AI_COACH.md 的 closed schema；供应商零保留；本地有效输出保留 90 天，最小审计 metadata 保留 365 天，用户问题不按原文持久化。
- 主要收益：最小化暴露并兼顾近期审阅和版本审计。
- 主要代价：过期内容不可重放，需实现清理和删除证明。
- 评估过的替代方案：保存完整请求、永久保存建议、只保留内存不审计。

## ADR-025 审计 migration 与安全评估是运行前硬门禁

- 状态：Accepted。
- 上下文：生成式输出需要持久化审计，但不能与评分表耦合；平均质量分不能掩盖关键安全失败。
- 决策：未来 migration `0.4.0` 新增独立 `ai_coach_audit`；至少 200 个合成案例连续三次通过，关键安全项必须 100%，任一关键失败阻断发布。
- 主要收益：迁移可追踪、安全失败不可被平均值掩盖、业务表保持隔离。
- 主要代价：实现和发布前验证成本增加。
- 评估过的替代方案：复用 recovery_scores、仅写日志、以单次平均分放行。

## ADR-026 当前云供应商选型保持 Blocked

- 状态：Accepted。
- 上下文：OpenAI API 当前不支持中国大陆访问且 ZDR 需事先审批；已核验的中国大陆候选未提供满足本项目硬门槛的公开零保留证据。
- 决策：不批准任何当前候选，不降低 ZDR、地区合规、禁训练或禁人工审阅门槛；通过企业合同证据或受支持地区 ZDR 项目解锁。
- 主要收益：避免通过代理或模糊隐私声明处理健康上下文。
- 主要代价：AI Coach runtime 保持 blocked，无法立即接入云模型。
- 评估过的替代方案：OpenAI 非支持地区访问、把“不训练”等同于“不保留”、无证据批准国内供应商。

## ADR-027 使用全通过的供应商尽调门禁

- 状态：Accepted。
- 上下文：公开隐私说明不足以证明具体 endpoint、snapshot、region 和企业账号控制满足健康数据边界。
- 决策：使用版本化 DD-01 至 DD-24 问卷和证据包；全部 mandatory gate 必须 PASS，UNKNOWN、PARTIAL 或 EXCEPTION 均不授权实现。
- 主要收益：供应商承诺可追溯，缺失证据不会被加权平均掩盖。
- 主要代价：需要 Product Owner 获取企业合同材料并至少每年复核。
- 评估过的替代方案：销售口头承诺、加权评分放行、先发送真实数据再观察。

## ADR-028 AI Coach 使用 fail-closed 分层威胁控制

- 状态：Accepted。
- 上下文：健康上下文跨越本地数据库、出站网络、外部模型、审计和展示边界，单一 prompt 无法承担安全控制。
- 决策：采用 TM-01 至 TM-18 威胁登记和 TB-1 至 TB-7 信任边界；Critical/High residual risk 不得发布，配置或控制异常统一降级到确定性功能。
- 主要收益：预防、检测、响应和验证责任可映射到具体实现层。
- 主要代价：未来 adapter、migration 和 UI 必须实现额外门禁与测试。
- 评估过的替代方案：仅依赖供应商安全、仅做 prompt 防护、异常继续显示部分输出。

## ADR-029 AI Coach 契约使用版本化 JSON Schema 与纯验证器

- 状态：Completed。
- 上下文：文字 allowlist 无法直接阻止 unknown fields、类型漂移或不可信模型输出进入后续层。
- 决策：prompt/output/safety contract 均为 `1.0.0`；输入输出使用 deny-unknown JSON Schema，并由无网络、无数据库依赖的本地纯验证器 fail closed。
- 主要收益：provider-independent、可测试、错误不回显 payload、版本漂移可立即阻止。
- 主要代价：字段变化需要显式版本升级和 schema/test 同步。
- 评估过的替代方案：仅靠 prompt、provider SDK 自动解析、宽松字典透传。

## ADR-030 语义安全失败统一返回确定性 fallback

- 状态：Completed。
- 上下文：Schema 合法不代表证据真实、医疗表达安全或语言与 Confidence 一致。
- 决策：本地语义门校验证据引用、数字、诊断、用药、Confidence 和紧急升级；任一失败返回无生成式 action 的确定性 fallback，并使用 HMAC 输入摘要。
- 主要收益：模型错误不会进入审计/展示，云端不可用不影响确定性功能。
- 主要代价：关键词门禁可能保守拒绝，未来需用合成评估持续校准。
- 评估过的替代方案：只依赖 JSON Schema、只显示警告但保留模型输出、异常返回空页面。

## ADR-031 本地安全预检与未来模型评估分离

- 状态：Completed。
- 上下文：Provider 阻塞期间仍需验证安全层规模化行为，但没有 exact snapshot 就不能声称模型评估通过。
- 决策：固定 200 个合成案例、8 类场景、连续 3 轮验证本地 pass/fallback expectation；报告仅聚合，并明确标记 `local_preflight_only` 与 `model_version=unreleased`。
- 主要收益：提前发现安全层回归，未来模型评估可复用分类和阈值。
- 主要代价：本地预检不能衡量模型质量、延迟或 provider 行为。
- 评估过的替代方案：等待 provider 后再测试、把单元测试冒充模型评估、记录完整合成 prompt/output。

## ADR-032 云端调用使用默认拒绝的机器审批记录

- 状态：Completed。
- 上下文：文档中的 blocked 状态无法独自阻止未来误配置 API Key 或 adapter 后发送数据。
- 决策：机器记录默认 blocked/authorization false；只有 exact provider/model/HTTPS endpoint/region、全部控制、双审批、有效证据和匹配 fingerprint 才允许调用。
- 主要收益：部分配置、过期和 drift 在健康上下文序列化前 fail closed。
- 主要代价：供应商或契约变化必须重新生成审批 fingerprint。
- 评估过的替代方案：仅环境变量开关、API Key 存在即启用、单人审批、运行后再检查区域。

## ADR-033 出站上下文使用显式投影且授权先于构建

- 状态：Completed。
- 上下文：即使最终 Schema 严格，宽松查询结果或 caller-supplied versions 仍可能扩大出站对象。
- 决策：TB-2 builder 只接受 closed source fields，深拷贝并注入权威版本；provider-bound 入口先检查 approval，再构建 context。
- 主要收益：blocked 状态下不构造健康上下文，raw/精确字段/版本伪造在本地失败。
- 主要代价：上游未来必须显式提供已分箱字段，不能透传数据库 Row。
- 评估过的替代方案：序列化整个 Row 后删除字段、忽略 unknown fields、让 caller 传版本。

## ADR-034 本地准备与云端 Runtime Ready 使用独立状态

- 状态：Completed。
- 上下文：大量本地测试通过可能被误读为 provider/model 已可上线。
- 决策：readiness gate 分开报告 local pre-provider 与 runtime；runtime 必须同时通过七项门禁并支持 `--require-runtime` 强制失败。
- 主要收益：本地进展可验证，同时不会掩盖 provider、migration、adapter 或 exact-model 缺口。
- 主要代价：未来每个 runtime artifact 都必须维护机器可验证状态。
- 评估过的替代方案：单一 ready 标志、以测试总数判断、人工阅读 HANDOFF 判断。

## ADR-035 Local Coach 与 Cloud AI Coach 使用独立运行路径

- 状态：Accepted。
- 决策：Local Coach 只读确定性 Recovery、Baseline、Confidence 和解释结果，只写入独立建议表。
- 理由：在不外发健康数据的前提下提供可解释建议，不绕过云端审批门禁。
- 结果：Schema `0.4.0` 属于 Local Coach，不代表 Cloud AI audit migration 已实现。

## ADR-036 Personal Logging 与手动 AI Context Export 保持本地边界

- 状态：Accepted。
- 决策：用户输入写入独立 Personal Logging 表；Polar 与手动训练并列，
  自动关联不自动确认；AI Context 只导出白名单汇总并由用户手动上传。
- 理由：增加可分析上下文，同时不绕过 provider、隐私或 Cloud Runtime 门禁。
- 结果：manual sync ready 为 true，automatic cloud sync 和 cloud runtime 保持 false。

## ADR-037 国际化使用统一显示层与稳定内部代码

- 状态：Accepted。
- 决策：语言资源使用相同键的 UTF-8 JSON；所有主要 Streamlit 文本通过统一 translator；数据库、JSON/CSV 机器字段和 enum 继续使用稳定英文代码。
- 理由：允许即时切换与后续扩展，同时不让语言影响计算、存储或机器处理。
- 结果：偏好仅存本地语言代码；报告按语言目录输出；缺失翻译明确 fallback。

## ADR-038 Kubios HRV 采用三层模型与确认式来源选择

- 状态：Completed。
- 上下文：CSV、截图和手工录入可能在同日产生不同完整度的 Kubios 记录。
- 决策：使用 raw / normalized / derived 三层；默认优先级为 CSV、已复核截图、已复核手工录入；两张互补截图仅在用户明确确认同一次测量后合并非空字段。
- 主要收益：保留全部来源证据，统一下游投影，不需猜测缺失值。
- 主要代价：增加 schema、版本化 builder 和用户确认步骤。
- 边界：不改变 Recovery、Confidence 或 Local Coach 公式；不将原始 OCR、图片、路径或 raw JSON 送入 AI Context。

## ADR-039 训练记录保留完整模型并默认简单录入

- 状态：Completed。
- 上下文：结构化训练表能支持专业字段，但同时展示使日常和窄屏录入拥挤。
- 决策：数据库与服务契约保持完整；界面默认 Simple，Advanced 与各 measurement mode 按需显示；隐藏值不删除，RPE/RIR 不换算。
- 理由：降低补录成本，同时保留科研、舞蹈、康复和未来 AI 分析语义。
- 边界：不修改训练容量、Recovery、Baseline、Confidence、Polar 或 AI Runtime。

## ADR-048 今日恢复详情与历史恢复评分分离（2026-07-23）

- 状态：Completed。
- 上下文：原始晨测表格和长期基线不能直接表达今天的恢复状态；现有
  Recovery Score 已有 0–100 公式，但这次需求要求在验证前不强行生成新分数。
- 决策：新增无数据库表的 `recovery_details` 解释层，复用已解析的晨测历史、
  28 天中位数/MAD 基线和质量语义；当前日期不进入比较窗口。基线不足时只显示
  当前值和建立进度，正负信号冲突时返回“恢复信号不一致”。
- 质量：详情层在分析边界兼容旧大写质量值，并统一为
  `excellent/good/average/poor/unusable/missing`；只有 excellent/good 记录进入
  基线，NULL、无效值和呼吸频率 0 均保持缺失。
- 结果：原始数据、今日解释、个人长期基线职责分离；既不修改旧评分含义，也不
  需要数据库迁移。
