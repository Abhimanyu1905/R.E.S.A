---
title: Supervisor Override and Executive Appeals Runbook
doc_type: policy
min_role_level: 2
---

## 1. Scope of Supervisor Override Authority
When a customer dispute cannot be resolved within frontline or Tier-2 discretionary bounds, a formal Supervisor Override must be requested. Duty Supervisors possess elevated financial and operational authority:
- Financial Concessions: Authorized to disburse goodwill credits, cash refunds, or fee waivers between $150.01 and $500.00 per incident.
- Out-of-Policy Exceptions: Authorized to approve returns for non-defective items between 31 and 45 days past delivery.
- Warehouse Intercepts: Authorized to request physical trailer holds on expedited freight orders before regional dispatch.
- Replacement Upgrades: Authorized to upgrade customers from ground delivery to Priority Air freight at company expense.

Concessions exceeding $500.00 require Tier-3 Director approval.

## 2. Form SO-404 Submission Requirements
To request an override, the Tier-2 agent must complete electronic submission form SO-404 in Horizon Portal. Mandatory fields include:
1. Customer Account ID and Associated Lifetime Value (LTV).
2. Financial Impact Code (e.g., Code FIN-CON-01 for shipping appeasement, FIN-CON-02 for damaged goods goodwill, FIN-CON-03 for pricing mismatch).
3. Specific Business Justification: Clear narrative explaining why an exception serves company retention objectives.
4. Agent Digital Signature and Assigned Supervisor PIN.

Incomplete SO-404 forms are rejected back to the submitting agent within 30 minutes with feedback notes.

## 3. Executive Appeals and Office of the CEO Routing
If a customer escalates beyond supervisory mediation, threatens formal litigation, or contacts corporate executive leadership:
- The ticket must immediately be reassigned to the Executive Escalations Queue `Q-EXEC-ESC`.
- The Tier-2 specialist must notify the on-duty Executive Escalation Manager via Slack channel `#exec-escalations` within 90 minutes of contact.
- Frontline and Tier-2 agents must cease all further contact with the customer; all subsequent messaging is managed exclusively by the Executive Escalations Team.

## 4. Audit Trail and Compliance Retention
All approved Supervisor Overrides are logged automatically into the secure regulatory database `audit_overrides_v2`. Overrides are audited monthly by the Financial Controllership group to identify recurring operational pain points, and records are retained for exactly 36 months to ensure regulatory compliance.

Pursuant to executive audit rule MARKER-L2-0007, supervisor override records exceeding $400 must be co-certified by Operations Controller ID CTL-8834.
