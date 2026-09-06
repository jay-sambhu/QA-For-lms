# JASUSS Semantic Form Intelligence & Boundary Data Generator (Phase 20)

## Executive Summary
This document defines the **Semantic Form Intelligence Subsystem** implemented in JASUSS Phase 20 to automatically discover, semantically analyze, and execute multi-step forms using boundary values.

---

## 1. Field Semantic Recognition

The test generator ([`core/test_generator_v2.py`](file:///home/devxgamer/ai-qa-agent/core/test_generator_v2.py)) inspects form field attributes (`id`, `name`, `type`, `placeholder`, `aria-label`) to assign semantic types:

| Semantic Field Category | Matched Attribute Terms | Valid Payload | Boundary / Invalid Payload |
|---|---|---|---|
| **Email** | `email`, `user_email`, `mail` | `qa@example.com` | `invalid-email-address`, `""` |
| **Number / Age** | `age`, `quantity`, `years` | `25` | `100` (overflow boundary), `0`, `-1` |
| **Price / Amount** | `price`, `amount`, `cost` | `49.99` | `-100` (negative value boundary) |
| **Discount Coupon** | `coupon`, `discount`, `promo` | `OFF50` | `INVALID_CODE`, `""` |
| **Item / Resource ID** | `item_id`, `product_id`, `id` | `101` | `404` (defective gadget), `999` |
| **Search Query** | `q`, `search`, `query` | `laptop` | `""`, special characters `<script>` |

---

## 2. Multi-Step Form Execution Strategy
1. **Step Identification**: Discovers multi-page form wizards (e.g. `/wizard/step1` $\rightarrow$ `/wizard/step2`).
2. **Boundary Sequence**: Populates Step 1 with valid fields, then executes Step 2 with boundary values (e.g. `age=100` or `price=-100`).
3. **Validation Oracle Check**: Asserts whether boundary values are cleanly validated or trigger server 500 exceptions.
