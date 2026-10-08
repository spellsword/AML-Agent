# POC 开发方案 · 案例叙事生成 Agent 与对话问答 Agent

> **文档定位**：面向开发者/接手工程师的可执行方案。读完本文 + 目录内 4 份契约文件，即可独立完成开发，无需回查 TSD/FSD 原文。
>
> **依据**：TSD v0.91、FSD v1.0、TO-BE High Level Process Flow V1.0。
> **强制前置**：`00-source-conflict-rulings.md` 必须先读。TSD 历经 13 次修订，正文含互斥表述，未做裁决会写错。

---

## 1. 一句话定义与验收底线

**做什么**：给定一个案件的完整证据包（客户 KYC、账户、交易、UBO、筛查、公开域检索、历史告警），自动产出 ①一份带证据引用的六段式分析师叙事与处置建议（Close / Escalate / RFI）；②一个能就本案件证据回答 Checker 提问的对话助手。

**POC 验收底线**（三条，全部满足才算通过）：

| # | 底线 | 判定方式 |
|---|---|---|
| A1 | 每一条实质性主张都携带可解析的证据引用 | 断开证据引用的裁决结果必须被 `LLM-OUTPUT-INVALID` 拦截；演示一条被拦的样例 |
| A2 | AI 只出建议，人工处置是独立闸门且覆核必须写理由 | 演示 Agree 与 Override 两条路径，Override 无理由时提交被拒 |
| A3 | LLM 失败必然降级，绝不静默返回假结果 | 演示一次超时降级，案件带 `AI-Fallback` 标记且 `heldForManualInvestigation=true` |

> 这三条是本 POC 的全部价值所在。**功能多寡不重要，这三条不成立则 POC 无意义。**

---

## 2. 范围裁剪：保留与不做

TSD/FSD 描述的是一个含 6 角色、17 场景、13 个外部集成的完整平台。POC 是验证核心链路的原型。

### 2.1 保留（必须实现）

| 能力 | 依据条款 | POC 实现形态 |
|---|---|---|
| 案件为单元的处理 | TSD §2.1 case-centric | 单案件函数式调用，无批处理 |
| 功能代理 4 个 | TSD §2.2.3 | Data Parser / Search / Risk Analyzer / Narrative Generation |
| 裁决代理 4 个 | TSD §2.2.3 | Detective / Prosecutor / Defender / Jury(A,B,C) / Judge |
| 对话代理 | TSD §2.2.3 Chat Agent | 案件上下文问答，越界即拒答 |
| 两层提示与知识架构 | TSD §2.2.3.1 | 通用原则 + 场景知识条目分离，知识外置 JSON |
| 四级决策标准 | TSD §2.2.3.2 | 准则 / 参数 / 硬规则 / 豁免四类 |
| 可解释性 | TSD §2.2.7 | 论据出处 + 逐案例特征贡献 + 四版本钉住 |
| LLM 契约 | TSD §7.11.2 / §7.11.3 | 字段冻结 + 错误码分类 + 重试与预算 |
| AI 降级 | TSD §12.5 | 四条降级路径 + 零样本打标 |
| 掩码与注入防护 | CTL-07 / CTL-19 / CTL-20 | 令牌化上下文 + 前后置双闸 |
| 生命周期状态 | TSD §5.4.1 | AI Analysis → Checker Review 闭环 |
| 人工闸门与覆核 | FSD §3.9 | Agree / Override 分离，覆核需理由 |
| 场景知识 | FSD §1.10 | SCN110 + SCN201 两个场景 |

### 2.2 不做（明确越界即返工）

| 不做项 | 理由 | 若被要求追加时的正确做法 |
|---|---|---|
| 任何真实外部集成 | INFO-03/04/05 未决，无端点无凭据 | 用本地 fixture 模拟响应，保留接口签名 |
| 批量调度（Zena/Celery/时间窗口） | POC 同步执行 | 在 `CaseProcessor` 边界留异步接口，不实现调度器 |
| Milvus 向量检索 / 相似案例 | TSD §12.5 已定义 zero-shot 降级 | 直接 `retrievalMode=zero_shot`，并在界面明示 |
| CDD/ODD 流程、QC 抽样、Round-Robin、节假日日历 | 超出核心范围 | 不实现 |
| 真实 RBAC / SAML / 华为云部署 | POC 单用户本地 | 以注释标注 CTL 编号供后续补齐 |
| PDF 渲染 | 非核心 | 保留 `renderedPdfRef` 字段占位 |

> **重要澄清**：POC 的 Chat Agent 是**给内部 Checker 用的案件助手**，不是客服机器人。TSD §2.2.8 明确 TM 域不存在对外通信。若有人想把本 POC 演示成"对客问答"，那是误解了需求边界。

---

## 3. 架构

