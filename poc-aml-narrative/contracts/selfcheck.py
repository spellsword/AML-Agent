#!/usr/bin/env python3
"""契约自检：校验 schema 合法性 + fixture 符合输入契约。

用法：
    python contracts/selfcheck.py

退出码 0 表示全部通过，可作为 CI 前置检查。
"""
import json
import os
import sys
import glob

try:
    from jsonschema import Draft7Validator
except ImportError:
    print("缺少依赖，请先执行：pip install jsonschema")
    sys.exit(2)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS = {
    "input": os.path.join(BASE, "contracts", "evidence_pack.schema.json"),
    "output": os.path.join(BASE, "contracts", "deliberation_result.schema.json"),
}
KNOWLEDGE = os.path.join(BASE, "contracts", "knowledge", "scenario_knowledge.json")
FIXTURES = sorted(glob.glob(os.path.join(BASE, "fixtures", "*.json")))

failures = []

print("=" * 60)
print("1. Schema 自身合法性")
print("=" * 60)
loaded = {}
for name, path in SCHEMAS.items():
    try:
        schema = json.load(open(path))
        Draft7Validator.check_schema(schema)
        loaded[name] = Draft7Validator(schema)
        print(f"  PASS  {name:<7} {os.path.basename(path)}")
    except Exception as e:
        failures.append(f"schema {name} 非法：{e}")
        print(f"  FAIL  {name:<7} {e}")

print()
print("=" * 60)
print("2. 场景知识与阈值唯一真相源")
print("=" * 60)
try:
    kb = json.load(open(KNOWLEDGE))
    codes = [s["scenarioCode"] for s in kb["scenarios"]]
    print(f"  PASS  知识库版本 {kb['knowledgeBaseVersion']}")
    print(f"  PASS  已实现场景 {codes}")
    for scn in kb["scenarios"]:
        n = len(scn["detectionMetrics"])
        if n == 0:
            failures.append(f"{scn['scenarioCode']} 无检测度量")
        if not scn.get("escalationGate", {}).get("minHits"):
            failures.append(f"{scn['scenarioCode']} 缺升级闸门")
        print(f"        {scn['scenarioCode']}: {n} 项度量, 闸门="
              f"{scn['escalationGate']['minHits']}, "
              f"红旗 {len(scn['redFlags'])}, 豁免 {len(scn['closeConditions'])}")
except Exception as e:
    failures.append(f"知识库读取失败：{e}")
    print(f"  FAIL  {e}")

print()
print("=" * 60)
print("3. Fixture 符合输入契约")
print("=" * 60)
if "input" in loaded:
    for path in FIXTURES:
        name = os.path.basename(path)
        try:
            data = json.load(open(path))
            errs = list(loaded["input"].iter_errors(data))
            if errs:
                for e in errs[:3]:
                    msg = f"{name} 违规 {list(e.path)}: {e.message[:120]}"
                    failures.append(msg)
                    print(f"  FAIL  {msg}")
            else:
                extra = ""
                scn = data.get("alert", {}).get("scenarioCode", "?")
                if scn not in codes:
                    msg = f"{name} 引用未实现场景 {scn}"
                    failures.append(msg)
                    extra = f" (场景 {scn} 未在知识库中)"
                print(f"  PASS  {name:<24} 场景={scn} "
                      f"交易={len(data.get('transactions', []))} 条{extra}")
        except Exception as e:
            failures.append(f"{name} 读取失败：{e}")
            print(f"  FAIL  {name} {e}")

print()
print("=" * 60)
if failures:
    print(f"结果：{len(failures)} 项失败")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("结果：全部通过 ✓")
print("=" * 60)
sys.exit(0)