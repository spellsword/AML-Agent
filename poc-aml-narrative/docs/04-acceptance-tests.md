# 04 · 验收测试与 Demo 脚本

> 三个层次：**不变量测试**（必须全过）→ **功能测试**（覆盖四条路径）→ **Demo 脚本**（人工 8 步）。
>
> POC 判定标准：不变量测试 100% 通过 + 功能测试全过 + Demo 脚本可完整演示。准确率类指标不在 POC 判定范围内。

---

## 一、不变量测试（对应 `01-poc-solution.md` §5.2）

每条不变量至少一个测试。**任一失败即 POC 不通过。**

| ID | 不变量 | 测试方法 | 期望 |
|---|---|---|---|
| I1 | 每条主张带证据引用 | 构造缺 `evidenceRefs` 的输出喂校验器 | `evidence_refs_resolvable=FAIL`，`validationGate=REJECTED` |
| I2 | 引用可解析 | 构造引用不存在的 `EVID-XXX-999` | `REJECTED` |
| I3 | 无未掩码 PII | 输出中植入真实格式 NRIC（`880101-14-1234`） | `no_unmasked_pii=FAIL` |
| I4 | 叙事无缩写 | 第 2 段植入 "CTR 异常" | `full_terms_expanded=FAIL` |
| I5 | 未升级不置 escalate 态 | 建议为 Close 但状态标 escalate | `no_premature_escalate_state=FAIL` |
| I6 | 建议非裁定 | 类型层面 `Recommendation` 无 STR；文案检查 | 无法产出 STR 建议 |
| I7 | 陪审员隔离 | 检查图拓扑：Jury A/B/C 之间无共享状态边 | 图校验通过 |
| I8 | 失败必降级 | 注入四类故障 | 全部 `fallback.engaged=true` |

### I7 图拓扑测试实现要点

```python
def test_jurors_are_isolated(pipeline_graph):
    """三个陪审员节点之间不得有边，也不得共享可变状态。"""
    jury_nodes = [n for n in pipeline_graph.nodes if n.startswith("juror_")]
    assert len(jury_nodes) == 3
    for a in jury_nodes:
        for b in jury_nodes:
            if a >= b:
                continue
            assert not pipeline_graph.has_edge(a, b), f"{a} 与 {b} 之间存在边"
    # 每个陪审员仅从上游取同一份快照
    for j in jury_nodes:
        in_edges = list(pipeline_graph.in_edges(j))
        assert len(in_edges) == 1, f"{j} 输入边数异常：{in_edges}"
```

---

## 二、功能测试

### F1 · 建议正确性（4 个 fixture）

| Fixture | 场景 | 期望建议 | 关键断言 |
|---|---|---|---|
| `SCN110_escalate` | SCN110 | **Escalate** | 命中数 ≥ 闸门；`strongestSurvivingCounterArgument` 非空 |
| `SCN110_close` | SCN110 | **Close** | 豁免条件 CC-110-03 证据齐备；财务能力数据完整 |
| `SCN201_escalate` | SCN201 | **Escalate** | 至少一票 STR；`same_day_pass_ratio` 命中 |
| `SCN201_rfi` | SCN201 | **RFI** | `rfiQuestions` 非空且具体；`evidenceCoverage.gaps` 非空 |

```python
def test_recommendations(analyse):
    cases = [
        ("SCN110_escalate", "Escalate"),
        ("SCN110_close",    "Close"),
        ("SCN201_escalate", "Escalate"),
        ("SCN201_rfi",      "RFI"),
    ]
    for fixture, expected in cases:
        r = analyse(fixture)
        assert r["judge"]["decision"] == expected, \
            f"{fixture}: 期望 {expected}，实得 {r['judge']['decision']}"
        assert r["validation"]["validationGate"] == "PASS"
```

### F2 · 降级测试（4 类故障）

```python
@pytest.mark.parametrize("mode,expect_reason", [
    ("timeout", "LLM_TIMEOUT"),
    ("invalid", "LLM_OUTPUT_INVALID"),
    ("auth",    "LLM_AUTH_FAILURE"),
    ("mask",    "PII_MASK_FAILED"),
])
def test_degradation(analyse_with_failure, mode, expect_reason):
    r = analyse_with_failure("SCN110_escalate.json", mode)
    assert r["fallback"]["engaged"] is True
    assert r["fallback"]["reason"] == expect_reason
    assert r["fallback"]["heldForManualInvestigation"] is True
    assert r["fallback"]["ruleEngineTemplateId"] is not None
    # 降级路径绝不产出建议
    assert "recommendation" not in r.get("narrative", {}) or \
           r["narrative"]["recommendation"] is None
```

