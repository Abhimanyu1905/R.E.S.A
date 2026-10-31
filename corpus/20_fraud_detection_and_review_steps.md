---
title: Fraud Detection and Manual Order Review Guide
doc_type: policy
min_role_level: 2
---

## 1. Automated Fraud Scoring Tiers
Every checkout transaction on R.E.S.A Support is evaluated in real time by the Sift Fraud Engine. Transactions receive a numerical risk score ranging from 0 to 100, which dictates routing:
- Score 0 to 45 (Green / Low Risk): Automated clearance. Order proceeds immediately to warehouse picking queues.
- Score 46 to 75 (Amber / Moderate Risk): Automatic fulfillment freeze. Order routed to the Manual Review Queue `Q-FRAUD` for agent analysis.
- Score 76 to 100 (Red / Critical Risk): Automatic decline. Order is cancelled systematically, and the card hash is registered in the Sentinel risk database.

## 2. Step-by-Step Manual Review Protocol
Agents assigned to the `Q-FRAUD` queue must complete the following mandatory three-step audit within 4 hours of order ingestion:

### Step 1: Geolocation and IP Geofencing
Compare the customer's transaction IP address against the verified billing ZIP code. If the physical distance between the IP connection node and the billing address exceeds 250 miles without a legitimate corporate VPN indicator, flag the transaction for elevated scrutiny.

### Step 2: Bank Identification Number (BIN) Validation
Verify the 6-digit card BIN against the issuing country database. If a domestic US shipping order utilizes a payment card issued by a financial institution outside North America or Western Europe, execute a secondary address verification match (AVS). An AVS response code other than 'Y' (full address and ZIP match) requires phone verification.

### Step 3: Outbound Voice and SMS Verification
Initiate an automated one-time passkey (OTP) challenge via Telesign SMS to the registered account telephone number. If the telephone number is identified as a disposable VOIP line (e.g., Google Voice, TextNow), the order must not be approved via SMS; the agent must conduct a live verification voice call.

## 3. Order Disposition and Risk Actions
Following completion of the 3-step audit:
- If cleared: Click `[APPROVE_FRAUD_RELEASE]` in Horizon Portal. Document clearance reason code `FR-PASS-01`.
- If confirmed fraudulent: Click `[FORCE_CANCEL_FRAUD]`. Select reason `FRAUD-RISK-HIGH`. This immediately voids authorization holds, notifies the cardholder bank, and adds the shipping address to the permanent blocklist.

For regulatory audit tracing under protocol MARKER-L2-0002, the secondary manual review queue threshold triggers an automated alert to team alias sentinel-review-alert-88.
