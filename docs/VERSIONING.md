# Versioning

Release `0.26.0` adds Training Logging `1.0.0`, Exercise Catalog `1.0.0`,
Database Schema `0.14.0`, Dashboard `1.7.0`, and AI Context Export `1.3.0`.
Recovery, Baseline and Confidence remain `1.0.0`; the cloud model remains
`unreleased`.

Release `0.19.0` adds Scheduler, Manual Logging, Nutrition Logging, and Data
Resolution `1.0.0`, Database Schema `0.8.0`, and Dashboard `1.0.0`. Recovery,
Baseline, Confidence, and Local Coach remain `1.0.0`; cloud `model_version`
remains `unreleased`.

> Independent version rules for the app, algorithms, database, UI, and future AI models.
> Effective: 2026-07-10.

## 目标

- 区分应用、算法、数据库、Dashboard 和模型版本。
- 避免一个版本号承担所有含义。
- 让历史评分可解释。
- 让数据库迁移可追踪。
- 让 UI 行为变化可发布。
- 让 AI 输出可审计。
- 版本必须随结果或发布物保存。
- 当前缺失版本要明确标记。
- 不能伪造未发布 tag。
- 规则自 2026-07-10 生效。

## 版本类别

- App Version 描述整体产品发布。
- Recovery Engine Version 描述评分公式。
- Database Schema Version 描述结构迁移。
- Dashboard Version 描述页面契约。
- Model Version 描述未来 AI 模型与提示词。
- Config Version 可描述算法配置。
- API Contract Version 可描述未来服务接口。
- 数据日期不是版本。
- Git commit 不是用户版本。
- 各类别独立演进。

## App Version

- 建议使用 Semantic Versioning。
- 格式 MAJOR.MINOR.PATCH。
- MAJOR 表示不兼容产品行为。
- MINOR 表示向后兼容功能。
- PATCH 表示向后兼容修复。
- 当前 App Version 是 pre-1.0 语义版本。
- 唯一运行时来源是 [config/versions.json](../config/versions.json)。
- README 只提供查看命令，不复制当前值。
- CURRENT_STATE 的当前值只能由状态脚本生成。

## Recovery Engine Version

- 统一版本源使用 MAJOR.MINOR.PATCH。
- 数据库历史 `score_version` 可继续保留旧的 `vMAJOR.MINOR` 标签。
- v0.1 是活动训练负荷版。
- v0.2 是 Kubios 晨测融合版。
- v0.3 是 Polar 夜间融合版。
- v1.0 是个人基线版。
- 版本保存在 recovery_scores.score_version。
- 公式或权重变化至少提升 MINOR。
- 含义不兼容变化提升 MAJOR。
- 文本修正不改变公式时可不升引擎版本。

## Confidence Engine Version

- Confidence 使用独立于 Recovery Engine 的版本命名。
- 首个已实现版本为 `1.0.0`（历史内部标签可保留 `confidence-v1.0`）。
- group weights、完整性规则、成熟度公式或 level 边界变化需要新版本。
- 只修改 Dashboard 文案不改变 Confidence Engine Version。
- Confidence 版本必须与持久化结果一起保存。
- Confidence Engine 1.0.0 已实现并持久化；本阶段没有修改其公式。
- 详细设计见 [CONFIDENCE_ENGINE.md](CONFIDENCE_ENGINE.md)。

## Recovery 版本触发

- 新增输入指标可能需要新版本。
- 改变指标方向需要新版本。
- 改变 baseline 窗口需要新版本。
- 改变最低有效日需要新版本。
- 改变异常值策略需要新版本。
- 改变权重需要新版本。
- 改变推荐区间需要新版本。
- 只修复显示不需要新评分版本。
- 只增加解释不需要新评分版本。
- fallback 行为变化需要评审版本。

## Database Schema Version

- 当前采用 SemVer，值由统一版本源管理。
- `schema_migrations` 持久化 sequence、SemVer、name、checksum 和 applied_at。
- 现有结构登记为 baseline migration，ledger 本身登记为下一 migration。
- 版本机制已经建立并用于所有正式迁移。
- 每个迁移对应唯一编号。
- 迁移只向前执行一次。
- 版本记录写在数据库内部。
- 代码应声明支持的最小 schema。
- 复杂迁移前备份数据库。
- CURRENT_STATE 只显示自动生成的当前 schema version。
- project_state 同时记录 migration count 与 ledger 最新版本。
- config 版本与 ledger 最新版本不一致时状态生成失败。