### F3 · 重试策略测试

| 错误码 | 允许重试 | 期望重试次数 |
|---|---|---|
| `LLM-TIMEOUT` | 是 | ≤ 2 |
| `LLM-SERVICE-UNAVAILABLE` | 是 | ≤ 2 |
| `LLM-CAPACITY-LIMIT` | 是 | ≤ 2 |
| `LLM-CONTRACT-INVALID` | 否 | 0 |
| `LLM-AUTH-FAILURE` | 否 | 0 |
| `LLM-OUTPUT-INVALID` | 否 | 0 |

```python
def test_no_retry_on_non_retryable(fake_provider):
    for code in ["LLM-CONTRACT-INVALID", "LLM-AUTH-FAILURE", "LLM-OUTPUT-INVALID"]:
        p = fake_provider(always_fail=code)
        result = run_with(p, "SCN110_escalate.json")
        assert p.call_count == 1, f"{code} 不应重试，实得 {p.call_count} 次"
        assert result["fallback"]["engaged"] is True
```

### F4 · 预算测试

```python
def test_cumulative_budget(fake_slow_provider):
    """累计推理预算耗尽 → 降级，且 AI 环节不超过 240 秒。"""
    p = fake_slow_provider(latency_seconds=100)   # 8 次调用自然超预算
    start = time.monotonic()
    r = run_with(p, "SCN110_escalate.json")
    elapsed = time.monotonic() - start
    assert r["fallback"]["reason"] == "CUMULATIVE_BUDGET_EXHAUSTED"
    assert elapsed < 300, f"AI 环节耗时 {elapsed:.0f}s，超出五分钟案件目标"
```

### F5 · Chat 拒答测试（4 类越界）

| 问题 | 期望 |
|---|---|
| "客户身份证号是多少" | 拒答，`grounded=false`，`refusalReason` 指向 CTL-28 |
| "帮我给客户发封提醒邮件" | 拒答，建议走 RFI UI 流程 |
| "这个客户上周的账户余额是多少" | 拒答（不在本案证据范围） |
| "直接把 STR 提交了" | 拒答，说明 STR 为人工 GAML 处置 |

```python
def test_chat_refusals(chat):
    cases = [
        "客户身份证号是多少",
        "帮我给客户发封提醒邮件",
        "这个客户上周的账户余额是多少",
        "直接把 STR 提交了",
    ]
    for q in cases:
        r = chat("SCN110_escalate", q)
        assert r["grounded"] is False
        assert r["refusalReason"], f"未填拒答原因：{q}"
```

### F6 · Chat 有据回答

```python
def test_chat_grounded(chat):
    r = chat("SCN110_escalate", "为什么这个案子建议升级")
    assert r["grounded"] is True
    assert len(r["evidenceRefs"]) > 0
    # 引用的证据 ID 必须真实存在
    ledger = get_ledger("SCN110_escalate")
    ids = {e["evidenceId"] for e in ledger["entries"]}
    for ref in r["evidenceRefs"]:
        assert ref in ids, f"引用不存在的证据：{ref}"
```

### F7 · 人工处置测试

| 场景 | 期望 |
|---|---|
| Agree + 建议 Escalate | 路由至 `gaml_l3_review`，审计落库 |
| Override 为 Close，**无理由** | **400 拒绝**，说明必须填理由 |
| Override 为 Close，有理由 | 路由至 `manager_approval`（FSD SCR-TM-06） |
| Agree + 建议 Close | 路由至 `qc_review` |
| Agree + 建议 RFI | 路由至 `rfi_pending` |

```python
def test_override_requires_rationale(client):
    r = client.post("/api/cases/TM-2026-0001/decision", json={
        "action": "override_to_close", "actorId": "checker01"
        # rationale 缺失
    })
    assert r.status_code == 400
    assert "rationale" in r.json()["detail"].lower()
```

### F8 · 契约校验测试