```
evidence_pack.json（唯一输入）
        ↓
[ Data Parser ]  归一为内部 CaseModel；辖区 fail-closed
        ↓
[ Risk Analyzer ]  计算检测度量 → 命中/未命中 + 特征贡献
        ↓
[ Detective ]  事实与证据覆盖（不倾向）
        ↓
   ┌────────────┴────────────┐
[Prosecutor]              [Defender]     并行，彼此不可见
   └────────────┬────────────┘
        [Jury A/B/C]        三票独立，差异化视角
        ↓
        [Judge ]  终裁 + 决定性因素 + 存活的最强反论
        ↓
[ Narrative Generation ]  六段式叙事 + 建议
        ↓
[ Human Gate ]  Checker 同意 / 覆核（需理由）
        ↓
   [ CTL-14 追加式审计 ]
```

实现形态：编排用 LangGraph（TSD §2.2.3 指定），后端 FastAPI。POC 单进程即可，但**必须**按 TSD 的五个逻辑层分文件，后续迁移不得重写。

**为什么用 LangGraph 而不是线性函数**：裁决阶段的 Prosecutor/Defender 并行 + Jury 三票独立 + Judge 汇合，本质是一个有环条件的图。线性函数会在 Jury 上退化成"看到对方投票"，直接破坏对抗式推理的前提（TSD §2.1 adversarial reasoning）。

---

## 4. 目录结构（POC 直接照建）

```
poc-aml-narrative/
├── docs/
│   ├── 00-source-conflict-rulings.md   ← 冲突裁决，先读
│   ├── 01-poc-solution.md              ← 本文，主入口
│   ├── 02-agent-specifications.md      ← 8 个 Agent 逐一规格
│   ├── 03-build-runbook.md             ← 分阶段实施步骤 + 验收
│   └── 04-acceptance-tests.md          ← 测试用例与判定
├── contracts/
│   ├── evidence_pack.schema.json          证据包（输入）
│   ├── deliberation_result.schema.json    裁决+叙事（输出）
│   ├── llm_inference_contract.json        LLM 契约（对齐 §7.11）
│   └── knowledge/
│       └── scenario_knowledge.json        场景知识（阈值唯一真相源）
├── fixtures/
│   ├── SCN110_escalate.json              典型升级案
│   ├── SCN110_close.json                 典型关闭案
│   ├── SCN201_escalate.json              跑分账户案
│   └── SCN201_rfi.json                   证据不足 → RFI 案
└── src/  （由开发者创建）
    ├── domain/          model.py, enums.py
    ├── agents/          parser.py risk_analyzer.py detective.py
    │                    prosecutor.py defender.py juror.py judge.py
    │                    narrative.py chat.py
    ├── graph/           pipeline.py（LangGraph）
    ├── llm/             adapter.py mock_provider.py prompts.py
    ├── guardrails/      masking.py injection.py validation.py
    ├── audit/           audit.py（追加式）
    └── api/             main.py
```

---

## 5. 数据流与不变量

### 5.1 输入

单个 JSON 文件，符合 `contracts/evidence_pack.schema.json`。**禁止**代码里拼装证据、随机生成交易、调用任何外部服务。

### 5.2 八条不变量（违反即为缺陷，逐条对应验收）

| # | 不变量 | 强制点 |
|---|---|---|
| I1 | 每条实质主张必须有 ≥1 个可解析 `evidenceRefs` | 后置校验 `evidence_refs_resolvable` |
| I2 | 证据引用必须解析到本次请求的证据集合内 | 同上，不接受"看起来合理"的引用 |
| I3 | 输出不得含未掩码 PII | 后置校验 `no_unmasked_pii` |
| I4 | 叙事不得使用缩写 | 后置校验 `full_terms_expanded` |
| I5 | 未实际升级不得置 escalate 状态 | 后置校验 `no_premature_escalate_state` |
| I6 | `recommendation` 永远不等于最终裁定 | 类型与文案双保险，界面上必须显示为"建议" |
| I7 | 三个陪审员互不可见 | 图结构层面隔离，不靠提示词约束 |
| I8 | 任一 LLM 失败必须走降级，不得吞异常 | 适配器统一出口，禁止裸 try/except |

### 5.3 输出

符合 `contracts/deliberation_result.schema.json`，含七声部、裁决、六段叙事、校验结果、降级标记、人工决定（后填）。

---

## 6. 关键设计决策与理由

| 决策 | 理由 | 备选方案为何不选 |
|---|---|---|
| 阈值/知识全部外置 JSON | TSD §2.2.3.1 两层架构要求；且提示词改动需走版本化审批 | 硬编码在提示词里 → 无法版本化、无法影子测试 |
| 判官用 LangGraph 而非顺序调用 | 对抗式推理要求 Prosecutor/Defender 真并行、Jury 真隔离 | 顺序调用会让陪审员看到彼此投票，退化为单次模型偏见 |
| 校验在适配器出口统一做 | CTL-20 是强制的，且不能只靠提示词约束 | 分散在各 Agent 内做 → 必然遗漏，且无法统一降级 |
| 掩码在构造上下文时做，不在提示词里做 | CTL-07 要求脱敏后再出集群，提示词内做等于已泄漏 | 提示词内掩码 → 数据已过网关 |
| 陪审员差异化视角（量化/红旗/客户背景） | 三个同质视角必然产生同质投票，三票失去意义 | 三个相同提示词 → 伪独立 |
| 降级产出规则模板 + 转人工 | TSD §12.5 明确禁止自主处置 | 降级时返回"无结论" → 业务停摆 |
| Mock provider 为默认 | INFO-05 未决，端点不存在 | 直连 DashScope → POC 无法离线复现 |
| 建议与裁定分离渲染 | FSD SCR-TM-04 明确该面板无"决策按钮" | 让 AI 直接定案 → 违反 human-in-the-loop 定位 |

