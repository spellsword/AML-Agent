# 02 · Agent 规格说明书

> 每个 Agent 按「角色 / 输入 / 输出 / 提示骨架 / 失败模式 / 验收」六段定义。
>
> **提示骨架是结构与纪律，不是最终文案**。最终文案走版本化审批（`promptVersion`）。骨架中不得出现任何阈值数字——阈值一律从 `scenario_knowledge.json` 运行时注入。

---

## 通用提示结构（两层架构，TSD §2.2.3.1）

所有 Agent 提示由两层组成：

```
[第 1 层] 通用原则 —— 跨场景推理纪律，从 scenario_knowledge.genericPrinciples 注入
           永不含具体场景/案件内容
[第 2 层] 场景知识 —— 红旗、豁免条件、经营手法、分析指引，从场景条目注入
           永不含个案证据
[数据层] 案件证据 —— 已掩码的案件上下文
```

**三层隔离是硬约束**：提示里不能同时出现"个案证据"与"硬编码知识"。否则知识无法影子测试、无法版本化。

### 全 Agent 通用纪律段（注入每一条提示）

```
- 你的输出必须是严格 JSON，符合给定 schema。禁止输出 schema 之外的任何文本。
- 每一条实质性主张必须携带至少一个 evidenceRef，且该引用必须来自提供的证据集合。
  无法用证据支撑的内容不得作为主张输出；应写入 namedUnknowns。
- 输出不得包含未脱敏的个人身份信息。使用代理令牌（如 [CUSTOMER_1]）。
- 使用完整术语，不得使用缩写。
- 证据不足时，输出 RFI 建议并列出需补充的具体信息，不得猜测填补。
- 你的输出是给人工复核的建议，不是最终裁定。
```

---

## A1 · Data Parser Agent

**角色**：把原始证据包归一为内部 `CaseModel`，供下游全部 Agent 使用。不做判断。

**输入**：符合 `evidence_pack.schema.json` 的 JSON。

**输出**：
```json
{
  "caseId": "...",
  "jurisdiction": "MY",
  "customer": { "代理化后的客户画像" },
  "accounts": [...],
  "transactionSummary": {
    "windowStart": "...", "windowEnd": "...",
    "totalCredit": 0, "totalDebit": 0,
    "transactionCount": 0,
    "topCounterparties": [...],
    "channels": {...},
    "truncated": false
    },
  "ubo": [...],
  "screening": {...},
  "nnsSummary": {...},
  "priorAlertSummary": {...},
  "evidenceLedger": [ { "evidenceId": "EVID-...", "sourceType": "...", "summary": "...", "citationText": "..." } ]
}
```

**关键实现点**：
- **证据台账在此生成**，`evidenceId` 从此分配。所有下游 Agent 只能引用台账中的 ID。分配规则：`EVID-{来源类型码}-{序号}`，如 `EVID-TXN-001`、`EVID-KYC-003`。
- 辖区缺失或不可解析 → **fail-closed 直接抛错**，不得降级为"不过滤"（TSD §2.2.6）。
- 交易超过 5000 条 → 截断并置 `truncated=true`，同时在台账中登记一条 `policy` 类证据说明截断。
- 计算 `transactionSummary` 时的聚合口径必须写进 `citationText`，供下游引用。

**失败模式**：辖区缺失 → fail-closed；schema 校验失败 → 抛 `LLM-CONTRACT-INVALID` 等价错误并终止分析。

---

## A2 · Search Agent（NNS）

**角色**：读取检索证据摘要，结构化为可引用条目。POC 不发起真实检索。

**输入**：`CaseModel.searchEvidence`。

**输出**：
```json
{
  "searchesPerformed": [
    { "searchId": "...", "query": "...", "resultCount": 0,
      "adverseCount": 0,
      "findings": [
        { "finding": "...", "relevance": "Adverse", "evidenceRefs": ["EVID-NNS-001"],
          "publishedAt": "...", "sourceRef": "..." }
      ] }
  ],
  "overallAdverseSignal": "none|low|medium|high",
  "adjudicationNotes": "..."
}
```

**关键实现点**：
- POC 阶段**只读 fixture，绝不外呼**。代码中不得出现 HTTP 客户端。
- 每条 finding 必须绑定截图引用（`screenshotRef`）——TSD §2.2.2 要求网页证据由无头浏览器截图留证。
- 检索为空与检索失败必须区分：空 → "无不利结果"；失败 → 记为证据缺口，支撑 RFI，不等于无风险。

