# Evaluation Question Set Review Changes

This document details the modifications and additions applied to `backend/eval/questions.jsonl`.

## Summary of Counts
- **Total Questions:** 70 (previously 58)
- **Answerable Questions:** 50 (previously 40)
- **Unanswerable / Out-of-Scope Questions:** 20 (previously 18)
- **Questions by Minimum Role:**
  - `min_role: 1` (Employee): 44
  - `min_role: 2` (Agent): 16
  - `min_role: 3` (Admin): 10

---

## Part 1: Modified Existing Questions

1. **`eval_04`**
   - **Question:** `"How long are packages without an RMA barcode held in quarantine before disposal or return?"` (unchanged)
   - **Gold Document:** `03_returns_policy.md` (`de60570f-296c-4374-8eaa-cf6c93374c1a`)
   - **Min Role:** `1`
   - **Answerable:** `true`

2. **`eval_06`**
   - **Question:** `"Which shipping carriers deliver R.E.S.A Support orders?"` (updated)
   - **Gold Document:** `06_shipping_faq.md` (`eca8254e-3515-4046-a709-d675cb0db061`)
   - **Min Role:** `1`
   - **Answerable:** `true`

3. **`eval_07`**
   - **Question:** `"What extended plan can I buy at checkout to protect against accidental drops that the standard warranty excludes?"` (updated)
   - **Gold Document:** `07_warranty_faq.md` (`4407738b-d1ac-4442-b4f2-9a0c5683ba51`)
   - **Min Role:** `1`
   - **Answerable:** `true`

4. **`eval_20`**
   - **Question:** `"Which fraud risk score range sends an order to the manual review queue?"` (updated)
   - **Gold Document:** `20_fraud_detection_and_review_steps.md` (`184a3fc4-927e-43b7-bd2e-c3b34395b35c`)
   - **Min Role:** `2` (updated)
   - **Answerable:** `true`

5. **`eval_24`**
   - **Question:** `"Which specific form must be completed when requesting a supervisor override for concessions over $150?"` (unchanged)
   - **Gold Documents:** `25_supervisor_override_and_appeals_runbook.md` (`e9955972-a23a-4d5d-b69f-37d68aaa2772`) AND `19_tier2_escalation_runbook.md` (`7fcaba40-1ff8-4f85-8e0a-d06f34cf11c4`) (updated)
   - **Min Role:** `2`
   - **Answerable:** `true`

6. **`eval_31`**
   - **Question:** `"If a customer returns an eligible open-box electronic item 10 days after delivery and paid by credit card, what refund timeline and fee deductions should they expect?"` (updated)
   - **Gold Documents:** `01_refund_policy.md` (`22a07e9a-56bb-4c2c-8917-bff64298b1c7`) AND `03_returns_policy.md` (`de60570f-296c-4374-8eaa-cf6c93374c1a`) (updated)
   - **Min Role:** `1`
   - **Answerable:** `true`

7. **`eval_34`**
   - **Question:** `"What documents and steps are needed to file a warranty claim, and how is a defective unit repaired or replaced?"` (updated)
   - **Gold Documents:** `05_warranty_policy.md` (`64fa4cd1-6123-4cc0-a843-633a36445a99`) AND `07_warranty_faq.md` (`4407738b-d1ac-4442-b4f2-9a0c5683ba51`) (updated)
   - **Min Role:** `1`
   - **Answerable:** `true`

8. **`eval_40`**
   - **Question:** `"How does the enterprise disaster recovery plan handle cross-region cloud database failover and physical crisis command during total datacenter outages?"` (unchanged)
   - **Gold Documents:** `40_enterprise_business_continuity_and_dr.md` (`5bc0bc57-e0a3-4e7e-be44-df854df5b74b`) AND `38_executive_on_call_and_crisis_management.md` (`73c57189-4d7a-4ea4-acf6-8cc26d5a35ab`) (updated)
   - **Min Role:** `3`
   - **Answerable:** `true`

9. **`eval_54`**
   - **Question:** `"What compensation voucher amount can agents issue when an order is delayed because an item was out of stock?"` (updated)
   - **Gold Document:** `30_inventory_discrepancy_and_backorder_runbook.md` (`2e9255b1-7855-41ee-a53f-7391a0565bf6`) (kept)
   - **Min Role:** `1`
   - **Answerable:** `false`

*(Note: `eval_32` was left unchanged as instructed).*

