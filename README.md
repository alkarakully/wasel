# Wasel (واصل) - Product Architecture & Execution Plan

## Food & Grocery Delivery App for Iraq & the Middle East

**Wasel (واصل)** is a restaurant-first delivery app in the style of **Talabatey (طلباتي)**: customers pick their location, browse hundreds of local restaurants and supermarkets, see the full price (meal + delivery) before ordering, and get it delivered by a Wasel captain. It connects three user types—**Customers**, **Vendors (Restaurants & Supermarkets)**, and **Delivery Captains**—through one backend built for Iraq.

Wasel follows Talabatey's proven flow and fixes the problems its users complain about most: order status that stops updating, slow support, offers that are hard to use, and drivers asking for tips.

---

## 1. Localized Architecture & Core Modules

```
+-----------------------------------------------------------------+
|                        WASEL CENTRAL BACKEND                    |
|  (REST API, Order Routing, Auth, Payments, Commission Ledger)   |
+--------+-----------------------+-----------------------+--------+
         |                       |                       |
         v                       v                       v
+------------------+   +------------------+   +------------------+
|   Customer App   |   |   Vendor Portal  |   |   Captain App    |
| (Browse & Order) |   | (Accept & Manage)|   |    (Deliver)     |
+------------------+   +------------------+   +------------------+
```

### A. Wasel Customer App (Mobile: iOS & Android)
* **Languages:** Arabic, Kurdish (Sorani/Kurmanji) and English, with full right-to-left layout.
* **Sign-Up & Login:**
  * Phone number with a one-time code sent by **WhatsApp** (default) or SMS.
  * Saved addresses (home, work) with a map pin, since Iraqi street addresses are often imprecise.
* **Home Screen (Talabatey-style):**
  * **Set location first**; everything shown is limited to restaurants that deliver to that spot.
  * Top banner carousel for offers and new restaurants.
  * Cuisine categories: **Popular, Eastern (شرقي), Western (غربي), Fast Food, Sweets, Drinks**.
  * **"Most Ordered" lists** near you to help undecided customers choose.
  * Separate **Supermarket** tab with its own exclusive offers, bundle deals and banners.
* **Restaurant List & Cards:**
  * Clear **Open / Closed** badge with opening hours; closed places sink to the bottom.
  * Delivery fee and estimated delivery time shown on every card.
  * Rating, cuisine type and active discount tag.
* **Menu & Catalog:**
  * **Restaurants:** menu sections, item photos, add-ons, sizes and combo choices.
  * **Supermarkets:** aisles with per-item or per-kg pricing.
* **Cart & Checkout:**
  * **Full price before ordering:** meal cost + delivery fee + service fee, itemized, with no surprises at the door.
  * Discount codes and restaurant offers applied automatically when eligible ("hard-to-use offers" is a top complaint about Talabatey).
  * Optional in-app tip; captains are not allowed to ask for tips at the door.
* **Payment Methods:**
  * Cash on Delivery (most orders in Iraq).
  * Credit/Debit Cards.
  * **Wasel Wallet** with balance, top-ups, refunds and cashback (top up via ZainCash, FastPay, Qi Card).
* **Order Tracking:**
  * Live status (`Received` → `Preparing` → `Ready` → `Out for Delivery` → `Delivered`) pushed over WebSockets, with a push notification at every step.
  * Captain on a live map once picked up.
  * **Call the captain** by phone or in-app internet call (no phone number exposed).
  * Automatic alert to support if an order sits in one status too long, so orders never get stuck "pending".
* **After the Order:**
  * Rate the restaurant and the captain separately.
  * One-tap **Reorder** from order history.
  * **In-app support chat** linked to the order.

### B. Wasel Vendor Portal (Web Dashboard & Tablet App)
* **Order Management:**
  * Loud, repeating alerts for new orders, built for noisy kitchens.
  * Accept, set prep time, reject (with reason), and mark ready.
