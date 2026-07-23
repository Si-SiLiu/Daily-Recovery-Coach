# Recovery Engine

## Sleep regularity separation (2.0.0)

Sleep regularity is an independent sleep-timing signal. It is not sleep
quality, sleep sufficiency, sleep score, or recovery status. The regularity
engine uses its own versioned parameters and does not change Recovery Engine
1.0.0 scoring.

## Training-load boundary

Training heat from Polar remains a training-analysis field and is not added
again to Polar daily total calories. The Training Load & Habits projection is
separate from Recovery Score calculation and does not change recovery scoring.

## Kubios Data Model 1.0 boundary

The new Kubios raw, normalized, derived, PNS/SNS, SDNN, stress, respiration,
quality, and frequency-domain fields do not change Recovery Engine 1.0.0.
Only the previously approved legacy daily inputs remain active. Any future use
of new Kubios metrics requires a separate ADR, formula version, validation, and
release gate.

> Deterministic personal recovery scoring design.
> Current highest implemented version: v1.0.
> Decision support only; not medical diagnosis.
> Verified: 2026-07-10.

## 定位

- 确定性评分层。
- 最高实现版本 v1.0。
- 读取日指标。
- 读取个人基线。
- 写入 recovery_scores。
- 不依赖 Streamlit。
- 不调用外部 API。
- 不调用生成式 AI。

## 输出契约

- recovery_score 为 0–100。
- activity_load_score 为 0–100。
- training_load_score 为 0–100。
- hrv_score 可为空。
- morning_hr_score 可为空。
- readiness_score 可为空。
- score_version 必填。
- recommendation 必填。

## v0.1

- 只使用活动和训练负荷。
- steps 静态范围 3000–15000。
- active calories 范围 300–1800。
- 活动权重 45% 与 55%。
- 训练 duration 范围 20–120 分钟。
- 训练 calories 范围 150–1000。
- 训练权重 55% 与 45%。
- 作为历史不足 fallback。

## v0.2

- 融合 Kubios 晨测。
- 使用 morning_rmssd。
- 使用 morning_mean_hr。
- 使用 kubios_readiness。
- 可用恢复项取平均。
- 恢复能力权重 70%。
- 负荷恢复权重 30%。
- Kubios 缺失时不选择该版本。

## v0.3

- 融合 Polar 夜间恢复。
- 使用 nightly_hrv_rmssd。
- 使用 sleep_score。
- 使用 nightly_resting_hr。
- 可用恢复项取平均。
- 恢复能力权重 65%。
- 负荷恢复权重 35%。
- Polar 恢复缺失时不选择该版本。

## Recovery Capacity

- HRV 代表恢复信号。
- 夜间和晨测 RMSSD 可并用。
- 静息与晨测心率方向相反。
- 呼吸频率作为当前心率组输入。
- 睡眠评分进入 readiness 组。
- 睡眠时长进入 readiness 组。
- Kubios readiness 进入 readiness 组。
- 可用分项允许部分计算。

## Stress Load

- steps 代表日常活动量。
- active calories 代表活动消耗。
- training duration 代表训练时长。
- training calories 代表训练消耗。
- 高于个人基线映射更高负荷。
- 活动总权重 60%。
- 训练总权重 40%。
- 高负荷不是医学异常。

## v1.0 基线映射

- higher_is_better 中心分 75。
- lower_is_better 反转偏离方向。
- higher_is_load 中心分 50。
- 每个偏离单位乘 15。
- 优先 robust_z_score。
- 其次 z_score。
- 最后 percent_change / 10。
- 所有结果 clamp 到 0–100。

## v1.0 总公式

- 活动分取可用活动项平均。
- 训练分取可用训练项平均。
- total_load = activity×0.6 + training×0.4。
- load_recovery = 100 − total_load。
- capacity 取可用恢复组平均。
- 有 capacity 时权重 65% 与 35%。
- 无 capacity 时只用 load_recovery。
- 最终分四舍五入为整数。

## Baseline

- 默认窗口 28 天。
- 至少 7 个有效历史日。
- 窗口排除当天。
- 负数不进入统计。
- duration 先统一单位。
- 异常值用 median + MAD。
- 保存标准与稳健 z 分数。
- 数据不足写 insufficient_data。