---

## A3 · Risk Analyzer Agent

**角色**：计算检测度量并求值。这是**确定性计算环节，不是 LLM 环节**。

**输入**：`CaseModel` + 场景知识条目的 `detectionMetrics`。

**输出**：
```json
{
  "scenarioCode": "SCN110",
  "metrics": [
    { "metricKey": "flow_through_rate", "label": "资金流通率",
      "observed": 0.94, "operator": ">=", "threshold": 0.9, "unit": "ratio",
      "hit": true, "featureContribution": 0.31,
      "evidenceRefs": ["EVID-TXN-001"],
      "computeExplanation": "窗口期内流出总额 / 流入总额 = 4.7M / 5.0M" }
  ],
  "hitCount": 4,
  "escalationGate": 3,
  "gateOutcome": "exceeds_gate|at_gate|below_gate",
  "evidenceGaps": ["缺少对手方关系说明"]
}
```

**关键实现点**：
- **这是纯函数，不调用 LLM。** 这是刻意的设计：TSD §2.2.7(a) 规定规则类打分的特征贡献是"按构造精确"的——贡献值就是公式里的那一项。把确定性计算交给 LLM 会破坏这一精确性声明。
- `featureContribution` 必须由公式项计算得出，不是模型估计。
- 阈值一律从 `scenario_knowledge.json` 读取，代码中不得出现数字常量。
- `hitCount` 与 `gateOutcome` 直接决定倾向，但**不直接决定最终建议**——Judge 仍可基于豁免条件给出不同判断，且必须在 `decisiveFactors` 中说明。

---

## A4 · Detective Agent

**角色**：建立事实基础与证据覆盖。不作倾向性判断——这是它与 Prosecutor/Defender 的根本区别。

**输入**：`CaseModel` + A3 的度量结果 + 场景知识。

**输出**：
```json
{
  "facts": [
    { "statement": "窗口期内累计流出 MYR 4,700,000", "evidenceRefs": ["EVID-TXN-001"] }
  ],
  "redFlags": [
    { "code": "RF-110-01", "description": "...", "evidenceRefs": ["EVID-KYC-002"] }
  ],
  "metricEvaluations": [ /* 引用 A3 结果 */ ],
  "evidenceCoverage": {
    "evidenceCatalogued": 12, "redFlagsIdentified": 4,
    "gaps": ["无对手方商业背景单据", "无发票佐证"]
  }
}
```

**关键实现点**：
- 每条 fact 必须带引用；无证据的事实不得输出。
- `gaps` 是 RFI 建议的主要来源之一，必须如实填写，不得为让案件看起来完整而省略。
- Detective **不做倾向性表述**。提示骨架需明确禁止 "suspicious" / "suspicious-looking" 这类定性词。

---

## A5 · Prosecutor Agent

**角色**：构造**最强**的升级论证。目标是尽力证明应当升级。

**输入**：`CaseModel` + Detective 输出 + A3 度量 + 场景知识（红旗 + 豁免条件 + 经营手法）。

**输出**：
```json
{
  "position": "Escalate",
  "coreThesis": "...",
  "arguments": [
    { "claim": "客户申报周转额显著低于实际资金流量，财务能力不足以支撑该活动",
      "evidenceRefs": ["EVID-KYC-001", "EVID-TXN-002"],
      "ruleCode": "RF-110-01", "weight": "primary" }
  ],
  "alternativeExplanations": [],
  "confidence": 0.78,
  "rfiItems": []
}
```

**关键实现点**：
- **必须看到豁免条件**。把 `closeConditions` 一并给 Prosecutor，强制它先尝试反驳豁免，再提出论点。否则 Prosecutor 是在稻草人上论证。
- 论据必须引用具体的豁免条件编号作为反驳对象（如"CC-110-01 不适用，因为缺少内部归集凭证"）。
- `confidence` 是对自身论证质量的评估，不是对案件结论的评估。
- 证据不足以支撑升级时，`position` 可以是 `Escalate` 但 `rfiItems` 非空——这会引导 Judge 输出 RFI。

---

## A6 · Defender Agent

**角色**：构造**最强**的关闭论证。目标是尽力证明应当关闭。

**输入**：与 Prosecutor **对称**——同层输入，互不可见（A5 与 A6 在图上并行且无共享状态）。

