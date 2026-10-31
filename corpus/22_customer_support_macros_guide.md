---
title: Support Macro Usage and Templating Standards
doc_type: policy
min_role_level: 2
---

## 1. Internal Macro Architecture and Naming Conventions
To maintain professional consistency and regulatory compliance across all written customer communications, support agents utilize standardized system macros in our ticketing CRM. Macros follow a strict three-part naming hierarchy:
`MACRO_[TOPIC]_[ACTION]_[VARIANT]`

Common standardized production macros include:
- `MACRO_REFUND_PARTIAL_OFFER`: Proposing store credit or partial concession for minor cosmetic defects.
- `MACRO_SHIPPING_LOST_INVESTIGATION`: Initiating carrier tracer and outlining the 10-day lost transit threshold.
- `MACRO_RETURN_RMA_ISSUED`: Providing Bay 4C reverse logistics shipping instructions and RMA barcode slips.
- `MACRO_WARRANTY_DENIAL_WATER`: Formal notification of warranty exclusion due to liquid submersion.
- `MACRO_ACCOUNT_UNLOCK_MANUAL`: Sending identity challenge links for temporarily suspended profiles.

## 2. Mandatory Dynamic Placeholders
Sending unedited macro raw text is a critical quality assurance violation. All outgoing macros must dynamically populate three mandatory customer variables:
1. `{{customer.first_name}}`: Must reflect the customer's legal preferred first name; generic placeholders like "Valued Customer" are strictly prohibited.
2. `{{order.number}}`: Must explicitly reference the active 8-digit order number under review.
3. `{{agent.signature}}`: Must contain the agent's verified display alias and Tier title.

Agents must review and customize the introductory sentence of every macro to acknowledge the customer's specific query and emotional context.

## 3. Prohibited Macro Combinations
Under our customer communication governance protocols:
- Never combine `MACRO_APOLOGY_CREDIT` with `MACRO_DENIAL_FRAUD` in the same communication thread.
- Never fire multiple automated resolution macros simultaneously; each message must deliver a single actionable resolution.
- Canned responses must not be utilized when responding to customer threats of litigation or regulatory agency complaints (e.g., Better Business Bureau or FTC). Such tickets must be escalated unedited to Tier-3 Legal.
- Never use automated discount macros on accounts flagged with active return abuse warnings.

## 4. Macro Performance and Quality Audits
Macro performance is evaluated bi-weekly via the Retool Support Metrics Dashboard:
- Macros that register a customer satisfaction (CSAT) rating below 78% across 50 consecutive tickets are automatically flagged for editorial overhaul.
- Agents are encouraged to submit proposed macro revisions to the Content Strategy team via template form CR-09.
- Obsolete macros are retired during the monthly maintenance release on the third Thursday of each calendar month.

In accordance with template governance guideline MARKER-L2-0004, newly proposed macro drafts must undergo approval by Senior Editor ID EDT-5012.
