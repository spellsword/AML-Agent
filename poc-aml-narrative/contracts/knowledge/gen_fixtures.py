#!/usr/bin/env python3
"""生成 POC 四个 fixture。开发阶段可直接运行本脚本重建 fixture。"""
import json, os
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(BASE, "fixtures")
os.makedirs(OUT, exist_ok=True)


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def day(d):
    return d.strftime("%Y-%m-%d")


def esc(id_, st, why):
    return {"evidenceId": id_, "sourceType": st, "summary": why, "citationText": why, "artifactRef": None}


# ============ FIXTURE 1: SCN110 建议 Escalate ============
t0 = datetime(2026, 6, 1)
txn1 = []
# 5 inbound, then 12 outbound within window, high throughput, concentrated
for i in range(5):
    txn1.append({
        "txnRef": f"TXN-A-{i:03d}", "accountRef": "ACC-1", "postedAt": iso(t0 + timedelta(days=i, hours=9)),
        "valueDate": day(t0 + timedelta(days=i)), "direction": "Credit", "amount": 1000000 + i * 1000,
        "currency": "MYR", "channel": "Transfer", "country": "MY",
        "counterpartyRef": f"CP-{i+1:02d}", "counterpartyName": f"Counterparty Alpha {i+1}",
        "counterpartyRisk": "Medium", "description": "Inbound customer payment"
    })