**输出**：
```json
{
  "position": "Close",
  "coreThesis": "...",
  "arguments": [
    { "claim": "全部资金流动与已申报的批发贸易活动一致，且有商业单据支持",
      "evidenceRefs": ["EVID-TXN-003"],
      "ruleCode": "CC-110-03", "weight": "primary" }
  ],
  "alternativeExplanations": ["季节性集中采购导致的资金集中"],
  "confidence": 0.64,
  "posture": "defensive",
  "plausibility": 0.72
}
```

**关键实现点**：
- **必须看到红旗**，同样强制它先回应红旗，再提出豁免论点。
- 财务能力数据缺失时，Defender 的 Close 论据必须被自我削弱——TSD §2.2.3.1 财务能力验证原则。提示骨架需写明这一纪律，让 Judge 看到诚实的削弱而非强行辩护。
- `alternativeExplanations` 允许提出无证据支撑的假设，但必须**标注为假设**且不得给 `evidenceRefs`（避免污染证据链）。

---

## A7 · Jury Agents（A / B / C）

**角色**：三个独立陪审员，各自评估攻防论证并独立投票。

**差异化视角**（防止三票同质化）：

| 陪审员 | 视角 | 关注重心 |
|---|---|---|
| A | `quantitative_metrics` | 检测度量是否客观成立、计算是否可复现 |
| B | `red_flag_evidence` | 红旗是否有证据支撑、有无被误读 |
| C | `customer_context` | 客户画像、经营背景是否解释了资金行为 |

**输入**：`CaseModel` + Detective + Prosecutor + Defender。
**隔离要求**：三者只接收同一份上游快照，**彼此的投票结果不可见**（不变量 I7）。图结构上实现隔离，不依赖提示词约束。

**输出**（每个陪审员）：
```json
{
  "jurorId": "A", "roleFocus": "quantitative_metrics",
  "vote": "Escalate", "confidence": 0.8, "completeness": 0.9,
  "rationale": "四项度量客观成立且可复现，未见豁免条件的支撑证据",
  "accepted": ["argument-1", "argument-3"],
  "rejected": [
    { "claimRef": "argument-5", "ground": "缺乏合同凭证支撑，无法采信" }
  ]
}
```

**关键实现点**：
- `rejected` 是必填实质字段。陪审员必须记录**否决了什么以及为什么**——这是 TSD §2.2.7(b) 要求的三层可解释性之一（论证出处 → 陪审团采纳/否决记录 → 判官记录决定性因素）。
- 若三个陪审员投票完全一致，需在输出中标记 `unanimous: true`，并由 Judge 额外审视是否存在同质化风险。
- 票型含 `STR`：表示陪审员认为需直接准备可疑交易报告，Judge 据此倾向 Escalate 并在叙事中标注 STR 准备事项。

---

## A8 · Judge Agent

**角色**：综合攻防与三票，产出最终建议 + 决定性因素 + 存活的最强反论。

**输入**：全部声部输出。
**输出**：见 `deliberation_result.schema.json` 的 `judge` 定义。

**关键实现点**：
- **必须记录 `strongestSurvivingCounterArgument`**。这是本方案最重要的可解释性字段——TSD §2.2.7(b) 明确：复核者得到的不是"一个需要相信的置信度分数"，而是"论证、其来源、以及它击败的反论"。留空即视为未实现可解释性。
- `decision` 逻辑：命中数达升级闸门且无可支撑的豁免条件 → Escalate；命中数达闸门但豁免条件部分成立 → 可能 Close 或 RFI；命中数不足但证据缺口显著 → RFI；命中数不足且豁免条件齐备 → Close。
- Judge **不能输出 STR 作为 decision**，只能 `Escalate`。STR 是人工 GAML 的处置（TSD §2.5.1：AI 升级可疑线索供人工调查，不做最终 STR 判定）。
- `adoptedVoices` / `rejectedVoices` 记录采纳与未采纳的声部，供 FSD SCR-TM-04 面板"已采纳/已否决声音"展示。

---

## A9 · Narrative Generation Agent

**角色**：产出六段式分析师叙事。

**输入**：`CaseModel` + Judge 结果 + Detective 证据覆盖。
**输出**：`narrative` 结构，六段固定段序。

**六段结构**：

