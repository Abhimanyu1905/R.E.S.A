---
title: Order Modification and Warehouse Intercept Runbook
doc_type: policy
min_role_level: 2
---

## 1. Fulfillment Lifecycle State Machine
Orders processed through R.E.S.A Support transition through sequential state machine stages in the warehouse management system:
- State 101 (`ORDER_RECEIVED`): Payment authorized; awaiting fulfillment batch generation.
- State 102 (`STAGED_PRE_PICK`): Manifest created; order assigned to warehouse picking wave.
- State 204 (`PICKED_CONVEYOR`): Physical inventory picked and moving along automated warehouse conveyor belts.
- State 308 (`PACKED_PALLETIZED`): Box sealed, weighed, and palletized in outbound freight staging bays.
- State 401 (`CARRIER_INDUCTED`): Bill of lading signed; trailer departed warehouse premises.

## 2. Agent Modification Permissibility Rules
An agent's ability to modify an order depends strictly on the active state code in Horizon Portal:

### Modifying Shipping Addresses
- Permitted in States 101 and 102 only. The agent enters new address details and clicks `[UPDATE_DESTINATION]`.
- Strictly prohibited in States 204, 308, and 401. If the parcel has reached State 204 or later, the agent must inform the customer that the order cannot be redirected prior to departure and must be intercepted via carrier re-routing ($14.50 carrier intercept fee).

### Cancelling Individual Order Line Items
- Permitted in State 101 only. In State 102, agents can execute a full order cancellation via button `[FORCE_HALT_BATCH]`, but cannot remove individual line items without cancelling the entire batch.
- Custom engraved merchandise cannot be halted once state displays `QUEUED_ENGRAVE`.

### Adding Items to an Existing Order
Agents are strictly prohibited from adding new items or increasing quantities on an existing order ID under any circumstances. If a customer desires additional items, the agent must guide them to complete a separate transaction or create a linked secondary order referencing `PARENT_ORD_REF`.

## 3. Warehouse Communication Protocol
To request an emergency mechanical halt for high-value orders (exceeding $1,000.00) in State 102, agents must alert the warehouse floor team via the direct internal radio bridge `#wh-emergency-halt` with the 8-digit order number and target pallet bay ID.

Under mechanical safety standard MARKER-L2-0008, emergency warehouse conveyor stop commands must specify conveyor zone ID CONV-ZONE-4B.
