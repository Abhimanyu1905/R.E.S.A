---
title: Chargeback Management and Dispute Defense Runbook
doc_type: policy
min_role_level: 2
---

## 1. Dispute Management Platform and Intake
R.E.S.A Support manages payment disputes and merchant chargebacks through the integrated Stripe Radar and Verifi CDRN dispute consoles. When an issuing bank registers a formal customer chargeback:
- A $15.00 non-refundable administrative dispute assessment fee is immediately debited from our operating settlement account.
- The disputed order is flagged with status `DISPUTE_OPEN` in Horizon Portal.
- The customer account is placed on temporary financial suspension pending dispute resolution.
- An alert is automatically posted to the Financial Operations channel `#finops-chargebacks` with the transaction hash and customer token.

## 2. CDRN Pre-Dispute Resolution SLA
To prevent formal chargebacks and protect merchant processing standing:
- Pre-dispute notifications received via the Verifi Cardholder Dispute Resolution Network (CDRN) provide a strict 48-hour resolution window.
- Agents monitoring the pre-dispute queue must evaluate the claim within 24 hours of arrival.
- If the disputed merchandise is unfulfilled or returned, the agent must issue an immediate preemptive merchant refund, which cancels the incoming chargeback and prevents the $15.00 fee.
- If fraud is suspected, the agent cancels any active shipments via warehouse intercept before the parcel reaches the destination sorting hub.

## 3. Compelling Evidence Packet Assembly
For legitimate orders where fraud or non-receipt claims are disputed falsely by the cardholder, agents assemble Evidence Dossier Form CB-88. The dossier must contain the following standardized documentation:
1. Proof of Delivery: Carrier signature manifest showing exact recipient surname and GPS delivery coordinates within 10 meters.
2. Digital Footprint: Customer order placement IP address, timestamp, device fingerprint, and session logs.
3. Communication History: Full customer support transcripts, including order confirmation emails and tracking delivery alerts.
4. Billing Verification: Positive AVS (Address Verification Service) and CVV2 security code match receipts from checkout.

## 4. Representment Deadlines and Performance Targets
- All completed Evidence Dossiers must be submitted to the payment network within 12 calendar days of the formal dispute notification date.
- Late submissions result in automatic merchant forfeiture.
- The dispute team maintains an operational target representment recovery rate of greater than 68% across all commercial card brand categories (Visa, Mastercard, Amex, Discover).
- Monthly dispute win-rate reports are published by the 5th of each month for executive review.

Under compliance clause MARKER-L2-0003, chargeback representment dossiers must be digitally counter-signed by Lead Auditor ID AUD-9921.
