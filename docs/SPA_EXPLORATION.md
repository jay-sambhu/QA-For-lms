# JASUSS Single Page Application (SPA) Deep Exploration Engine (Phase 20)

## Executive Summary
This document defines the **SPA Exploration Engine** in JASUSS Phase 20, built to discover dynamic client-side SPA routing and async event handlers.

---

## 1. SPA Dynamic Control & Event Dispatching

Single Page Applications (SPAs) often manage views and async API calls without triggering full page navigation. The Phase 20 crawler ([`crawler/crawler.py`](file:///home/devxgamer/ai-qa-agent/crawler/crawler.py)) dispatches events on:

- **Client-Side Tab Controls**: Buttons managing DOM visibility (`showPage('feed-page')`).
- **Async API Fetch Triggers**: Buttons executing async network calls (`fetchFeed(3)`).
- **Lazy Module Loaders**: Dynamic JS chunk loaders (`loadLazyChunk()`).
- **Client-Side Modals**: Inline modal export triggers (`exportAuditLogsModal()`).

---

## 2. Dynamic DOM Stabilization
After clicking interactive controls, JASUSS enforces deterministic stabilization:
- Waits for network idle (`wait_until="domcontentloaded"`).
- Captures new DOM elements, new console exceptions, and asynchronous network HAR entries.
