# 03 · 构建实施手册

> 五阶段推进。**每阶段有独立验收点，未通过不进入下一阶段。**
>
> 核心原则：先打通最小闭环，再横向扩展，最后加固护栏。反序推进会让护栏脱离真实数据形态而失效——这是本项目最容易犯的错误。

---

## 阶段一 · 骨架与最小闭环

**目标**：一个案件从证据包跑到叙事输出，中途无护栏、无降级。先证明链路通。

### 步骤

1. **建目录**（照 `01-poc-solution.md` §4）

2. **领域模型** `src/domain/model.py` + `enums.py`
   - 定义 `CaseModel`、`EvidenceEntry`、`MetricEvaluation`、`VoiceOutput`、`JudgeDecision`、`Narrative`
   - `Recommendation` 枚举：`CLOSE / ESCALATE / RFI`（**无 STR**，STR 是人工处置）

3. **数据解析** `src/agents/parser.py`
   - 按 A1 规格实现证据台账生成
   - 辖区 fail-closed
   - 交易 5000 条截断

4. **风险分析** `src/agents/risk_analyzer.py`
   - 纯函数实现，阈值从 `scenario_knowledge.json` 读
   - 计算 `featureContribution`

5. **Mock provider** `src/llm/mock_provider.py`
   - 返回符合 `llm_inference_contract.json` 的成功响应
   - 输出固定但结构完整的七声部 JSON（按模板 ID 分支）
   - **必须**支持故障注入：`--inject-failure timeout|invalid|auth|mask`

6. **适配器** `src/llm/adapter.py`
   - 统一出口，8 次调用全部经此
   - 埋点：token 用量、耗时、requestId 幂等

7. **编排** `src/graph/pipeline.py`
   - LangGraph：Parser → RiskAnalyzer → Detective → (Prosecutor ‖ Defender) → Jury×3 → Judge → Narrative

8. **CLI** `src/cli.py` —— `python -m src.cli run fixtures/SCN110_escalate.json`

### 验收

```bash
python -m src.cli run fixtures/SCN110_escalate.json --out out/result.json
```
- [ ] 命令退出码 0
- [ ] `out/result.json` 通过 `deliberation_result.schema.json` 校验
- [ ] `runContext` 四版本齐全
- [ ] `voices.jurors` 恰好 3 条
- [ ] `narrative.sections` 恰好 6 条且段序正确
- [ ] `evidenceLedger.entries` 非空

> 本阶段**不要求**证据引用全部有效、**不要求**有护栏。先跑通。

---

## 阶段二 · 护栏与降级

**目标**：把八条不变量真正落地。本阶段是 POC 的核心价值所在。

### 步骤

1. **掩码器** `src/guardrails/masking.py`
   - 构造上下文时替换为稳定代理令牌：`[CUSTOMER_1]`、`[ACCOUNT_2]`、`[COUNTERPARTY_1]`
   - 保留内存映射，仅在展示层还原
   - 掩码失败 → 抛错并触发降级（**不发送**未掩码数据）

2. **注入防护** `src/guardrails/injection.py`
   - 扫描证据字段中的注入模式（"ignore previous instructions"、"忽略上述指令"、角色劫持等）
   - 命中 → 记录并从上下文中隔离该字段，**不静默丢弃**（要留证据说明为何隔离）

3. **输出校验器** `src/guardrails/validation.py`
   - 八项校验，逐项产出 `checkId` + 状态：
     `schema_valid` / `evidence_refs_resolvable` / `no_unmasked_pii` / `full_terms_expanded` /
     `no_premature_escalate_state` / `prompt_injection_clean` / `recommendation_not_autonomous` / `full_terms_expanded`
   - **任一 FAIL → `validationGate=REJECTED`**
   - 缩写检测：维护缩写黑名单，命中即 FAIL

4. **降级处理器** `src/agents/fallback.py`
   - 触发条件：`LLM_TIMEOUT` / `LLM_OUTPUT_INVALID` / `LLM_AUTH_FAILURE` / `PII_MASK_FAILED` / `CUMULATIVE_BUDGET_EXHAUSTED`
   - 产出规则模板摘要 + `heldForManualInvestigation=true`
   - **禁止**在降级路径产生 recommendation

5. **重试策略** `src/llm/retry.py`
   - 严格按 `retryPolicy`：仅 3 个错误码可重试，最多 2 次，累计预算 240 秒
   - 重试复用同一 `requestId`
   - **`LLM-CONTRACT-INVALID` / `LLM-AUTH-FAILURE` / `LLM-OUTPUT-INVALID` 不得重试**

6. **审计** `src/audit/audit.py`
   - 追加式 JSONL
   - 记录：runId、caseId、agent、requestId、四版本、token、耗时、校验结果、降级标记、人工动作
   - 保留期标 36 个月（CTL-14，POC 只标注不实现清理）

### 验收

```bash
# 八项校验全部 PASS
python -m src.cli run fixtures/SCN110_escalate.json --out out/r1.json
python -c "import json;d=json.load(open('out/r1.json'));print(d['validation']['validationGate'])"
# 期望：PASS

# 故障注入 → 降级
python -m src.cli run fixtures/SCN110_escalate.json --inject-failure timeout
# 期望：fallback.engaged=true，heldForManualInvestigation=true，recommendation 缺席

# 四类故障逐一验证
for f in timeout invalid auth mask; do
  python -m src.cli run fixtures/SCN110_escalate.json --inject-failure $f --out out/fb_$f.json
done
```
- [ ] 正常路径 `validationGate=PASS`
- [ ] 四类故障全部正确降级
- [ ] 降级输出**不含** `recommendation`
- [ ] 审计日志每条运行都有记录且含四版本
- [ ] 代码中无裸 `try/except` 吞异常（可用 grep 检查 `except:` 后无 raise/降级调用）

