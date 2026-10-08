# 00 · 源文档冲突裁决表（POC 开发前必读）

> 依据：`Farben_AI_AML_TSD_v0.91_shared_20260930.docx`（下称 **TSD**）、`RHB_NOVA_AML_AI_FSD_v1.0_updated.docx`（下称 **FSD**）、`Draft TO-BE High Level TM+CDD/GAML Process Flow V1.0`（下称 **TO-BE**）。
>
> TSD 历经 13 次修订（v0.66→v0.91），正文内保留了修订痕迹，**同一章节存在互斥表述**。下表逐条裁决，POC 实现以「裁决」列为准，不得回退到「文档冲突」列的表述。

---

## 1. 批次时间窗口（直接决定 POC 是否要实现调度）

| 文档冲突项 | 表述 A | 表述 B | **POC 裁决** |
|---|---|---|---|
| TSD §13.3 夜间批处理窗口 | `Daily, 21:00–02:00 (300 minutes)`，处理腿目标 01:00 完成，01:00–02:00 为重跑 | `Part 1 21:00–23:00 (120min)；Part 2 06:00–09:00 (180min)`；23:00–06:00 为 RHB IT 维护窗口，**无批处理** | **采用表述 B**。Part 1 = Datamart 抽取 + EDL 请求传输；Part 2 = EDL 响应校验装载 + 案件登记 + LLM 分析 + 叙事装配。表述 A 是早期单窗口设计的残留（v0.86 及更早）。<br/>**POC 影响**：POC 不实现 Zena 调度，但文档中的「Part 2 06:00–09:00」必须写进设计文档，避免后续误按 300 分钟窗口排期。 |

## 2. Wrapper 退出码（Zena 判成败的依据）

| 文档冲突项 | 表述 A | 表述 B | **POC 裁决** |
|---|---|---|---|
| TSD §7.10.3 + §12.4 Scenario D | 退出码 `10` = prerequisite/upstream not ready | 退出码 `2` = `FAILED_UPSTREAM_EDL_MISSING` | **采用表述 B（exit 2）**，理由：Scenario D 的最新修订明确写 "Zena receives exit code **2** (FAILED_UPSTREAM_EDL_MISSING / Upstream prerequisite timeout at 09:00 cut-off)"，且该段带删除线轨迹表示旧值已被替换。<br/>**POC 影响**：POC 不实现 wrapper，但 `MockScheduler` 的返回码枚举须按 `0 / 2 / 20 / 99` 定义（§7.10.3），不要用 10。 |

## 3. LLM 部署形态（部署单元的边界，直接影响代码分层）

| 文档冲突项 | 表述 A | 表述 B | **POC 裁决** |
|---|---|---|---|
| TSD §2.1 五大层描述 | "API Gateway (APIG) fronts inbound API traffic and routes it to ELB" | 同段后半"the Elastic Load Balance (ELB) terminates the request" | **采用表述 B**。APIG 为华为云托管服务，RHB 侧架构未采购 APIG（§4.4.1 已述及此点）。<br/>**POC 影响**：跳过 APIG。 |
| TSD §7.11.1 部署形态 A | Internal Huawei Cloud **ModelArts** 端点 | External **Alibaba Cloud DashScope** 端点 | **两者均为待选项，INFO-05 未决**。POC 必须在适配器后留一个 `LLMProvider` 接口，两种形态都不实现具体 SDK。<br/>**POC 裁决：实现 `MockLLMProvider`（离线可复现）+ 预留 `DashScopeProvider` / `ModelArtsProvider` 插槽**，由 `LLM_PROVIDER` 环境变量切换。POC 演示走 Mock，切换真实模型只需换一个 provider 文件。 |

## 4. 场景编号体系（知识库主键，错号会导致整个知识库挂不上）