## Recommendation

- 80–100 正常训练。
- 60–79 适度训练。
- 40–59 减量训练。
- 0–39 恢复优先。
- 由最终整数分生成。
- 不判断疾病。
- 不判断伤病。
- 需要结合个人主观感受。

## 缺失处理

- 全部 baseline 缺失时 fallback。
- 只有 Polar HRV 可部分计算。
- 只有 Kubios HRV 可部分计算。
- 睡眠缺失跳过睡眠项。
- readiness 不可解析时跳过。
- 负荷组缺失时使用旧分项。
- NULL 不伪造成健康值。
- 真实零值与 NULL 区分。

## Data Completeness

- 当前通过 NULL 表达缺失。
- 通过 valid_days 表达历史数量。
- 通过 status 表达基线可用性。
- Dashboard 展示数据缺口。
- 未来区分未授权与无记录。
- 未来区分抓取与导入失败。
- 完整性不等于恢复分。
- 当前公式不加入 completeness。

## Confidence

- Confidence 是 Recovery Engine 的独立旁路结果，不进入 v1.0 评分公式。
- Data Completeness、Baseline Maturity、公式和拟议数据契约见
  [CONFIDENCE_ENGINE.md](CONFIDENCE_ENGINE.md)。
- 当前只完成设计，尚未创建表或实现计算模块。

## Explainability

- 解释层不重算分数。
- 读取 baseline status。
- 读取 percent_change。
- 按指标方向判断影响。
- 按偏离强度排序。
- 数据不足列为缺口。
- 显示个人中位数。
- 不声明医学因果。

## Future AI Coach

- 位于 Recovery Engine 下游。
- 输入结构化评分事实。
- 读取 score_version。
- 读取数据完整性。
- 不读取 token。
- 不默认读取 raw_json。
- 不计算 recovery_score。
- 不覆盖 recovery_scores。

## 安全边界

- 仅用于个人训练决策辅助。
- 不是医疗诊断。
- 异常身体信号应寻求专业帮助。
- 日志不输出 token。
- 报告不输出 raw_json。
- Dashboard 不访问 Polar。
- AI 不访问授权文件。
- 历史评分必须可追溯。

## 测试要求

- 测试评分范围。
- 测试推荐边界。
- 测试各 fallback 版本。
- 测试高低方向。
- 测试基线不足。
- 测试 MAD 与 std 为零。
- 测试重复 upsert。
- 全量 unittest 必须通过。

## 变更协议

- 公式变化定义新引擎版本。
- 权重变化记录决策。
- 输入变化更新数据字典。
- schema 变化更新数据库文档。
- 推荐变化更新 changelog。
- 新版本做历史回放。
- 不得静默改写旧版本含义。
- Product Owner 最终验收。

## Today's Recovery Details Engine 1.0.0

The Recovery page now has a separate interpretable details layer below the raw
"Today's Recovery Data" table. It reuses resolved morning RMSSD and resting-HR
values and applies the same 28-day personal-baseline contract to stress index
and respiration rate. The current date is excluded from its comparison window;
only valid values from records with `excellent` or `good` measurement quality
enter the baseline. Legacy `GOOD`, `ACCEPTABLE`, `POOR`, and `INVALID` values
are normalized at the display/analysis boundary for backward-compatible reads.

The center is the median. The common range is median ± 1.4826 × MAD, with an
IQR/min–max fallback when MAD is zero. Invalid `NULL`, non-finite, and
non-positive respiration values never become zero and never enter the baseline.
Maturity is collecting (<7 valid days), provisional (7–13), reliable (14–27),
or stable (28+). Before 7 valid days the details layer returns `基线建立中`
and does not issue a definitive recovery conclusion.

The layer intentionally does not call the legacy 0–100 Recovery Score. RMSSD
and resting-HR direction rules are asymmetric, stress is auxiliary, and
respiration uses bilateral deviation. Conflicting positive and negative
signals return `恢复信号不一致`; quality and maturity affect confidence.
This is decision support only, not a diagnosis or injury prediction.

## 当前事实

- 当前引擎版本、评分天数和基线记录数属于运行状态。
- 请以 [project_state.json](../project_state.json) 为机器权威来源。
- 本文只维护各 Recovery Engine 版本的算法语义和变更协议。