---

## 7. 验收标准

### 7.1 功能验收（Demo 脚本，8 步）

1. 载入 `SCN110_escalate.json`，点击"运行分析"→ 全链路跑通，产出七声部 + 六段叙事，建议为 Escalate。
2. 打开裁决面板 → 展示 Judge 终裁、决定性因素、存活的最强反论、三票明细、被告方证据账本。
3. 点击任一论断的证据引用 → 打开对应证据条目（一键可达，FSD §2.2.7）。
4. 点击"同意升级" → 路由至 `gaml_l3_review`，审计落库。
5. 新建 `SCN110_close.json` → 建议 Close，点击"覆核为升级"但**不填理由** → 提交被拒；补理由后成功。
6. 打开 Chat Agent，问"这案子为什么被升级" → 答出并引用证据；问"客户身份证号是多少" → 拒答并说明披露约束。
7. 开启 Mock provider 的故障注入 → 分析失败，案件带 `AI-Fallback`，`heldForManualInvestigation=true`，界面明示转人工。
8. 查看运行上下文 → 显示 prompt/model/knowledge/config 四版本。

### 7.2 质量验收

| 项 | 标准 |
|---|---|
| 证据引用有效性 | 100%。出现任一无法解析的引用即失败 |
| 幻觉率 | 零。抽样 20 条论据，须全部可追溯到证据条目 |
| 降级可靠性 | 注入 4 类故障（超时/格式错误/鉴权失败/掩码失败），全部正确降级 |
| 可复现性 | 同输入 + 同版本，结论一致 |
| 单案件耗时 | < 5 分钟（TSD §13.3 硬目标），实际应远低于此 |

### 7.3 不验收（PoC 不证明这些）

绝对准确率、FALSE POSITIVE 下降、真实集成连通性、并发性能、多辖区隔离、PDF 渲染质量。

---

## 8. 风险与避坑

| 风险 | 表现 | 规避 |
|---|---|---|
| **照 TSD 直译时踩到残留表述** | 批次窗口、退出码、场景编号三处冲突 | 见 `00-source-conflict-rulings.md`，实现前对照 |
| **陪审员退化为同质投票** | 三票意见雷同，伪独立 | 图结构隔离 + 差异化视角，评审时专门检查 |
| **证据引用幻觉** | 生成看似合理但解析不了的 `EVID-*` | 出口统一校验，解析失败即降级，不得放行 |
| **降级被静默吞掉** | 异常被 catch 后返回空结果 | I8 硬约束；代码评审专项检查裸 try/except |
| **范围蔓延** | 顺手做了 CTOS/RPA/QC/日历 | 见 §2.2，追加需显式授权 |
| **把 Chat Agent 当客服** | 演示成对客问答 | TSD §2.2.8 硬边界，需在界面显式标注"内部助手" |
| **提示词硬编码阈值** | 阈值散落各处，改一处漏三处 | 单一真相源检查；测试断言提示词中无数字阈值 |
| **缩写字典膨胀** | 为"看起来专业"大量用缩写 | CTL-20 强校验，Narrative 段必须展开全称 |

---

## 9. 环境与依赖

```
Python 3.11+
fastapi, uvicorn, pydantic v2
langgraph
jsonschema          # 契约校验
```
无数据库：审计用追加式 JSONL 文件。PDF/向量库/云 SDK 一律不引入。

---

## 10. 开发推进顺序

按 `03-build-runbook.md` 的五个阶段推进，每阶段有独立验收点，**不要跳阶段**。核心原则：先让一个案件跑通最小闭环（Parser → Detective → Judge → Narrative），再横向加场景与对话，最后加护栏与降级。反序推进（先做护栏再做功能）会让护栏脱离真实数据形态而失效。

---

## 附：源文件索引

| 文件 | 用途 |
|---|---|
| `00-source-conflict-rulings.md` | 冲突裁决，实现前必读 |
| `01-poc-solution.md` | 本文，主入口 |
| `02-agent-specifications.md` | 8 个 Agent 逐一规格（输入/输出/提示骨架/失败模式） |
| `03-build-runbook.md` | 五阶段实施步骤、每阶段验收命令 |
| `04-acceptance-tests.md` | 测试用例、判定标准、Demo 脚本 |
| `contracts/evidence_pack.schema.json` | 输入契约 |
| `contracts/deliberation_result.schema.json` | 输出契约 |
| `contracts/llm_inference_contract.json` | LLM 契约 |
| `contracts/knowledge/scenario_knowledge.json` | 场景知识与阈值 |