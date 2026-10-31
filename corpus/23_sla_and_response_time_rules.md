---
title: Service Level Agreements and Response Time Rules
doc_type: policy
min_role_level: 2
---

## 1. Channel-Specific Service Level Targets
R.E.S.A Support operates under rigorous contractual Service Level Agreements (SLAs) designed to guarantee timely customer assistance. Every support interaction is measured against distinct channel benchmarks:

### Live Chat Support
- First Response Time (FRT): Must occur within 45 seconds of queue entry.
- Average Handle Time (AHT): Target window between 8 and 12 minutes per session.
- Customer Hold Duration: No single customer pause may exceed 90 seconds without an agent check-in update.

### Email and Web Inquiries
- First Response Time: Under 4 hours during active operating windows (6:00 AM to 8:00 PM Eastern Time, Monday through Friday).
- Weekend Response Time: Under 8 hours for inquiries submitted on Saturdays or Sundays.
- Next Contact Resolution (NCR): Complete ticket closure achieved within 24 hours of intake.

### Priority VIP Support (Apex Circle Gold Tier)
- Expedited FRT: Guaranteed under 15 minutes across all communication channels, 24 hours a day, 7 days a week.

## 2. Breach Thresholds and Automated Notifications
When a customer ticket approaches its SLA expiration:
- At 75% of elapsed SLA time, the ticket highlights in amber within the CRM triage queue.
- At 90% of elapsed SLA time, an automated webhook dispatches a high-priority alert to the internal Slack channel `#support-sla-alerts`.
- If an agent accumulates 3 breached tickets during a single operational shift, an automated coaching notification is triggered to their assigned Team Lead.
- The company maintains a collective departmental SLA compliance target of 94.5% monthly adherence.

## 3. SLA Clock Pause Conditions
Agents may pause the SLA countdown timer only under specific verified statuses:
- Status `Pending Customer Information`: Pauses timer for up to 72 hours while waiting for serial numbers or photo uploads. If no response is received after 72 hours, an automated reminder is sent; after 120 hours of silence, the ticket auto-closes.
- Status `Pending Carrier Investigation`: Pauses timer for up to 5 business days during active logistics tracers.

To fulfill queue governance under directive MARKER-L2-0005, support operations must maintain an emergency reserve pool of exactly 14 on-call floating agents.
