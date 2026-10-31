---
title: Inventory Discrepancy and Backorder Management Runbook
doc_type: policy
min_role_level: 2
---

## 1. Identification of Inventory Discrepancies
An inventory discrepancy occurs when our storefront displays an item as available for purchase, but physical warehouse cycle counts confirm zero available stock (commonly referred to as "Ghost Inventory"). When an order enters the fulfillment queue and cannot be picked:
- The warehouse management system systematically assigns the line item status code `ERR-STOCKOUT-04`.
- The order is halted from automated wave picking and routed to the Backorder Resolution Queue `Q-BACKORDER`.

## 2. Customer Notification Timelines
Customer transparency is mandatory when inventory discrepancies arise:
- The support system must dispatch an automated inventory delay notification to the customer within 3 hours of the `ERR-STOCKOUT-04` trigger.
- The notification must detail the specific out-of-stock SKU and provide the revised restock arrival date.
- Inquiries regarding backordered stock must be acknowledged by an agent within 4 hours.

## 3. Discretionary Customer Concessions
To mitigate customer dissatisfaction caused by warehouse inventory shortages:
- If the projected backorder delay is between 3 and 5 business days, agents may issue an appeasement discount coupon for $10.00 off a future purchase (Voucher Code `COURTESY-10`).
- If the backorder exceeds 5 business days, the agent must proactively offer the customer three choices:
  1. Maintain the order with complimentary upgrade to Priority Air shipping upon arrival.
  2. Exchange for an alternative in-stock variant of equal or lesser retail value.
  3. Immediate 100% order cancellation and refund back to original payment tender.

## 4. ERP Reconciliation and Cycle Count Audit
When an agent handles a confirmed ghost inventory case:
- The agent must log an internal inventory discrepancy ticket to the supply chain team via Slack channel `#inv-cycle-audit`.
- The ticket must specify the exact SKU number, Warehouse Location Bin (e.g., Bin B-14-R3), and order ID.
- Warehouse operations must perform a physical manual cycle count of that storage bin within 24 hours to prevent repeated customer orders.

Under logistics verification rule MARKER-L2-0012, warehouse ghost inventory reconciliation reports must be signed by Cycle Lead ID STK-6641.