---

## 阶段三 · 场景与对话

**目标**：横向扩展到 4 个 fixture 与 Chat Agent。

### 步骤

1. **补齐 fixture**（4 个，覆盖全部三种建议 + 边界）
   - `SCN110_escalate.json` —— 命中多、无豁免证据 → Escalate
   - `SCN110_close.json` —— 命中少、豁免条件齐备 → Close
   - `SCN201_escalate.json` —— 跑分特征 → Escalate，投票 STR
   - `SCN201_rfi.json` —— 命中达闸门但豁免部分成立 → RFI

2. **Chat Agent** `src/agents/chat.py`
   - 四类问题路由（解释/证据/状态/越界）
   - 越界拒答，返回 `refusalReason`
   - 会话历史系统自持

3. **建议 API** `src/api/main.py`
   - `POST /api/analyse` → 跑完整链路
   - `GET /api/cases/{caseId}` → 取结果
   - `POST /api/cases/{caseId}/chat` → 问答
   - `POST /api/cases/{caseId}/decision` → 人工处置（override 无理由须拒绝）
   - `GET /api/cases/{caseId}/audit` → 审计

4. **最小前端**（静态页即可）
   - 裁决面板：Judge 卡、Prosecutor/Defender 并排、三陪审员卡、决定性因素、存活反论、规则码
   - 证据面板：点引用即开对应证据条目
   - 叙事面板：六段式 + 建议标识为"AI 建议"
   - Chat 面板：含拒答态渲染
   - 降级横幅：`AI-Fallback · 转人工`

### 验收

```bash
for f in fixtures/*.json; do
  python -m src.cli run $f --out out/$(basename $f)
done
```
- [ ] 4 个 fixture 全部跑通
- [ ] 建议分布：2×Escalate、1×Close、1×RFI
- [ ] Chat 越界问题（4 类各一）全部拒答且填 `refusalReason`
- [ ] Chat 解释类问题能引用真实证据 ID
- [ ] 人工处置：override 无理由 → 400 并说明

---

## 阶段四 · 可解释性与可复现

**目标**：满足 TSD §2.2.7 三类可解释性。

### 步骤

1. **论证出处**（`(b)` 类）
   - 每条主张可点开引用 → 打开证据条目（FSD §2.2.7 要求"一键可达"）
   - 陪审团采纳/否决记录完整展示
   - **Judge 的 `strongestSurvivingCounterArgument` 不得为空**——空则视为未实现

2. **模型行为透明度**（`(c)` 类）
   - 界面展示四版本（prompt / model / knowledge / config）
   - 同输入同版本复跑 → 结论一致（Mock 下必然一致；真实模型下记录差异）

3. **特征归因**（`(a)` 类）
   - 展示每个度量的 `featureContribution` 与 `computeExplanation`

4. **降级可见性**
   - `retrievalMode=zero_shot` 在界面明示（TSC §12.5 要求 QC 可见）
   - `AI-Fallback` 案件在列表中高亮

### 验收

- [ ] 任一论断可一键跳到证据
- [ ] 三陪审员视角标签正确显示且投票不雷同
- [ ] 四版本可见
- [ ] `strongestSurvivingCounterArgument` 非空
- [ ] AI-Fallback 案件界面有明确标识

---

## 阶段五 · 收口

**目标**：达到可交付状态。

### 步骤

1. **测试** `tests/`（照 `04-acceptance-tests.md`）
2. **README**：一键启动、目录说明、已知限制
3. **提示文档登记**：`promptVersion` 与提示文件对应关系写入 README
4. **对照检查表**：逐条核对 `01-poc-solution.md` §5.2 八条不变量

### 验收

- [ ] 全部测试通过
- [ ] Demo 脚本 8 步全部可演示
- [ ] 八条不变量逐条有对应测试
- [ ] README 可让他人独立启动

---

## 开发纪律（各阶段通用）

### 必须做

- 每个 Agent 的输入输出**都用契约 schema 校验**，不要靠 TypeScript/Pydantic 类型断言代替运行时校验——LLM 输出不可信。
- LLM 调用**只经适配器**。业务代码不得直接调 provider。
- 任何异常路径都要有明确归宿：抛错、返降级、或写审计。**不允许消失。**
- 阈值、场景名、豁免条件引用**全部外置**。代码里出现数字常量形式的业务阈值即违规。

### 禁止做

- 禁止在提示词中硬编码阈值或案件事实。
- 禁止让陪审员看到彼此投票。
- 禁止在降级路径产出建议。
- 禁止用 `except: pass` 或返回空字典掩盖失败。
- 禁止为了演示效果在 POC 里接任何真实外部接口。

### 提交前自查

```bash
# 1. 无裸 except
grep -rn "except:" src/ | grep -v "raise"
# 2. 提示词无硬编码阈值
grep -rniE "threshold.*[0-9]{2,}" src/llm/prompts.py
# 3. 无真实外呼
grep -rnE "requests\.|httpx\.|urllib\.request" src/
# 4. 契约校验通过
python -m tests.run_all
```