## Schema 版本触发

- 新增表提升 schema version。
- 新增列提升 schema version。
- 删除列提升 schema version。
- 重命名列提升 schema version。
- 改变唯一键提升 schema version。
- 新增重要索引提升 schema version。
- 数据回填随迁移记录。
- 仅更新行数据不提升 schema version。
- 重建评分不是 schema 变化。
- 重建 baseline 不是 schema 变化。

## Dashboard Version

- 统一版本源使用 MAJOR.MINOR.PATCH。
- Dashboard 已有独立版本并从统一版本源读取。
- 重大导航变化提升 MAJOR。
- 新增兼容展示模块提升 MINOR。
- 样式或兼容修复提升 PATCH。
- 页面应展示 Recovery Engine Version 而非混淆。
- Dashboard 版本不改变评分含义。
- 未来移动端有独立客户端版本。
- CURRENT_STATE 与 Dashboard 都从统一版本源的派生状态显示版本。

## Model Version

- AI Coach 架构已设计，但运行模块未开发，统一版本源保持 `unreleased`。
- 模型供应商名称不是完整版本。
- 应记录具体模型标识。
- 应记录 prompt template version。
- 应记录 output schema version 与 tools contract version；首版不得启用工具。
- 应记录安全策略版本。
- 应记录 allowlisted input snapshot digest。
- 输出应保存 model_version。
- 模型版本不等于 Recovery Engine Version。
- 模型升级不能静默改变历史解释。
- 纯设计阶段不提升 App、Engine、Database 或 Dashboard runtime 版本。
- 云端治理批准仍不发布 runtime model，`model_version` 保持 `unreleased`。
- 未来云端审计表必须使用高于当前 schema 的新迁移版本；旧设计中的
  `0.4.0` 已被 Local Coach 使用，不得复用。
- AI Coach prompt、output schema 和 safety policy 使用独立
  `config/ai_coach_contract.json`，当前均为 `1.0.0`。
- 这些契约版本不表示 provider/model 已发布；`model_version` 继续为 `unreleased`。
- 任一契约版本变化必须同步对应 JSON Schema、测试、安全评估和历史审计解释。

## Config Version

- baseline_config 当前无显式 version 字段。
- 未来算法配置可增加 config_version。
- 窗口、阈值和指标清单需要追踪。
- 配置版本应与评分结果关联或可回放。
- 纯展示配置无需算法 config version。
- 配置校验失败应快速停止。
- 旧配置应保留用于历史回放。
- 配置变化写入 CHANGELOG。
- 关键变化写入 DECISIONS。
- 当前 v1.0 假定现有配置。

## API Contract Version

- 当前没有公共 REST API。
- Polar API 版本由外部平台定义。
- 内部 Python 方法不是公共网络契约。
- 未来移动端需要稳定 API version。
- 建议 URL 或 header 明确版本。
- 破坏性字段变化提升 API major。
- 新增可选字段可提升 minor。
- 错误对象也属于契约。
- AI API 与数据 API 可独立版本。
- API.md 记录当前接口。

## 当前版本矩阵

- [config/versions.json](../config/versions.json) 是 App、Recovery Engine、
  Baseline Engine、Database Schema、Dashboard 与 Model Version 的唯一权威。
- [project_state.json](../project_state.json) 自动读取并镜像统一版本源。
- [CURRENT_STATE.md](CURRENT_STATE.md) 的生成区和 Dashboard System Status
  都只消费派生状态，不手工复制版本。
- 当前正式快照见 [releases](../releases/README.md)。
- 除未来模型可明确使用 `unreleased` 外，所有当前版本必须通过 SemVer 校验。
- One-Click Sync 属于 App 的向后兼容功能，因此提升 App MINOR。
- Dashboard 新增只读 Last Sync 契约时独立提升 Dashboard MINOR。
- 独立 `sync_history.db` 是运维状态，不改变 recovery database schema version。
- Confidence Engine 使用独立 `confidence_engine_version` SemVer。
- Confidence 公式或组权重变化独立提升 Confidence Engine 版本。
- `recovery_confidence` migration 提升 Database Schema Version。
- Pipeline 失败语义与安全错误修复提升 App PATCH。
- Dashboard 在 System Status 显示 endpoint warning count 时提升 Dashboard PATCH。

