# POC · 案例叙事生成 Agent 与对话问答 Agent

基于 RHB NOVA AML AI 项目的 **FSD v1.0 / TSD v0.91 / TO-BE 流程图 V1.0**，裁剪出的最小可运行原型方案。

**目标**：给定案件证据包，自动产出带证据引用的六段式分析师叙事与处置建议，并支持就本案证据的对话问答。

---

## 快速开始

```bash
# 0. 阅读顺序（必读，不可跳过）
#    docs/00-source-conflict-rulings.md   ← 源文档冲突裁决
#    docs/01-poc-solution.md              ← 主方案
#    docs/02-agent-specifications.md      ← 8 个 Agent 规格
#    docs/03-build-runbook.md             ← 五阶段实施
#    docs/04-acceptance-tests.md          ← 验收与 Demo 脚本

# 1. 环境
python3.11 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic langgraph jsonschema

# 2. 契约自检（schema 合法性 + fixture 一致性 + 场景引用，已验证通过）
python contracts/selfcheck.py

# 3. 需要时重建 fixture
python contracts/knowledge/gen_fixtures.py

# 4. 运行（实现后）
python -m src.cli run fixtures/SCN110_escalate.json --out out/result.json
python -m src.cli run fixtures/SCN110_escalate.json --inject-failure timeout   # 演示降级
```

---

## 目录

| 路径 | 说明 | 状态 |
|---|---|---|
| `docs/00-source-conflict-rulings.md` | TSD/FSD 冲突裁决表，**实现前必读** | ✅ |
| `docs/01-poc-solution.md` | 主方案：范围、架构、不变量、验收 | ✅ |
| `docs/02-agent-specifications.md` | 8 个 Agent 逐一规格 + 提示骨架 | ✅ |
| `docs/03-build-runbook.md` | 五阶段实施步骤与阶段验收 | ✅ |
| `docs/04-acceptance-tests.md` | 9 组测试用例 + 8 步 Demo 脚本 | ✅ |
| `contracts/evidence_pack.schema.json` | 输入契约（Draft-07，已校验） | ✅ |
| `contracts/deliberation_result.schema.json` | 输出契约（Draft-07，含 8 条不变量） | ✅ |
| `contracts/llm_inference_contract.json` | LLM 契约，对齐 TSD §7.11 | ✅ |
| `contracts/knowledge/scenario_knowledge.json` | 场景知识 + 阈值唯一真相源 | ✅ |
| `contracts/selfcheck.py` | 契约自检脚本，可作 CI 前置 | ✅ 已验证通过 |
| `fixtures/*.json` | 4 个案件样本，覆盖三种建议 | ✅ 已通过 schema |
| `src/` | 代码实现 | ⬜ 待开发 |
| `tests/` | 测试实现 | ⬜ 待开发 |

---

## 这个 POC 做什么、不做什么

**做**（严格按 TSD/FSD）：

- 案件为单元的处理链路
- 功能代理：Data Parser / Search / Risk Analyzer / Narrative Generation
- 裁决代理：Detective / Prosecutor / Defender / Jury(A,B,C) / Judge（七声部）
- 对话 Agent：案件上下文问答，越界拒答
- 两层提示与知识架构（TSD §2.2.3.1）
- LLM 契约与结构化校验（TSD §7.11、CTL-19/20）
- AI 降级（TSD §12.5）
- 人工闸门：同意 / 覆核分离，覆核需理由（FSD §3.9）

**不做**（避免范围蔓延）：

- 任何真实外部集成（EDL/CTOS/Google/CIS/EAI/FINS/RPA 等）——INFO-03/04/05 未决
- 批量调度（Zena/Celery）
- Milvus 向量检索——走 TSD §12.5 定义的 zero-shot 降级
- CDD/ODD、QC 抽样、Round-Robin、节假日日历
- 真实 RBAC/SAML/云部署、PDF 渲染

> **注意**：Chat Agent 是**内部 Checker 助手**，不是客服机器人。TSD §2.2.8 规定 TM 域不存在对外通信。

---

## 三条验收底线

| # | 底线 | 如何验证 |
|---|---|---|
| A1 | 每条主张携带可解析证据引用 | 断开引用 → 被 `LLM-OUTPUT-INVALID` 拦截 |
| A2 | AI 只出建议，人工处置独立且覆核需理由 | 覆核无理由 → 提交被拒 |
| A3 | LLM 失败必然降级，绝不静默出错 | 注入超时 → `AI-Fallback` + 转人工 |

**这三条是 POC 的全部价值。功能多寡不重要，这三条不成立则 POC 无意义。**

---

## 给下一个开发者/Agent 的提示

1. **先读 `docs/00`**，否则会照 TSD 残留表述写错（批次窗口、退出码、场景编号三处冲突）。
2. **照 `03-build-runbook.md` 五阶段推进**，每阶段有验收点，不要跳阶段。先跑通最小闭环再加护栏。
3. **阈值只在 `contracts/knowledge/scenario_knowledge.json` 定义**，提示词里禁止硬编码数字。
4. **LLM 调用只经适配器**；陪审员在图结构上隔离，不靠提示词。
5. **不变量测试（8 条）必须全过**才算 POC 成立，详见 `04-acceptance-tests.md`。

---

## 提示模板与版本

模板 ID 登记见 `docs/02-agent-specifications.md` 附录 A。提示骨架是结构与纪律，不是最终文案；最终文案需版本化，写入 `runContext.promptVersion`。