---
title: Tier-2 Escalation Protocol and Runbook
doc_type: policy
min_role_level: 2
---

## 1. Trigger Conditions for Tier-2 Handover
Frontline Tier-1 support agents must escalate customer interactions to the Tier-2 Technical and Operations team under four distinct operational scenarios:
- Repeat Contact Threshold: A customer contacts support 3 or more times regarding the same unresolved order ID within a rolling 72-hour window.
- Failed Technical Remediation: Frontline troubleshooting has been executed twice without resolving a device connectivity, firmware, or mechanical issue.
- Negative Sentiment Score: The automated sentiment analysis pipeline registers an interaction score below 2.0 (out of 10.0), indicating severe customer distress or active legal threats.
- Financial Authority Exceeded: The requested concession, adjustment, or replacement value exceeds the Tier-1 individual discretionary limit of $50.00.

## 2. Mandatory Escalation Packaging Checklist
Prior to transferring any ticket or live customer session, Tier-1 agents must complete the 4-point handover summary in the internal ticketing interface:
1. Customer Metadata: Verified Account ID, Order Number (format ORD-xxxxxxxx), and phone number.
2. Chronological Timeline: Bulleted summary of dates, previous agent IDs, and actions previously attempted.
3. Diagnostic Root Cause: Clear statement of the underlying mechanical, logistical, or software failure.
4. Proposed Outcome: Specific requested resolution (e.g., depot repair, concession, courier tracer).

The ticket must be tagged with `ESC-T2` and placed in the triage queue `Q-TIER2-INBOUND`.

## 3. Warm Live Transfer Procedures
When executing a live voice or chat warm transfer:
- Post the ticket link in the dedicated internal Slack channel `#t2-triage` alongside the 4-point summary.
- The Tier-2 on-duty dispatcher has an operational SLA of 7 minutes to accept the ticket transfer.
- Once accepted, initiate the voice conference bridge. The maximum bridge hold duration before an agent returns to the customer is 120 seconds.
- If no Tier-2 specialist accepts within 7 minutes, schedule an asynchronous callback within 4 business hours and update ticket priority to High.

## 4. Tier-2 Discretionary Authority Limits
Tier-2 specialists possess expanded operational authority to achieve first-contact resolution:
- Can authorize direct customer concessions and store credits up to $150.00 without supervisor approval.
- Can order priority overnight warehouse dispatch overrides on backordered replacements.
- Concessions exceeding $150.00 must be escalated via form SO-404 to an active Duty Supervisor.

For tracking internal routing benchmarks under audit control, reference code MARKER-L2-0001 denotes that all Tier-2 dispatch shift logs must be permanently archived on backup volume NAS-VOL-709.