* **Store Controls:**
  * Open/close toggle and weekly opening hours (drives the Open/Closed badge).
  * Instantly mark items out of stock.
  * Edit prices, photos and menu sections.
* **Offers & Promotions:**
  * Create discounts (percentage, fixed amount, free delivery) and request a spot in the home banner.
* **Earnings Dashboard:**
  * Sales, commission deducted per order, and payout history.

### C. Wasel Captain App (Mobile App)
* **Captain Sign-Up:** Separate onboarding for delivery captains (ID, vehicle, phone verification), similar to Talabatey's captain recruitment app.
* **Order Dispatch:**
  * Nearest available captain is offered the order; route-aware batching at peak hours.
  * Online/offline toggle.
* **Delivery:**
  * Turn-by-turn navigation (Google Maps / Mapbox).
  * Call the customer or restaurant from inside the app.
  * Delivery confirmed with the customer's PIN code.
* **Cash & Earnings:**
  * Ledger of cash collected on COD orders and the amount owed to Wasel.
  * Per-delivery earnings, tips and daily/weekly payouts.

---

## 2. Business Model: Commission + Delivery Fees

Like most regional delivery apps, Wasel earns mainly from a **commission on each order**, plus customer fees. There are no monthly subscription fees for vendors or captains.

```
+-----------------------------------------------------------------------+
|                      WASEL MONETIZATION ENGINE                        |
+-----------------------------------+-----------------------------------+
|          Customer Side            |           Vendor Side             |
+-----------------------------------+-----------------------------------+
| • Delivery fee (by distance)      | • Commission % on each order      |
| • Small service fee per order     | • 30 days commission-free at      |
| • "Wasel Plus" monthly pass       |   launch for new vendors          |
|   (free delivery, lower fees)     |                                   |
+-----------------------------------+-----------------------------------+
```

### A. Vendor Commission (Restaurants & Supermarkets)
* **Commission per order:** a percentage of the food subtotal (e.g., 15–20%), set per vendor so large chains and small shops can get different rates.
* **Commission-free onboarding:** new vendors pay **0% commission for their first 30 days**, to sign restaurants quickly in each new city.
* **Settlement:** Wasel collects card/wallet payments, deducts commission, and pays vendors out weekly. For cash orders, the captain's cash ledger tracks what is owed between captain, vendor and Wasel.

### B. Customer Fees & Wasel Plus (واصل بلس)
* **Delivery fee:** based on distance, always shown on the restaurant card and at checkout.
* **Service fee:** small fixed fee per order.
* **Wasel Plus:** optional monthly pass (e.g., 6,000 IQD / month) with free delivery over a minimum order, lower service fees and priority captains at peak hours. New users get **14 days free**.

### C. Captain Earnings
* Captains keep the delivery fee portion set for each trip (plus 100% of in-app tips). Wasel pays captains per delivery; there is no access fee for captains.

---

## 3. Technology Stack

| Layer | Technology Choices | Rationale |
| :--- | :--- | :--- |
| **Mobile Apps** | **Flutter** | Single codebase for iOS and Android with excellent native performance and out-of-the-box RTL/Arabic layout support. |
| **Vendor Portal** | **React.js** | Highly responsive UI ideal for web browsers and operational POS tablets. |
| **Backend Framework** | **Django REST Framework (Python)** | Mature API toolkit with built-in admin (useful for support and vendor onboarding), strong auth/permissions, and GeoDjango for PostGIS map queries. |
| **Primary Database** | **PostgreSQL + PostGIS** | Relational storage for transactions and orders, paired with spatial indexing for map-based queries. |
| **Caching & Real-Time** | **Redis + Django Channels (WebSockets)** | Instant order alerts, live captain GPS streaming, and high-performance session caching. |
| **Background Jobs** | **Celery + Redis** | Stuck-order alerts, Wasel Plus trial expiry, weekly vendor payouts, and push notifications. |
| **Payments Infrastructure** | **ZainCash API, FastPay API, Local Gateways** | Direct integration with regional digital wallet providers alongside Cash-on-Delivery reconciliation modules. |