for i in range(12):
    txn1.append({
        "txnRef": f"TXN-B-{i:03d}", "accountRef": "ACC-1", "postedAt": iso(t0 + timedelta(days=6 + i // 3, hours=11)),
        "valueDate": day(t0 + timedelta(days=6 + i // 3)), "direction": "Debit", "amount": 400000 + (i % 3) * 5000,
        "currency": "MYR", "channel": "Wire", "country": "MY",
        "counterpartyRef": "CP-90", "counterpartyName": "Meridian Trading Sdn Bhd",
        "counterpartyRisk": "Medium", "description": "Outbound settlement"
    })
# cash deposit with PCT
txn1.append({
    "txnRef": "TXN-A-CASH", "accountRef": "ACC-1", "postedAt": iso(t0 + timedelta(days=2, hours=10)),
    "valueDate": day(t0 + timedelta(days=2)), "direction": "Credit", "amount": 850000,
    "currency": "MYR", "channel": "Cash", "country": "MY",
    "counterpartyRef": None, "counterpartyName": None, "counterpartyRisk": None,
    "description": "Counter service cash deposit",
    "cashIdentification": {"identifier": "PACT-2026-88112", "amount": 850000, "currency": "MYR"}
})

f1 = {
    "caseId": "TM-2026-0616-001",
    "jurisdiction": "MY",
    "integrity": {"schemaVersion": "1.0.0", "sourceSnapshot": "EDL-SNAP-20260616-OK", "generatedAt": iso(t0)},
    "alert": {
        "alertId": "AL-2026-0616-7781", "scenarioCode": "SCN110",
        "detectedAt": iso(t0 + timedelta(days=15)), "businessDate": day(t0 + timedelta(days=15)),
        "reasonCodes": ["DS24", "HIGH_TURNOVER_OUT"], "riskScore": 78
    },
    "customer": {
        "customerRef": "CUST-001", "type": "Company", "name": "Zayntra Sdn Bhd",
        "riskRating": "Medium", "kycStatus": "Stale", "kycLastMaintenance": day(t0 - timedelta(days=400)),
        "occupation": None,
        "declaredAnnualTurnover": 3800000,
        "declaredSourceOfWealth": None,
        "declaredBusinessNature": "Consumer electronics distribution",
        "relationshipManager": "Priya Nair",
        "pepStatus": "None", "nationality": "MY"
    },
    "accounts": [{
        "accountRef": "ACC-1", "type": "Current", "currency": "MYR", "openedAt": day(t0 - timedelta(days=700)),
        "cardLimit": None, "status": "Active",
        "monthlyCreditTurnover": 5100000, "monthlyDebitTurnover": 4900000
    }],
    "transactions": txn1,
    "ubo": [
        {"subjectRef": "U-0", "subjectType": "Company", "ownershipPercent": 100, "qualifyingUBO": True, "depth": 0,
         "haltReason": None, "providerReference": "CTOS-EXAMPLE-0011"},
        {"subjectRef": "U-1", "subjectType": "Company", "ownershipPercent": 40, "qualifyingUBO": True, "depth": 1,
         "haltReason": None, "providerReference": "CTOS-EXAMPLE-0012"},
        {"subjectRef": "U-2", "subjectType": "Individual", "ownershipPercent": 35, "qualifyingUBO": True, "depth": 2,
         "haltReason": None, "providerReference": "CTOS-EXAMPLE-0013"}
    ],
    "screening": {
        "watchlistHits": [{
            "hitId": "HIT-9001", "listName": "Regional Watchlist", "matchedName": "ZAYNTRA SDN BHD",
            "matchType": "Identity_Full", "band": "Match", "adjudication": "False_Positive", "adjudicatedBy": "qc02"
        }],
        "pepHits": []
    },
    "searchEvidence": [{
        "searchId": "SRCH-1", "query": "Zayntra Sdn Bhd regulatory action adverse news",
        "searchedAt": iso(t0 + timedelta(days=15, hours=2)),
        "results": [{
            "title": "Zayntra Sdn Bhd — company profile",
            "url": "https://registry.example.com/company/zayntra",
            "snippet": "Registered 2019, consumer electronics distribution, active status.",
            "publishedAt": day(t0 - timedelta(days=200)),
            "screenshotRef": "SHOT-SRCH-1-0", "relevance": "Favourable"
        }]
    }],
    "priorAlerts": [{
        "caseId": "TM-2025-0412-006", "scenarioCode": "SCN110", "closedAt": day(t0 - timedelta(days=180)),
        "disposition": "Close", "suppressionReason": "trade settlement pattern consistent with declared business"
    }]
}

# ============ FIXTURE 2: SCN110 建议 Close ============
t1 = datetime(2026, 7, 1)
txn2 = []
for i in range(4):
    txn2.append({
        "txnRef": f"TXN-A2-{i:03d}", "accountRef": "ACC-2", "postedAt": iso(t1 + timedelta(days=i * 4, hours=10)),
        "valueDate": day(t1 + timedelta(days=i * 4)), "direction": "Credit", "amount": 900000 + i * 5000,
        "currency": "MYR", "channel": "Transfer", "country": "MY",
        "counterpartyRef": "CP-21", "counterpartyName": "Harbour Distribution Bhd",
        "counterpartyRisk": "Low", "description": "Invoice-linked wholesale settlement"
    })
for i in range(4):
    txn2.append({
        "txnRef": f"TXN-B2-{i:03d}", "accountRef": "ACC-2", "postedAt": iso(t1 + timedelta(days=i * 4 + 1, hours=14)),
        "valueDate": day(t1 + timedelta(days=i * 4 + 1)), "direction": "Debit", "amount": 880000 + i * 4000,
        "currency": "MYR", "channel": "Transfer", "country": "MY",
        "counterpartyRef": "CP-22", "counterpartyName": "Kiman Retail Sdn Bhd",
        "counterpartyRisk": "Low", "description": "Invoice-linked retail settlement"
    })

f2 = {
    "caseId": "TM-2026-0616-002",
    "jurisdiction": "MY",
    "integrity": {"schemaVersion": "1.0.0", "sourceSnapshot": "EDL-SNAP-20260616-OK", "generatedAt": iso(t1)},
    "alert": {
        "alertId": "AL-2026-0616-7792", "scenarioCode": "SCN110",
        "detectedAt": iso(t1 + timedelta(days=15)), "businessDate": day(t1 + timedelta(days=15)),
        "reasonCodes": ["DS24", "FREQUENCY_BREACH"], "riskScore": 41
    },
    "customer": {
        "customerRef": "CUST-002", "type": "Company", "name": "Harbourline Distribution Sdn Bhd",
        "riskRating": "Low", "kycStatus": "Current", "kycLastMaintenance": day(t1 - timedelta(days=60)),
        "occupation": None,
        "declaredAnnualTurnover": 32000000,
        "declaredSourceOfWealth": "Documented wholesale distribution margin",
        "declaredBusinessNature": "Building materials wholesale distribution",
        "relationshipManager": "Daniel Lim",
        "pepStatus": "None", "nationality": "MY"
    },
    "accounts": [{
        "accountRef": "ACC-2", "type": "Current", "currency": "MYR", "openedAt": day(t1 - timedelta(days=1800)),
        "cardLimit": None, "status": "Active",
        "monthlyCreditTurnover": 9600000, "monthlyDebitTurnover": 9200000
    }],
    "transactions": txn2,
    "ubo": [
        {"subjectRef": "U-10", "subjectType": "Company", "ownershipPercent": 100, "qualifyingUBO": True, "depth": 0,
         "haltReason": None, "providerReference": "CTOS-EXAMPLE-0021"},
        {"subjectRef": "U-11", "subjectType": "Individual", "ownershipPercent": 70, "qualifyingUBO": True, "depth": 1,
         "haltReason": None, "providerReference": "CTOS-EXAMPLE-0022"}
    ],
    "screening": {"watchlistHits": [], "pepHits": []},
    "searchEvidence": [{
        "searchId": "SRCH-2", "query": "Harbourline Distribution Sdn Bhd adverse news",
        "searchedAt": iso(t1 + timedelta(days=15, hours=2)),
        "results": [{
            "title": "Harbourline Distribution — company registry extract",
            "url": "https://registry.example.com/company/harbourline",
            "snippet": "Active since 2021, building materials wholesale, no adverse filings.",
            "publishedAt": day(t1 - timedelta(days=90)),
            "screenshotRef": "SHOT-SRCH-2-0", "relevance": "Neutral"
        }]
    }],
    "priorAlerts": []
}

# ============ FIXTURE 3: SCN201 建议 Escalate（含 STR 票） ============
t2 = datetime(2026, 8, 1)
txn3 = []
for i in range(10):
    txn3.append({
        "txnRef": f"TXN-C-{i:03d}", "accountRef": "ACC-3", "postedAt": iso(t2 + timedelta(days=3, hours=8 + i % 10)),
        "valueDate": day(t2 + timedelta(days=3)), "direction": "Credit", "amount": 49500 + i * 50,
        "currency": "MYR", "channel": "Mobile", "country": "MY",
        "counterpartyRef": f"CP-M{i:02d}", "counterpartyName": f"Mobile Sender {i+1}",
        "counterpartyRisk": None,
        "description": "Mobile money transfer in"
    })
for i in range(9):
    txn3.append({
        "txnRef": f"TXN-D-{i:03d}", "accountRef": "ACC-3", "postedAt": iso(t2 + timedelta(days=3, hours=9 + i % 9)),
        "valueDate": day(t2 + timedelta(days=3)), "direction": "Debit", "amount": 49500 + i * 50,
        "currency": "MYR", "channel": "Online", "country": "MY",
        "counterpartyRef": f"CP-R{i:02d}", "counterpartyName": f"Payee Account {i+1}",
        "counterpartyRisk": None, "description": "Same-day onward transfer"
    })

f3 = {
    "caseId": "TM-2026-0616-003",
    "jurisdiction": "MY",
    "integrity": {"schemaVersion": "1.0.0", "sourceSnapshot": "EDL-SNAP-20260616-OK", "generatedAt": iso(t2)},
    "alert": {
        "alertId": "AL-2026-0616-7804", "scenarioCode": "SCN201",
        "detectedAt": iso(t2 + timedelta(days=12)), "businessDate": day(t2 + timedelta(days=12)),
        "reasonCodes": ["SCN201_MULE", "SAME_DAY_FLOW"], "riskScore": 91
    },
    "customer": {
        "customerRef": "CUST-003", "type": "Individual", "name": "Lim Wei Jian",
        "riskRating": "High", "kycStatus": "Incomplete", "kycLastMaintenance": day(t2 - timedelta(days=200)),
        "occupation": "Salesperson",
        "declaredAnnualTurnover": 42000,
        "declaredSourceOfWealth": "Undisclosed",
        "declaredBusinessNature": None,
        "relationshipManager": "Priya Nair",
        "pepStatus": "None", "nationality": "MY"
    },
    "accounts": [{
        "accountRef": "ACC-3", "type": "Current", "currency": "MYR", "openedAt": day(t2 - timedelta(days=90)),
        "cardLimit": None, "status": "Active",
        "monthlyCreditTurnover": 495000, "monthlyDebitTurnover": 495000
    }],
    "transactions": txn3,
    "ubo": None,
    "screening": {"watchlistHits": [], "pepHits": []},
    "searchEvidence": [{
        "searchId": "SRCH-3", "query": "Lim Wei Jian mule account adverse news",
        "searchedAt": iso(t2 + timedelta(days=12, hours=2)),
        "results": [{
            "title": "Police advisory: account rental mule networks",
            "url": "https://news.example.com/advisory/mule-2026",
            "snippet": "Advisory on account rental schemes involving rapid in-out transfers near RM50,000.",
            "publishedAt": day(t2 - timedelta(days=40)),
            "screenshotRef": "SHOT-SRCH-3-0", "relevance": "Adverse"
        }]
    }],
    "priorAlerts": [{
        "caseId": "TM-2026-0303-011", "scenarioCode": "SCN201", "closedAt": day(t2 - timedelta(days=120)),
        "disposition": "RFI", "suppressionReason": None
    }]
}

# ============ FIXTURE 4: SCN201 建议 RFI ============
t3 = datetime(2026, 9, 1)
txn4 = []
for i in range(6):
    txn4.append({
        "txnRef": f"TXN-E-{i:03d}", "accountRef": "ACC-4", "postedAt": iso(t3 + timedelta(days=2, hours=9 + i)),
        "valueDate": day(t3 + timedelta(days=2)), "direction": "Credit", "amount": 200000 + i * 5000,
        "currency": "MYR", "channel": "Transfer", "country": "MY",
        "counterpartyRef": f"CP-S{i:02d}", "counterpartyName": f"Seller {i+1}",
        "counterpartyRisk": None, "description": "Marketplace settlement receipt"
    })
for i in range(6):
    txn4.append({
        "txnRef": f"TXN-F-{i:03d}", "accountRef": "ACC-4", "postedAt": iso(t3 + timedelta(days=2, hours=13 + i)),
        "valueDate": day(t3 + timedelta(days=2)), "direction": "Debit", "amount": 195000 + i * 5000,
        "currency": "MYR", "channel": "Online", "country": "MY",
        "counterpartyRef": "CP-77", "counterpartyName": "Vendor Consolidated Payable",
        "counterpartyRisk": None, "description": "Vendor payment"
    })

f4 = {
    "caseId": "TM-2026-0616-004",
    "jurisdiction": "MY",
    "integrity": {"schemaVersion": "1.0.0", "sourceSnapshot": "EDL-SNAP-20260616-OK", "generatedAt": iso(t3)},
    "alert": {
        "alertId": "AL-2026-0616-7815", "scenarioCode": "SCN201",
        "detectedAt": iso(t3 + timedelta(days=10)), "businessDate": day(t3 + timedelta(days=10)),
        "reasonCodes": ["SCN201_MULE"], "riskScore": 66
    },
    "customer": {
        "customerRef": "CUST-004", "type": "Individual", "name": "Tan Mei Ling",
        "riskRating": "Medium", "kycStatus": "Current", "kycLastMaintenance": day(t3 - timedelta(days=80)),
        "occupation": "Online reseller",
        "declaredAnnualTurnover": 2600000,
        "declaredSourceOfWealth": "Partially documented",
        "declaredBusinessNature": "Online marketplace reselling",
        "relationshipManager": "Aisha Rahman",
        "pepStatus": "None", "nationality": "MY"
    },
    "accounts": [{
        "accountRef": "ACC-4", "type": "Current", "currency": "MYR", "openedAt": day(t3 - timedelta(days=500)),
        "cardLimit": None, "status": "Active",
        "monthlyCreditTurnover": 1200000, "monthlyDebitTurnover": 1180000
    }],
    "transactions": txn4,
    "ubo": None,
    "screening": {"watchlistHits": [], "pepHits": []},
    "searchEvidence": [{
        "searchId": "SRCH-4", "query": "Tan Mei Ling online reseller adverse news",
        "searchedAt": iso(t3 + timedelta(days=10, hours=2)),
        "results": [{
            "title": "Marketplace seller registry check",
            "url": "https://registry.example.com/seller/tanmei",
            "snippet": "Registered seller since 2024, no enforcement actions found.",
            "publishedAt": day(t3 - timedelta(days=70)),
            "screenshotRef": "SHOT-SRCH-4-0", "relevance": "Favourable"
        }]
    }],
    "priorAlerts": []
}

for name, data in [
    ("SCN110_escalate.json", f1),
    ("SCN110_close.json", f2),
    ("SCN201_escalate.json", f3),
    ("SCN201_rfi.json", f4),
]:
    p = os.path.join(OUT, name)
    with open(p, "w") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print("wrote", p, len(json.dumps(data)), "bytes")