## 发布前检查

- 更新 App Version。
- 更新 CURRENT_STATE。
- 更新 ROADMAP 状态。
- 更新 CHANGELOG。
- 确认 Recovery Engine Version。
- 确认 Database Schema Version。
- 确认 Dashboard Version。
- 运行全量测试。
- 备份真实数据库。
- 检查 secret 与 token 未提交。

## 发布标签

- Git tag 建议使用 app-vX.Y.Z。
- 评分版本不单独作为 Git tag 必需条件。
- 数据库迁移应在 release notes 列出。
- 预发布可用 -alpha、-beta 或 -rc。
- tag 必须指向已验证 commit。
- 不得移动已发布 tag。
- 修复发布创建新 PATCH tag。
- 文档快照随 tag 保存。
- 本地实验不创建正式 tag。
- Product Owner 批准正式发布。

## 兼容性

- 新代码应读取旧 score_version。
- Dashboard 对未知版本提供通用说明。
- 数据库迁移支持已有本地库。
- raw JSON 映射兼容常见字段别名。
- API 错误不破坏已有数据库。
- 旧报告不需要被覆盖。
- 新算法不应静默重写历史含义。
- 回填历史评分必须记录使用版本。
- 删除兼容路径需要迁移计划。
- 兼容期写入 ROADMAP。

## 版本与数据

- date 表示被评估日期。
- created_at 表示结果首次生成。
- updated_at 表示结果最近重算。
- score_version 表示算法。
- window_days 表示基线配置的一部分。
- 模型版本表示解释生成器。
- 重叠展示/导出字段将来源、原因、fallback、override 与解析规则版本
  保存在 `resolved_daily_fields`；原始来源版本仍由 raw 证据保留。
- raw_json 保留来源证据。
- 同一日期可能因重算更新。
- 重算不等于新 App release。

## 版本与 Changelog

- Added 记录新能力。
- Changed 记录行为变化。
- Fixed 记录缺陷修复。
- Tests 记录验证变化。
- Security 记录安全修复。
- Breaking 明确不兼容变化。
- 每个发布有日期。
- Unreleased 收集未发布变化。
- 版本标签与 changelog 标题一致。
- 历史条目不删除。

## 版本与测试

- 每个评分版本有独立测试。
- 迁移版本有升级测试。
- Dashboard 版本有页面测试。
- AI 模型版本未来有契约测试。
- 旧版本 fallback 保持回归测试。
- 版本字符串必须断言。
- 未知版本展示必须测试。
- 发布前记录测试数量。
- 测试失败不能发布。
- 仅文档发布也检查链接。

## 升级流程

- 提出版本变化原因。
- 识别受影响版本类别。
- 记录 DECISION。
- 实现兼容或迁移。
- 增加测试。
- 历史数据回放。
- 更新专题文档。
- 更新 CURRENT_STATE。
- 更新 CHANGELOG。
- Product Owner 验收。

## 回滚原则

- 代码回滚不自动回滚数据库。
- 数据库回滚需要备份恢复计划。
- 评分结果可通过旧算法重建时要保留代码。
- Dashboard 回滚不影响评分表。
- AI 模型回滚不改 Recovery Engine。
- 回滚原因写入 CHANGELOG。
- 安全事件可紧急停用外部接口。
- 不得使用破坏性 Git 命令覆盖用户数据。
- 回滚后重新运行测试。
- 回滚完成更新当前状态。

## 持续维护

- 每次阶段完成检查版本矩阵。
- 每次评分变化检查引擎版本。
- 每次 schema 变化检查数据库版本。
- 每次页面发布检查 Dashboard Version。
- 每次 AI 模型变化检查 Model Version。
- 每次正式发布检查 App Version。
- 避免用“最新版”替代具体版本。
- 文档注明核验日期。
- 版本来源必须可查询。
- 未知状态明确写 Unknown 或 Unversioned。