| # | sectionKey | 内容 |
|---|---|---|
| 1 | `customer_profile` | 客户类型、经营性质、申报能力、UBO 与 KYC 状态 |
| 2 | `transaction_analysis` | 交易行为量化、资金流向、异常模式、通道分布 |
| 3 | `risk_indicators` | 命中的红旗与检测度量，明确标注未命中的关键项 |
| 4 | `screening_outcomes` | 筛查命中、比对方式、待人工裁定项、NNS 检索结果 |
| 5 | `connected_parties` | 对手方网络、UBO 层级、关联性、无法核实项 |
| 6 | `conclusion` | 建议 + 决定性因素 + 最强反论 + RFI 项 |

**关键实现点**：
- **每段必须带 `evidenceRefs`**。段落中出现的每个实质性事实陈述都要能对应到引用。
- 第 3 段必须**同时列出未命中的关键度量**。只报命中项会构成误导——复核者无法判断 AI 是否漏判。这是对抗式设计在叙事层的延伸。
- 第 6 段必须写明建议是"建议"而非裁定。
- CTL-20 强制：全文使用完整术语。实现上应在校验器中维护一个缩写黑名单（如 "CTR"、"WPC"、"CTOS"、"KYC" 若作为缩写出现需展开）。
- 建议为 RFI 时，第 6 段须具体列出待补信息，措辞可直接用于人工起草 RFI。

---

## A10 · Chat Agent（对话问答）

**角色**：就本案证据回答 Checker 提问。

**输入**：`caseId` + 用户问题 + 会话历史。
**输出**：
```json
{
  "answer": "...",
  "evidenceRefs": ["EVID-TXN-001"],
  "grounded": true,
  "refusalReason": null,
  "suggestedActions": ["trigger_rfi"]
}
```

**四类问题与应答策略**：

| 问题类型 | 示例 | 策略 |
|---|---|---|
| 解释类 | "为什么建议升级" | 引用裁决记录：决定性因素、被采纳/否决的主张、存活反论 |
| 证据类 | "这笔 850 万的付款对手方是谁" | 引用具体证据条目；无记录则明确说无 |
| 状态类 | "现在到哪一步了" | 读生命周期状态机，不调 LLM |
| 越界类 | "客户身份证号" / "帮我给客户发邮件" | **拒答**，说明披露约束 |

**拒答规则（硬约束）**：
1. 询问未脱敏 PII → 拒答，提示见 TSD §2.2.8 / CTL-28。
2. 要求执行动作（发信、改状态、提交 STR）→ 拒答，Chat 为只读，建议走对应 UI 流程。
3. 询问证据中不存在的事实 → 明确说无记录，**不得推测**。
4. 回答必须落在案例上下文内。跨案件问题一律拒答。

**关键实现点**：
- `grounded=false` 时必须填 `refusalReason`，前端明确渲染为拒答态。
- 会话历史由系统自持，**不进模型训练**（TSD §2.2.3.3）。
- 问答上下文复用同一套掩码后的案件数据，不重新构造。
- `suggestedActions` 只是提示，不执行动作。

---

## 附录 A · 模板 ID 与版本登记

| templateId | 用途 | 初始版本 |
|---|---|---|
| `TM_ANALYSIS_DETECTIVE` | Detective | 1.0.0 |
| `TM_ANALYSIS_PROSECUTOR` | Prosecutor | 1.0.0 |
| `TM_ANALYSIS_DEFENDER` | Defender | 1.0.0 |
| `TM_ANALYSIS_JUROR` | Jury A/B/C（视角参数化） | 1.0.0 |
| `TM_ANALYSIS_JUDGE` | Judge | 1.0.0 |
| `TM_NARRATIVE` | 六段式叙事 | 1.0.0 |
| `TM_CHAT` | 对话问答 | 1.0.0 |

版本写入 `runContext.promptVersion`，参与可复现性保障。

## 附录 B · Agent 调用次数与耗时预算

单案件 LLM 调用：Detective 1 + Prosecutor 1 + Defender 1 + Jury 3 + Judge 1 + Narrative 1 = **8 次**。

累计推理预算 240 秒/案件（TSD §7.11.3）。Risk Analyzer 与 Data Parser 为确定性计算，不计入。

演示环境下 8 次 Mock 调用应 < 3 秒；接真实模型后需实测分配：裁决阶段 5 次为主要开销，叙事 1 次建议分配更大 `maxOutputTokens`。