---

## 4. Database Schema Design (Order, Commission & Wallet Core)

```
+------------------------+    +------------------------+    +------------------------+
|         USERS          |    |        VENDORS         |    |    WASEL_PLUS_SUBS     |
+------------------------+    +------------------------+    +------------------------+
| id (PK)                |    | id (PK)                |    | id (PK)                |
| name                   |    | owner_id (FK Users)    |    | user_id (FK)           |
| phone                  |    | name                   |    | trial_start_date       |
| role (Customer/        |    | type (Restaurant/      |    | trial_end_date         |
|   Captain/Vendor)      |    |   Supermarket)         |    | renews_at              |
| language_pref          |    | cuisine (Eastern/      |    | status (Trial/Active/  |
|   (ar/ku/en)           |    |   Western/FastFood/..) |    |   Expired)             |
| wallet_balance         |    | location (PostGIS)     |    +------------------------+
+------------------------+    | is_open                |
                              | opening_hours          |
                              | commission_rate        |
                              | commission_free_until  |
                              +------------------------+

+------------------------+    +------------------------+    +------------------------+
|        PRODUCTS        |    |   PRODUCT_MODIFIERS    |    |         OFFERS         |
+------------------------+    +------------------------+    +------------------------+
| id (PK)                |    | id (PK)                |    | id (PK)                |
| vendor_id (FK)         |    | product_id (FK)        |    | vendor_id (FK, null =  |
| name_ar/name_ku/name_en|    | group_name             |    |   platform-wide)       |
| menu_section           |    |   (e.g. Size, Extras)  |    | type (Percent/Fixed/   |
| price                  |    | name_ar/name_ku/name_en|    |   FreeDelivery/Bundle) |
| unit_type (Item/Kg)    |    | price_delta            |    | value                  |
| is_available           |    | is_required            |    | min_order              |
+------------------------+    +------------------------+    | starts_at / ends_at    |
                                                            | is_banner              |
                                                            +------------------------+

+------------------------+    +------------------------+    +------------------------+
|         ORDERS         |    |      ORDER_ITEMS       |    |  ORDER_ITEM_MODIFIERS  |
+------------------------+    +------------------------+    +------------------------+
| id (PK)                |    | id (PK)                |    | id (PK)                |
| customer_id (FK Users) |    | order_id (FK)          |    | order_item_id (FK)     |
| vendor_id (FK)         |    | product_id (FK)        |    | modifier_id (FK)       |
| captain_id (FK Users)  |    | quantity (decimal,     |    | price_delta (snapshot) |
| offer_id (FK)          |    |   for per-kg items)    |    +------------------------+
| status (Received/      |    | unit_price (snapshot)  |
|   Preparing/Ready/     |    | line_total             |
|   OutForDelivery/      |    +------------------------+
|   Delivered/Cancelled) |
| payment_type (COD/     |
|   Card/Wallet)         |
| subtotal               |
| delivery_fee           |
| service_fee            |
| discount               |
| tip                    |
| commission_amount      |
| total_amount           |
| delivery_pin           |
+------------------------+

+------------------------+    +------------------------+
|        RATINGS         |    |  WALLET_TRANSACTIONS   |
+------------------------+    +------------------------+
| id (PK)                |    | id (PK)                |
| order_id (FK)          |    | user_id (FK)           |
| vendor_stars           |    | type (TopUp/Payment/   |
| captain_stars          |    |   Refund/Cashback)     |
| comment                |    | amount                 |
+------------------------+    | order_id (FK, null)    |
                              +------------------------+
```

