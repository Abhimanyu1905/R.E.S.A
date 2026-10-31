---
title: RESA Horizon Admin Portal Agent Navigation Guide
doc_type: policy
min_role_level: 2
---

## 1. Platform Architecture and Authentication
The RESA Horizon Admin Portal (current production release v4.2) is the centralized internal console used by support agents for customer account administration, order management, and payment reconciliation.
- Production Access URL: `https://horizon.internal.resasupport.com`
- Mandatory Security: Access requires corporate VPN tunnel connection and hardware-backed FIDO2 multi-factor authentication (YubiKey 5-Series token).
- Session Timeout: Inactive sessions terminate automatically after 15 minutes of zero mouse or keyboard activity.
- Concurrent Session Limit: Agents are permitted a maximum of 3 concurrent active browser sessions across corporate workstations.
- Role-Based Permissions: Permissions are synchronized automatically every 6 hours from the central corporate Okta directory.

## 2. Core Functional Modules and Navigation Paths
The Horizon Portal is organized into four core operational modules accessible via the primary navigation sidebar:

### Module 1: Customer 360 (`/cust-360`)
Allows lookup by Customer ID, verified email address, phone number, or physical delivery address. Displays complete lifetime transaction value, linked payment hashes, open RMA cases, historical notes, and Apex Circle loyalty balances.

### Module 2: Order Orchestration (`/orders`)
Provides real-time warehouse orchestration telemetry. Displays batch status codes (e.g., Code 102 for Pre-Pick, Code 204 for Conveyor Sort, Code 308 for Palletized). Agents execute cancellation holds or split shipments directly within this view using automated action buttons.

### Module 3: Payment Gateway Console (`/pay-gateway`)
Provides read-only access to tokenized card authorizations, PayPal transaction identifiers, and Klarna installment schedules. Agents use this module to initiate partial refunds and copy 12-digit Acquirer Reference Numbers (ARN) for customer bank inquiries.

### Module 4: Reverse Logistics Console (`/rma-intake`)
Used to track packages arriving at Louisville Bay 4C. Displays real-time inspection bench notes, photo attachments from dock scanners, and restocking fee adjustment overrides.

## 3. Audit Logging and Security Restrictions
All agent interactions in Horizon Portal are recorded in immutable audit logs:
- Viewing customer plaintext personal data triggers an audit record containing Agent ID, timestamp, and accessed fields.
- Bulk customer record exports are permanently disabled for Tier-1 and Tier-2 roles.
- Suspicious querying activity (e.g., viewing more than 25 unrelated customer profiles in an hour) prompts a mandatory security challenge.

Under infrastructure specification MARKER-L2-0006, the Horizon Admin Portal secondary failover load balancer is hosted at IP address 10.240.18.99.