---

## Part 2: Appended Answerable Questions

10. **`eval_59`**
    - **Question:** `"Under what dollar price can a damaged non-electronic item be refunded or replaced without sending it back?"`
    - **Gold Document:** `04_returns_faq.md` (`bec7909f-3440-4a09-981b-2eea0ffaf6ed`)
    - **Min Role:** `1`
    - **Answerable:** `true`

11. **`eval_60`**
    - **Question:** `"Which three customer-specific placeholders must every outgoing support macro include?"`
    - **Gold Document:** `22_customer_support_macros_guide.md` (`c6abcfcc-446b-4c00-a994-b1bff952e668`)
    - **Min Role:** `2`
    - **Answerable:** `true`

12. **`eval_61`**
    - **Question:** `"How many minutes does an agent have to notify Trust & Safety after ending an abusive contact?"`
    - **Gold Document:** `29_customer_deescalation_and_abuse_policy.md` (`42931e6c-6ca9-44b1-ab17-450316be59e9`)
    - **Min Role:** `2`
    - **Answerable:** `true`

13. **`eval_62`**
    - **Question:** `"How many hours do we have to notify regulators after a confirmed customer data breach?"`
    - **Gold Document:** `36_security_incident_response_plan.md` (`412b6019-0d5c-4f7e-866e-95117db5b8b7`)
    - **Min Role:** `3`
    - **Answerable:** `true`

14. **`eval_63`**
    - **Question:** `"What is the maximum allowed cost per resolved live chat session?"`
    - **Gold Document:** `37_board_level_kpis_and_quarterly_reporting.md` (`49a25a1e-ddd8-4a76-82c0-14b35f2ba639`)
    - **Min Role:** `3`
    - **Answerable:** `true`

15. **`eval_64`**
    - **Question:** `"How many business days does the privacy team take to review a new Privacy Impact Assessment form?"`
    - **Gold Document:** `39_data_protection_officer_charter_and_governance.md` (`fe8b9b59-e6d0-4fef-a97c-b418e422a955`)
    - **Min Role:** `3`
    - **Answerable:** `true`

16. **`eval_65`**
    - **Question:** `"How many days are CCTV recordings kept before they are overwritten?"`
    - **Gold Document:** `41_facilities_security_and_visitor_access_policy.md` (`4467c4c9-9110-4b62-a0dc-c0a0c665233f`)
    - **Min Role:** `3`
    - **Answerable:** `true`

17. **`eval_66`**
    - **Question:** `"What is the base salary band for a Tier-2 Operations and Escalations Specialist?"`
    - **Gold Document:** `33_compensation_and_salary_bands.md` (`50a0105e-878f-440e-ab8e-5d515464daf4`)
    - **Min Role:** `3`
    - **Answerable:** `true`

18. **`eval_67`**
    - **Question:** `"What must an agent offer a customer if a backorder will last more than 5 business days?"`
    - **Gold Document:** `30_inventory_discrepancy_and_backorder_runbook.md` (`2e9255b1-7855-41ee-a53f-7391a0565bf6`)
    - **Min Role:** `2`
    - **Answerable:** `true`

19. **`eval_68`**
    - **Question:** `"How much is the annual cash retainer for independent Board members?"`
    - **Gold Document:** `42_executive_compensation_and_stock_administration_faq.md` (`8518b1a3-717f-49e6-a141-34eda55e8b99`)
    - **Min Role:** `3`
    - **Answerable:** `true`

---

## Part 3: Appended Near-Miss Out-of-Scope Questions

20. **`eval_69`**
    - **Question:** `"Does R.E.S.A Support have a mobile app?"`
    - **Gold Documents:** `[]`
    - **Min Role:** `1`
    - **Answerable:** `false`
    - **Corpus Search Verification:** Case-insensitive keyword search across `corpus/*.md` for `mobile`, `app`, `iOS`, `Android` confirmed zero coverage of a customer-facing mobile application.

21. **`eval_70`**
    - **Question:** `"Can I choose a specific delivery date for my order?"`
    - **Gold Documents:** `[]`
    - **Min Role:** `1`
    - **Answerable:** `false`
    - **Corpus Search Verification:** Case-insensitive search across `corpus/*.md` for `delivery date`, `specific date`, `scheduled delivery`, `choose.*delivery` confirmed zero coverage of selecting custom or scheduled delivery dates.