| 文档冲突项 | 表述 A | 表述 B | **POC 裁决** |
|---|---|---|---|
| TSD §2.2.3.1 | "SCN-001 through SCN-009 in the initial scope" | FSD §1.10 给出 17 个场景：`SCN101/102/105/106/108/109/110/111/113/114/…`，legacy 别名 `SCN_001–009` 保留但不用于新配置 | **采用表述 B**。`SCN-001…009` 形式带连字符的是**已废弃的 legacy 别名**（FSD 附录 K.2 所述 `SCN_001–009` 为 legacy），新配置一律用无连字符的 `SCN1xx/2xx`。<br/>**POC 影响**：知识库 JSON 的 `scenarioCode` 字段取 `SCN110`，不得写 `SCN-001`。 |
| FSD §1.10 场景数 | 标题写 "seventeen (17)" | 表格实际列出编号 1–17（需核对完整表） | **以表格逐行计数为准**，标题数字若与行数不符以行数为准。POC 只需实现 **SCN110（Rapid Movement of Funds）+ SCN201（Mule Account）** 两个场景，其余留占位。 |

## 5. `INFO-xx` 编号冲突（POC 依赖的开放项）

TSD 内部 `INFO-31` 被用于**两个不同事项**：

- §6.10.1：`INFO-31 — Production DNS allocation`（生产 DNS 分配）
- 泰国本地化 Round-3 CR：`INFO-30 / INFO-31`（泰国土地局/黄金交易所 DNFBP schema 与端点）

**POC 裁决**：泰国 DNFBP 相关编号在 POC 中**整体不实现**（属于 Round-3 扩展，非核心叙事链路）。POC 文档只引用 `INFO-03 / INFO-04 / INFO-05` 三项，并明确标注：`INFO-05`（LLM 部署形态未决）→ Mock provider；`INFO-03/04`（CTOS schema/凭据未决）→ 全部本地 fixture。

## 6. 客户信息披露边界（FSD 与 TSD 的口径差）

| 文档 | 表述 | **POC 裁决** |
|---|---|---|
| FSD §3.3 步骤 7 | Checker 在信息不足时可发起 RFI | 与 TSD 一致，无冲突 |
| TSD §2.2.8 | TM 域**不存在对外通信**；CDD/ODD 对外消息**不得含任何客户详情**，仅能请求客户更新资料 | **严格采用 TSD**。<br/>**POC 影响**：POC 的 Chat Agent 是**内部 Checker 助手**，不是客服机器人；它对"客户是谁"类问题必须走内部证据口径回答，且输出受 CTL-28 掩码约束。任何把 POC 演示成"对客问答"的理解都是错的。 |

---

## 7. 冲突规避的强制工程约定

以下三条是**方案层面的硬约束**，写入代码骨架，防止 coder 自行"优化"：

1. **单一真相源**：所有场景阈值、知识条目、模板 ID 只允许在 `contracts/knowledge/*.json` 中定义。Prompt 模板里**禁止**硬编码任何阈值数字。
2. **契约冻结**：§7.11.2 的请求/响应字段名不得改动。需要扩展只能加可选字段，且必须版本化 `templateVersion`。
3. **降级不可绕过**：任何 LLM 调用失败必须走 `AI-Fallback`（TSD §12.5），**不允许用 try/except 吞掉异常后返回一个假结果**。POC 必须有一条可复现的降级演示路径。

---

## 8. 本方案对源文件的取舍声明

POC 是**验证核心链路的原型**，不是生产实现。明确**不做**的部分（防止 coder 越界）：

| 不做 | 理由 |
|---|---|
| 真实 EDL / Datamart / CTOS / Google / CIS / EAI / FINS / RPA 对接 | 依赖 INFO-03/04/05 未决开放项与客户方环境；POC 全用本地 fixture |
| 批量调度（Zena / Celery / 时间窗口） | POC 为单案件同步执行；架构上保留异步接口边界，但不实现调度器 |
| Milvus 向量库 / 相似案例检索 | TSD §12.5 已定义降级路径（zero-shot）；POC 直接走 zero-shot，并显式打标 `retrieval_mode=zero_shot` |
| CDD/ODD 全流程、QC 抽样、Round-Robin、节假日日历 | 超出"叙事生成 + 对话问答"核心范围 |
| 真实多租户/RBAC/SAML/华为云部署 | POC 用单用户本地模式；RBAC 断言以代码注释形式标注 CTL 编号 |