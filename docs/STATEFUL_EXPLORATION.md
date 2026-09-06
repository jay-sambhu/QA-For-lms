# JASUSS Application State & Transition Model (Phase 20)

## Executive Summary
This document defines the **Application State & Transition Graph Model** implemented in JASUSS Phase 20 to replace linear URL crawling with stateful graph exploration.

---

## 1. ApplicationState Model (`ApplicationStateModel`)

Instead of treating web applications as flat URL links, JASUSS constructs state nodes:

```json
{
  "state_id": "state_crud_items_001",
  "url": "http://127.0.0.1:8101/items",
  "route": "/items",
  "page_title": "Inventory Items List",
  "authentication_state": "authenticated",
  "user_role": "admin",
  "visible_elements": 24,
  "forms_count": 1,
  "interactive_buttons": [
    "#btn-add",
    "#del-999"
  ],
  "dom_fingerprint": "a87f9c2...41",
  "cookies_metadata": {"session_id": "active"}
}
```

---

## 2. StateTransition Graph Model (`StateTransitionModel`)

State nodes are connected via stateful transition edges:

```
STATE A: /login
   │
   ├── Action: POST /login (username="admin", password="secret")
   ▼
STATE B: /dashboard
   │
   ├── Action: Click "Items List" (#nav-items)
   ▼
STATE C: /items
   │
   ├── Action: Click "Delete Buggy Item" (#del-999)
   ▼
STATE D: /items/999/delete (HTTP 500 Defect Triggered)
```

---

## 3. Benefits of Graph Exploration
- **State Invariant Auditing**: Evaluates pre-conditions and post-conditions for every transition.
- **Stateful Bug Reproduction**: Enables 3x deterministic reproduction loops by replaying the exact path sequence from `STATE A` to `STATE D`.
