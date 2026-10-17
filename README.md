# Wasel (واصل) - Product Architecture & Execution Plan

## Multi-Sided Marketplace & Delivery Platform for Iraq & the Middle East

**Wasel (واصل)** connects three primary user types—**Customers (People)**, **Vendors (Restaurants & Markets)**, and **Delivery Drivers**—through a localized backend ecosystem optimized for Iraq and the Middle East market.

---

## 1. Localized Architecture & Core Modules

```
+-----------------------------------------------------------------+
|                        WASEL CENTRAL BACKEND                    |
|    (REST/GraphQL API, Order Routing, Auth, Payment Gateways)    |
+--------+-----------------------+-----------------------+--------+
         |                       |                       |
         v                       v                       v
+------------------+   +------------------+   +------------------+
|   Customer App   |   |   Vendor Portal  |   |  Driver/Delivery |
| (Browse & Order) |   | (Accept & Manage)|   |  App (Fulfill)   |
+------------------+   +------------------+   +------------------+
```

### A. Wasel Customer App (Mobile: iOS & Android)
* **Localization & Languages:** Full Right-To-Left (RTL) support with Arabic, Kurdish (Sorani/Kurmanji), and English interface switching.
* **Discovery & Search:**
  * Browse by categories (Restaurants, Fresh Markets, Bakeries, Supermarkets).
  * Location-aware store discovery using map geofencing.
* **Dynamic Product Catalogs:**
  * **Restaurants:** Customizable menu items (modifiers, add-ons, combo choices).
  * **Markets:** Categorized grocery aisles with weight-based unit pricing (e.g., per kg or per item).
* **Payment Methods:**
  * Cash on Delivery (COD) management and driver reconciliation.
  * Local E-Wallets: **ZainCash**, **FastPay**, **Qi Card**, and Credit/Debit Cards.
* **Order Lifecycle & Real-Time Tracking:**
  * Live status updates (`Order Received` $\rightarrow$ `Preparing` $\rightarrow$ `Ready for Pickup` $\rightarrow$ `Out for Delivery` $\rightarrow$ `Delivered`).
  * Real-time GPS driver tracking via WebSockets.

### B. Wasel Vendor Portal (Web Dashboard & Tablet App)
* **Order Management System (OMS):**
  * High-volume audio notifications for incoming orders (customizable for noisy kitchen/market environments).
  * Multi-state order actions: Accept, adjust prep time, reject, and mark ready.
* **Catalog & Inventory Control:**
  * Instant "86ing" (marking out-of-stock items) to prevent order cancellations.
  * Dynamic price and inventory adjustments.
* **Subscription & Billing Dashboard:**
  * Manage trial status, monthly software subscription renewals, and payout histories.

### C. Wasel Driver / Delivery App (Mobile App)
* **Dispatch Engine:**
  * Smart order allocation based on proximity and delivery route optimization.
  * Cash collection tracking (managing COD payments collected from customers to settle with vendors/platform).
* **Navigation & Order Proof:**
  * Turn-by-turn map integration (Mapbox / Google Maps).
  * Delivery validation via PIN code verification or customer signature.

---

## 2. Subscription Engine & Trial Period Strategy

Wasel utilizes a hybrid monetization strategy tailored for quick merchant onboarding and long-term customer retention.

```
+-----------------------------------------------------------------------+
|                      WASIL MONETIZATION ENGINE                        |
+-----------------------------------+-----------------------------------+
|          Customer Layer           |           Vendor Layer            |
+-----------------------------------+-----------------------------------+
| • 14-Day Free Trial               | • 30-Day Free Merchant Trial      |
| • "Wasel Plus" Pass               | • Flat Monthly Subscription       |
|   (Free Delivery / Zero Fees)     |   (SaaS Model vs High Commission) |
+-----------------------------------+-----------------------------------+
```

### A. Customer Subscription: **Wasel Plus (واصل بلس)**
* **Pricing Structure:** Monthly subscription fee (e.g., 6,000 IQD / month).
* **Member Benefits:**
  * Free delivery on orders over a minimum threshold.
  * Lower service fees on all restaurant and market orders.
  * Priority driver assignment during peak order hours.
* **14-Day Free Trial Strategy:**
  * New users automatically receive **14 days of Wasel Plus** upon account verification.
  * No upfront payment required to enter trial; converts seamlessly via in-app prompts.

### B. Merchant Subscription (Restaurants & Markets)
* **SaaS Subscription Tiers:**
  * **Basic Tier:** Fixed monthly fee for up to X orders/month (ideal for small local stores).
  * **Pro/Unlimited Tier:** Fixed monthly fee with unlimited orders, priority listing, and detailed analytics.