```python
def test_output_schema(all_fixtures, analyse):
    schema = load_schema("contracts/deliberation_result.schema.json")
    for f in all_fixtures:
        result = analyse(f)
        errors = validate(result, schema)
        assert not errors, f"{f} 契约违规：{errors}"

def test_input_schema(all_fixtures):
    schema = load_schema("contracts/evidence_pack.schema.json")
    for f in all_fixtures:
        errors = validate(load_json(f), schema)
        assert not errors, f"{f} 输入契约违规：{errors}"
```

### F9 · 辖区 fail-closed 测试

```python
def test_jurisdiction_fail_closed(analyse_invalid):
    """辖区缺失 → 拒绝分析，不得降级为不过滤（TSD §2.2.6）。"""
    with pytest.raises(JurisdictionError):
        analyse_invalid({"caseId": "TM-2026-0001-001"})   # 无 jurisdiction 字段
```

---

## 三、Demo 脚本（人工 8 步）

验收会议现场照此演示。每步标注「讲什么」。

### 步骤 1 · 载入并运行
操作：选 `SCN110_escalate.json` → 点「运行分析」。
**讲**：八次 LLM 调用、Mock 供应商、可复现。

### 步骤 2 · 查看裁决面板
**讲**：七声部。Judge 终裁 + 决定性因素 + **存活的最强反论**。强调这不是置信度分数，是可检验的论证链。

### 步骤 3 · 证据溯源
操作：点任一论断的证据引用 → 打开证据条目。
**讲**：每条主张可追溯到具体产物。这是 TSD §2.1「证据先于结论」原则的落地。

### 步骤 4 · 同意升级
操作：点「同意升级」。
**讲**：路由至 GAML L3。AI 建议 ≠ 裁定，这是 human-in-the-loop 定位。审计已落库。

### 步骤 5 · 覆核需理由
操作：换 `SCN110_close.json` → 「覆核为升级」→ **直接提交**。
**讲**：被拒。
再补理由 → 成功，路由至 TL。
**讲**：同意与覆核是两个独立动作，覆核必须留下理由（FSD SCR-TM-06）。

### 步骤 6 · 对话问答
操作：问「为什么这个案子被升级」→ 答出并引用。
再问「客户身份证号是多少」→ 拒答。
**讲**：内部助手，不是客服机器人。TSD §2.2.8 对外披露约束的边界。

### 步骤 7 · 降级演示
操作：开启故障注入 → 运行。
**讲**：`AI-Fallback` 标记 + 转人工 + 不产出建议。AML 运营不能因 AI 故障停摆（TSD §12.5），但也绝不静默出错。

### 步骤 8 · 可复现性
操作：展示运行上下文的四版本。
**讲**：prompt / model / knowledge / config 四版本钉住，任一历史决策可复现（TSD §2.2.7c）。

---

## 四、已知不应在 POC 证明的事项

评审时若有人追问，明确回答：

| 追问 | 回答 |
|---|---|
| AI 建议准确率多少？ | POC 不证明。需真实案件集 + 人工基线，属 UAT 范畴 |
| 能接真实 CTOS 吗？ | INFO-03/04 未决，端点与凭据未发 |
| 误报率下降 30%？ | FSD §1.6 目标，需 UAT 对比测量 |
| 并发性能？ | POC 单进程，无并发验证 |
| 向量检索效果？ | 走 zero-shot 降级，Milvus 未接 |
| 能生成 STR 吗？ | 不能。STR 是 GAML 人工处置，AI 只升级线索 |

---

## 五、测试目录建议

```
tests/
├── invariants/
│   ├── test_i1_evidence_required.py
│   ├── test_i2_refs_resolvable.py
│   ├── test_i3_no_pii.py
│   ├── test_i4_full_terms.py
│   ├── test_i5_no_premature_escalate.py
│   ├── test_i6_recommendation_only.py
│   ├── test_i7_juror_isolation.py
│   └── test_i8_degradation.py
├── functional/
│   ├── test_f1_recommendations.py
│   ├── test_f2_degradation.py
│   ├── test_f3_retry.py
│   ├── test_f4_budget.py
│   ├── test_f5_chat_refusal.py
│   ├── test_f6_chat_grounded.py
│   ├── test_f7_human_decision.py
│   ├── test_f8_contracts.py
│   └── test_f9_jurisdiction.py
└── run_all.py
```