**Relationships:**
* `USERS` 1 → * `ORDERS` (as `customer_id`, and as `captain_id` for captain accounts).
* `USERS` 1 → * `VENDORS` (via `owner_id`).
* `VENDORS` 1 → * `PRODUCTS`, `VENDORS` 1 → * `ORDERS`, `VENDORS` 1 → * `OFFERS`.
* `PRODUCTS` 1 → * `PRODUCT_MODIFIERS` (add-ons, sizes, combo choices).
* `ORDERS` 1 → * `ORDER_ITEMS` → `PRODUCTS`; each item's chosen add-ons live in `ORDER_ITEM_MODIFIERS`.
* `ORDERS` 1 → 1 `RATINGS`; `USERS` 1 → * `WALLET_TRANSACTIONS`; `USERS` 1 → * `WASEL_PLUS_SUBS`.

**Design notes:**
* Each order stores its own `commission_amount`, worked out from the vendor's `commission_rate` at checkout (0 while `commission_free_until` is in the future), so changing a vendor's rate never rewrites past settlements.
* Prices on order lines are **snapshots** taken at checkout, so later menu price changes never alter past orders.
* `quantity` is a decimal so supermarket items sold per kg (`unit_type = Kg`) use the same table as per-item products.
* `wallet_balance` is a cached total; `WALLET_TRANSACTIONS` is the source of truth.
* Product and modifier names are stored in Arabic, Kurdish and English to match the app's three interface languages.

---

## 5. Implementation & Execution Roadmap

```
Phase 1: Discovery & Localized UI Design     [Weeks 1–3]    ==============>
Phase 2: Backend Architecture & Auth         [Weeks 4–7]    ====================>
Phase 3: Order Engine, Payments & Commission [Weeks 8–11]   ====================>
Phase 4: Customer, Vendor & Captain Apps     [Weeks 12–17]  =============================>
Phase 5: Field Testing & Deployment          [Weeks 18–20]  ===============>
```

### Phase 1: Specifications & Localized Design (Weeks 1–3)
* Finalize Arabic/Kurdish UI design systems in Figma (RTL-first components), using Talabatey's home → restaurant → cart → tracking flow as the baseline.
* Map out captain cash-reconciliation workflows for COD orders.
* Set commission rates, delivery fee bands and Wasel Plus rules.

### Phase 2: Core Backend & Auth (Weeks 4–7)
* Set up the Django REST Framework project, PostgreSQL + PostGIS (GeoDjango), Redis, Celery and Django Channels.
* Build phone-number authentication (WhatsApp OTP with SMS fallback).
* Implement Vendor, Product Catalog, Offers and User API endpoints.

### Phase 3: Order Engine, Payments & Commission (Weeks 8–11)
* Integrate card payments and wallet top-ups via **ZainCash**, **FastPay** and **Qi Card**.
* Build WebSocket server for real-time dispatch alerts, status updates and captain tracking, plus stuck-order alerts for support.
* Build the commission ledger and weekly vendor payouts, and the Wasel Plus trial tracker (Trial → Active → Expired).

### Phase 4: Frontend Apps Development (Weeks 12–17)
* **Customer App:** Location picker, home with banners/cuisines/"Most Ordered", Supermarket tab, restaurant menus, itemized checkout, wallet, live tracking, in-app captain calls, ratings and support chat.
* **Vendor App:** Order board with loud alerts, open/close and hours, out-of-stock toggles, offers, and earnings/commission dashboard.
* **Captain App:** Captain sign-up, job acceptance, map navigation, customer calls, cash-collected ledger, PIN delivery confirmation and earnings.

### Phase 5: QA, Field Testing & Launch (Weeks 18–20)
* Conduct pilot tests in target city zones (e.g., Baghdad, Erbil, Sulaymaniyah, or Basra).
* Sign the first restaurants on 30-day commission-free onboarding before launch.
* Load-test API endpoints and WebSocket channels for peak dinner hours.
* Submit mobile applications to Apple App Store and Google Play Store.
