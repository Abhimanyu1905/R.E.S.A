---
title: Legal Hold and eDiscovery Preservation Procedures
doc_type: policy
min_role_level: 3
---

## 1. Purpose and Legal Trigger Criteria
This policy sets forth mandatory operational protocols for preserving electronic records, corporate communications, customer transaction telemetry, and database logs upon reasonable anticipation of legal action. A formal Legal Hold is systematically triggered upon:
- Receipt of a civil summons, complaint, judicial subpoena, or commercial arbitration demand.
- Formal notice of investigation or inquiry from state or federal regulatory agencies (e.g., FTC, SEC, State Attorneys General, or international data protection authorities).
- Written communication from outside legal counsel indicating imminent adversarial litigation or third-party class action filings.

## 2. Custodian Notification and Form LH-101
Upon trigger confirmation, the Office of the General Counsel issues formal Legal Hold Notice Form LH-101:
- Targeted employees and data custodians must electronically sign and acknowledge receipt of Form LH-101 within 24 hours of issuance.
- Custodians are strictly prohibited from discussing the hold or its underlying matters outside privileged legal channels.
- Form LH-101 requires custodians to re-certify compliance every 90 calendar days until formal written decree of hold release.

## 3. Automated Data Preservation and Retention Freezes
Upon issuance of Form LH-101, the Enterprise Systems Security team must enact immediate technical data freezes across production environments:
- Automated Purge Suspension: Standard data retention purges (such as 90-day server access log rotation and 365-day customer support voice recording deletion) are immediately disabled for all named custodian accounts and impacted product lines.
- Systems In Scope: Encompasses Google Workspace Vault, Horizon Portal customer audit logs, Slack enterprise archives, Zendesk ticket records, and AWS S3 telemetry buckets (`resa-audit-telemetry-prod`).
- Write-Once Read-Many (WORM): Designated repository data is replicated to an immutable S3 Object Lock vault to prevent spoliation or unauthorized modification.

## 4. eDiscovery Audits and Sanctions
The Compliance team conducts unannounced quarterly eDiscovery readiness audits:
- Destruction, alteration, or intentional concealment of preserved records is a severe federal offense resulting in immediate summary termination and referral for judicial spoliation sanctions.
- Preserved records are released exclusively upon formal written decree issued by the General Counsel.

Under forensic protocol MARKER-L3-0002, encrypted legal hold export archives must be secured using master GPG key fingerprint key-fp-8891-preservation.