* **30-Day Free Vendor Onboarding Trial:**
  * Zero listing fees and zero fixed monthly charges for the first 30 days.
  * Encourages rapid merchant acquisition across target Iraqi cities.

### C. Driver Access Plan
* **Flexible Dispatch Access:** Monthly platform access fee or small flat transaction fee per delivered order, giving drivers predictable earnings.

---

## 3. Technology Stack

| Layer | Technology Choices | Rationale |
| :--- | :--- | :--- |
| **Mobile Apps** | **Flutter** | Single codebase for iOS and Android with excellent native performance and out-of-the-box RTL/Arabic layout support. |
| **Vendor Portal** | **React.js** | Highly responsive UI ideal for web browsers and operational POS tablets. |
| **Backend Framework** | **Django REST Framework (Python)** or **NestJS (Node.js)** | Robust API building blocks, enterprise-grade security, and simple multi-currency/payment gateway integrations. |
| **Primary Database** | **PostgreSQL + PostGIS** | Relational storage for transactions and orders, paired with spatial indexing for map-based queries. |
| **Caching & Real-Time** | **Redis + WebSockets** | Instant order alerts, live driver GPS streaming, and high-performance session caching. |
| **Payments Infrastructure** | **ZainCash API, FastPay API, Local Gateways** | Direct integration with regional digital wallet providers alongside Cash-on-Delivery reconciliation modules. |

---

## 4. Database Schema Design (Subscription & Order Core)

```
+------------------+         +--------------------+         +--------------------+
|      USERS       |         |      VENDORS       |         |   SUBSCRIPTIONS    |
+------------------+         +--------------------+         +--------------------+
| id (PK)          |<-------1| id (PK)            |<-------1| id (PK)            |
| name             |         | name               |         | entity_type (User/ |
| phone            |         | type               |         |              Vendor|
| language_pref    |         | subscription_id(FK)|         | entity_id (FK)     |
| is_wasel_plus    |         | status             |         | plan_type          |
+------------------+         +--------------------+         | trial_start_date   |
         ^                            ^                     | trial_end_date     |
         |                            |                     | status (Trial/     |
         |                            |                     |         Active)    |
         |                   +--------+                     +--------------------+
         |                   |
         |                   | 1
         |                   v *
         |           +--------------------+                 +--------------------+
         |           |      PRODUCTS      |                 |       ORDERS       |
         |           +--------------------+                 +--------------------+
         |           | id (PK)            |                 | id (PK)            |
         |           | vendor_id (FK)     |                 | customer_id (FK)   |
         |           | name_ar / name_en  |                 | vendor_id (FK)     |
         |           | price              |<---------------*| driver_id (FK)     |
         +--------------------------------------------------| payment_type (COD/ |
                                                            |           Wallet)  |
                                                            | total_amount       |
                                                            +--------------------+
```

---

## 5. Implementation & Execution Roadmap

```
Phase 1: Discovery & Localized UI Design  [Weeks 1–3]   ==============>
Phase 2: Backend Architecture & Auth       [Weeks 4–7]   ====================>
Phase 3: Order Engine & Payments           [Weeks 8–11]  ====================>
Phase 4: Multi-App Development & Trial Logic[Weeks 12–17] =============================>
Phase 5: Field Testing & Deployment        [Weeks 18–20] ===============>
```

### Phase 1: Specifications & Localized Design (Weeks 1–3)
* Finalize Arabic/Kurdish UI design systems in Figma (RTL-first components).
* Map out driver cash-reconciliation workflows for COD orders.
* Define subscription rules and trial period triggers.

### Phase 2: Core Backend & Auth (Weeks 4–7)
* Setup backend infrastructure, PostgreSQL database, and Redis.
* Build phone-number authentication (SMS OTP verification).
* Implement Vendor, Product Catalog, and User API endpoints.

### Phase 3: Order Engine & Regional Payments (Weeks 8–11)
* Integrate local payment gateways (**ZainCash**, **FastPay**, **QI Card**).
* Build WebSocket server for real-time dispatch alerts and tracking.
* Develop automated trial period tracker (switching users from Trial $\rightarrow$ Active $\rightarrow$ Expired).

### Phase 4: Frontend Apps Development (Weeks 12–17)
* **Customer App:** Product listings, Wasel Plus banner integrations, trial activation UI, checkout, and live map tracking.
* **Vendor App:** Order management board, tablet-friendly sound notifications, and subscription management.
* **Driver App:** Job acceptance, map navigation, cash-collected ledger, and delivery confirmation.

### Phase 5: QA, Field Testing & Launch (Weeks 18–20)
* Conduct pilot tests in target city zones (e.g., Baghdad, Erbil, Sulaymaniyah, or Basra).
* Load-test API endpoints and WebSocket channels for peak dinner hours.
* Submit mobile applications to Apple App Store and Google Play Store.
