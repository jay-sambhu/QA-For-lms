# JASUSS Interactive Control & Event Discovery Engine (Phase 20)

## Executive Summary
This document outlines the **Interactive Control & Event Discovery Engine** in JASUSS Phase 20, designed to discover non-link interactive controls.

---

## 1. Targeted Interactive Control Categories

Playwright discovery extracts and interacts with controls beyond traditional `<a>` tags:

1. **Button Controls**: `<button>`, `input[type="button"]`, `input[type="submit"]`, `[role="button"]`.
2. **Form Dropdowns**: `<select>` options, dynamic comboboxes.
3. **Form Inputs**: `<input type="text">`, `<input type="number">`, `<input type="email">`.
4. **Client-Side Event Handlers**: Elements exposing inline `onclick="..."` handlers (e.g. `exportAuditLogsModal()`, `loadLazyChunk()`).
5. **SPA Viewport Tabs**: Buttons with class/aria attributes managing client-side view switching.

---

## 2. Interaction Prioritization Formula

Discovered controls are scored to prioritize high-value actions:

$$\text{interaction\_score} = \text{is\_visible} + \text{is\_form\_submit} + \text{is\_api\_trigger} + \text{is\_destructive} + \text{untested\_weight}$$

This guarantees that form submissions, checkout triggers, and client-side modal exports are prioritized during scan execution.
