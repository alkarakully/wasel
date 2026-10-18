/* Wasel operations page: staff watch the platform and act on it.
   Data comes from /api/ops/ (session sign-in through the admin) and refreshes
   every 10 seconds while the tab is visible. */
(function () {
  "use strict";

  var STRINGS = {
    ar: {
      payouts: "المدفوعات", dueToStores: "مستحق للمتاجر", weeklyNote: "كشف أسبوعي من السبت إلى الجمعة لكل متجر.", due: "مستحق", paid: "مدفوع",
      closeWeeks: "إنشاء الكشوفات المتأخرة", statements: "الكشوفات", week: "الأسبوع", foodSales: "مبيعات الطعام", payout: "المستحق",
      markPaid: "تم الدفع", reference: "رقم التحويل", noStatements: "لا توجد كشوفات هنا.", madeStatements: "أُنشئ {n} كشف",
      tag: "العمليات", overview: "نظرة عامة", orders: "الطلبات", captains: "الكباتن", stores: "المتاجر", users: "الحسابات",
      admin: "الإدارة", signOut: "خروج", todaySales: "مبيعات اليوم", commission: "عمولة واصل", avgDelivery: "متوسط التوصيل",
      activeOrders: "طلبات جارية", openAlerts: "تنبيهات مفتوحة", onlineCaptains: "كباتن متصلون", openStores: "متاجر مفتوحة",
      thisMonth: "هذا الشهر", stuckOrders: "طلبات متأخرة", topStores: "الأكثر طلباً اليوم", liveOrders: "الطلبات الجارية",
      status: "الحالة", store: "المتجر", customer: "الزبون", captain: "الكابتن", total: "المجموع", age: "المدة",
      owner: "المالك", commissionRate: "العمولة", ordersToday: "طلبات اليوم", salesToday: "مبيعات اليوم", open: "مفتوح",
      phone: "الهاتف", name: "الاسم", role: "الدور", joined: "الانضمام", active: "نشط", searchUsers: "ابحث بالرقم أو الاسم",
      addAccount: "حساب جديد", ordersCount: "{n} طلب", deliveredCount: "{n} تم توصيله", minutes: "{n} د", none: "لا يوجد",
      fees: "رسوم الخدمة {s} · التوصيل {d}", cancelledCount: "{n} ملغى", resolve: "تم", noAlerts: "لا توجد طلبات متأخرة الآن.",
      noOrders: "لا توجد طلبات جارية.", noCaptains: "لا يوجد كباتن نشطون اليوم.", noStoreOrders: "لا طلبات بعد اليوم.",
      online: "متصل", offline: "غير متصل", seenAgo: "قبل {n} د", seenNow: "الآن", carrying: "يوصّل #{id}",
      all: "الكل", role_customer: "زبون", role_captain: "كابتن", role_vendor: "صاحب متجر", staff: "موظف",
      st_received: "جديد", st_preparing: "قيد التحضير", st_ready: "جاهز", st_out_for_delivery: "بالطريق",
      r_not_accepted: "المتجر لم يقبل", r_not_ready: "تجاوز وقت التجهيز", r_no_captain: "لا يوجد كابتن",
      r_not_picked_up: "جاهز ولم يُستلم", r_delivery_late: "التوصيل متأخر", edit: "تعديل",
      connection: "تعذّر تحديث البيانات. نعيد المحاولة...", sales: "المبيعات", currency: "د.ع", unassigned: "—",
    },
    ku: {
      payouts: "پارەدانەکان", dueToStores: "قەرزی دووکانەکان", weeklyNote: "کەشفی هەفتانە لە شەممە تا هەینی بۆ هەر دووکانێک.", due: "ماوە", paid: "دراوە",
      closeWeeks: "دروستکردنی کەشفە دواکەوتووەکان", statements: "کەشفەکان", week: "هەفتە", foodSales: "فرۆشی خواردن", payout: "شایستە",
      markPaid: "درا", reference: "ژمارەی گواستنەوە", noStatements: "هیچ کەشفێک نییە.", madeStatements: "{n} کەشف دروستکرا",
      tag: "کارگێڕی", overview: "پوختە", orders: "داواکارییەکان", captains: "کاپتنەکان", stores: "دووکانەکان", users: "هەژمارەکان",
      admin: "بەڕێوەبردن", signOut: "دەرچوون", todaySales: "فرۆشی ئەمڕۆ", commission: "کۆمیسیۆنی واصل", avgDelivery: "تێکڕای گەیاندن",
      activeOrders: "داواکاری چالاک", openAlerts: "ئاگادارکردنەوەی کراوە", onlineCaptains: "کاپتنی سەرهێڵ", openStores: "دووکانی کراوە",
      thisMonth: "ئەم مانگە", stuckOrders: "داواکاری دواکەوتوو", topStores: "زۆرترین داواکراو ئەمڕۆ", liveOrders: "داواکارییە چالاکەکان",
      status: "دۆخ", store: "دووکان", customer: "کڕیار", captain: "کاپتن", total: "کۆ", age: "ماوە",
      owner: "خاوەن", commissionRate: "کۆمیسیۆن", ordersToday: "داواکاری ئەمڕۆ", salesToday: "فرۆشی ئەمڕۆ", open: "کراوە",
      phone: "ژمارە", name: "ناو", role: "ڕۆڵ", joined: "بەشداربوون", active: "چالاک", searchUsers: "بە ژمارە یان ناو بگەڕێ",
      addAccount: "هەژماری نوێ", ordersCount: "{n} داواکاری", deliveredCount: "{n} گەیەندرا", minutes: "{n} خ", none: "هیچ",
      fees: "خزمەتگوزاری {s} · گەیاندن {d}", cancelledCount: "{n} هەڵوەشاوە", resolve: "تەواو", noAlerts: "ئێستا هیچ داواکارییەکی دواکەوتوو نییە.",
      noOrders: "هیچ داواکارییەکی چالاک نییە.", noCaptains: "ئەمڕۆ هیچ کاپتنێکی چالاک نییە.", noStoreOrders: "ئەمڕۆ هێشتا داواکاری نییە.",
      online: "سەرهێڵ", offline: "دەرهێڵ", seenAgo: "پێش {n} خ", seenNow: "ئێستا", carrying: "دەگەیەنێت #{id}",
      all: "هەموو", role_customer: "کڕیار", role_captain: "کاپتن", role_vendor: "خاوەن دووکان", staff: "کارمەند",
      st_received: "نوێ", st_preparing: "ئامادە دەکرێت", st_ready: "ئامادەیە", st_out_for_delivery: "لە ڕێگایە",
      r_not_accepted: "دووکان قبوڵی نەکردووە", r_not_ready: "کاتی ئامادەبوون تێپەڕی", r_no_captain: "کاپتن نییە",
      r_not_picked_up: "ئامادەیە بەڵام وەرنەگیراوە", r_delivery_late: "گەیاندن دواکەوتووە", edit: "دەستکاری",
      connection: "نوێکردنەوە سەرکەوتوو نەبوو. هەوڵ دەدەینەوە...", sales: "فرۆش", currency: "د.ع", unassigned: "—",
    },
    en: {
      payouts: "Payouts", dueToStores: "Due to stores", weeklyNote: "One statement per store each week, Saturday to Friday.", due: "Due", paid: "Paid",
      closeWeeks: "Make missing statements", statements: "Statements", week: "Week", foodSales: "Food sales", payout: "Payout",
      markPaid: "Mark paid", reference: "Transfer number", noStatements: "No statements here.", madeStatements: "{n} statements made",
      tag: "Operations", overview: "Overview", orders: "Orders", captains: "Captains", stores: "Stores", users: "Accounts",
      admin: "Admin", signOut: "Sign out", todaySales: "Sales today", commission: "Wasel commission", avgDelivery: "Average delivery",
      activeOrders: "Active orders", openAlerts: "Open alerts", onlineCaptains: "Captains online", openStores: "Stores open",
      thisMonth: "This month", stuckOrders: "Stuck orders", topStores: "Top stores today", liveOrders: "Orders in progress",
      status: "Status", store: "Store", customer: "Customer", captain: "Captain", total: "Total", age: "Age",
      owner: "Owner", commissionRate: "Commission", ordersToday: "Orders today", salesToday: "Sales today", open: "Open",
      phone: "Phone", name: "Name", role: "Role", joined: "Joined", active: "Active", searchUsers: "Search by phone or name",
      addAccount: "Add account", ordersCount: "{n} orders", deliveredCount: "{n} delivered", minutes: "{n} min", none: "None",
      fees: "Service {s} · delivery {d}", cancelledCount: "{n} cancelled", resolve: "Done", noAlerts: "No stuck orders right now.",
      noOrders: "No orders in progress.", noCaptains: "No captains active today.", noStoreOrders: "No orders yet today.",
      online: "Online", offline: "Offline", seenAgo: "{n} min ago", seenNow: "Just now", carrying: "Delivering #{id}",
      all: "All", role_customer: "Customer", role_captain: "Captain", role_vendor: "Store owner", staff: "Staff",
      st_received: "New", st_preparing: "Preparing", st_ready: "Ready", st_out_for_delivery: "On the way",
      r_not_accepted: "Store hasn't accepted", r_not_ready: "Past its ready time", r_no_captain: "No captain",
      r_not_picked_up: "Ready, not picked up", r_delivery_late: "Delivery is late", edit: "Edit",
      connection: "Couldn't refresh. Retrying...", sales: "Sales", currency: "IQD", unassigned: "—",
    },
  };
  var STATUSES = ["received", "preparing", "ready", "out_for_delivery"];
  var REFRESH_MS = 10000;

  var lang = STRINGS[read("wasel_lang")] ? read("wasel_lang") : "ar";
  var view = "overview";
  var role = "";
  var query = "";
  var map = null;
  var markers = {};
  var fitted = false;

  function $(id) { return document.getElementById(id); }
  function read(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* private mode */ } }

  function t(key, vars) {
    var text = STRINGS[lang][key] || STRINGS.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.replace("{" + k + "}", vars[k]); });
    return text;
  }

  function number(n) { return Number(n || 0).toLocaleString("en-US"); }
  function money(n) { return lang === "en" ? number(n) + " IQD" : number(n) + " د.ع"; }

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (key) {
      if (key === "class") node.className = attrs[key];
      else if (key === "text") node.textContent = attrs[key];
      else if (key.indexOf("on") === 0) node.addEventListener(key.slice(2), attrs[key]);
      else node.setAttribute(key, attrs[key]);
    });
    (children || []).forEach(function (child) {
      if (child == null) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }

  function icon(name) { return el("i", { class: "ph-light ph-" + name, "aria-hidden": "true" }); }

  function csrf() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function api(path, body) {
    var options = { credentials: "same-origin", headers: { Accept: "application/json" } };
    if (body) {
      options.method = "POST";
      options.headers["Content-Type"] = "application/json";
      options.headers["X-CSRFToken"] = csrf();
      options.body = JSON.stringify(body);
    }
    return fetch("/api/ops/" + path, options).then(function (response) {
      if (response.status === 401 || response.status === 403) {
        window.location.href = "/admin/login/?next=/ops/";
        throw new Error("signed out");
      }
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    });
  }

  function empty(text) { return el("li", { class: "empty" }, [icon("check-circle"), text]); }

  function statusChip(status) {
    return el("span", { class: "chip st-" + status, text: t("st_" + status) });
  }

  function editLink(href) {
    return el("a", { class: "row-link", href: href, title: t("edit") }, [icon("arrow-square-out")]);
  }

  function toggle(checked, label, onChange) {
    var input = el("input", { type: "checkbox", role: "switch", "aria-label": label });
    input.checked = checked;
    input.addEventListener("change", function () { onChange(input.checked, input); });
    return el("label", { class: "switch" }, [input]);
  }

  // --- Overview ---------------------------------------------------------------

  function renderOverview(data) {
    var today = data.today, live = data.live;
    $("k-sales").textContent = money(today.sales);
    $("k-orders").textContent = t("ordersCount", { n: number(today.orders) });
    $("k-delivered").textContent = t("deliveredCount", { n: number(today.delivered) });
    $("k-commission").textContent = money(today.commission);
    $("k-fees").textContent = t("fees", { s: money(today.service_fees), d: money(today.delivery_fees) });
    $("k-avg").textContent = today.avg_delivery_minutes == null ? "—" : t("minutes", { n: today.avg_delivery_minutes });
    $("k-cancelled").textContent = t("cancelledCount", { n: today.cancelled });
    $("k-active").textContent = number(live.active_orders);
    $("k-alerts").textContent = number(live.open_alerts);
    $("tile-alerts").classList.toggle("warn", live.open_alerts > 0);
    $("k-captains").textContent = number(live.online_captains);
    // Isolated left-to-right so "4 / 5" doesn't flip in Arabic.
    $("k-stores").textContent = "\u2066" + live.open_stores + " / " + live.stores + "\u2069";

    var counter = $("count-orders");
    counter.hidden = !live.active_orders;
    counter.textContent = live.active_orders;

    var pipeline = $("pipeline");
    pipeline.replaceChildren();
    var total = Math.max(1, live.active_orders);
    STATUSES.forEach(function (status) {
      var n = data.by_status[status] || 0;
      pipeline.appendChild(el("div", { class: "stage st-" + status, style: "flex-grow:" + Math.max(n, 0.0001) / total, title: t("st_" + status) + ": " + n }, [
        el("span", { text: t("st_" + status) + " " + n }),
      ]));
    });

    var month = $("k-month");
    month.replaceChildren();
    [["sales", money(data.month.sales)], ["commission", money(data.month.commission)], ["orders", number(data.month.orders)]].forEach(function (pair) {
      month.appendChild(el("dt", { text: t(pair[0]) }));
      month.appendChild(el("dd", { text: pair[1] }));
    });

    var top = $("top-stores");
    top.replaceChildren();
    if (!data.top_stores.length) top.appendChild(empty(t("noStoreOrders")));
    data.top_stores.forEach(function (store, i) {
      top.appendChild(el("li", { style: "--i:" + i }, [
        el("span", { class: "rank", text: String(i + 1) }),
        el("span", { class: "grow", text: store.name }),
        el("span", { class: "muted", text: t("ordersCount", { n: store.orders }) }),
        el("strong", { text: money(store.sales) }),
      ]));
    });
  }

  function renderAlerts(alerts) {
    var list = $("alerts");
    list.replaceChildren();
    if (!alerts.length) list.appendChild(empty(t("noAlerts")));
    alerts.forEach(function (alert, i) {
      var done = el("button", { type: "button", class: "small", text: t("resolve") });
      done.addEventListener("click", function () {
        done.disabled = true;
        api("alerts/" + alert.id + "/resolve/", {}).then(refresh, function () { done.disabled = false; });
      });
      list.appendChild(el("li", { class: "alert", style: "--i:" + i }, [
        el("span", { class: "alert-icon" }, [icon("warning")]),
        el("div", { class: "grow" }, [
          el("strong", { text: "#" + alert.order + " · " + alert.store }),
          el("span", { class: "muted", text: t("r_" + alert.reason) + " · " + t("minutes", { n: alert.minutes }) }),
        ]),
        editLink("/admin/orders/order/" + alert.order + "/change/"),
        done,
      ]));
    });
  }

  // --- Orders -------------------------------------------------------------------

  function renderOrders(orders) {
    var body = $("orders");
    body.replaceChildren();
    if (!orders.length) body.appendChild(el("tr", {}, [el("td", { colspan: "8", class: "empty-cell", text: t("noOrders") })]));
    orders.forEach(function (order, i) {
      var late = order.alerts.length > 0;
      body.appendChild(el("tr", { class: late ? "late" : "", style: "--i:" + Math.min(i, 12) }, [
        el("td", { class: "id", text: "#" + order.id }),
        el("td", {}, [statusChip(order.status)].concat(order.alerts.map(function (reason) {
          return el("span", { class: "chip warn", text: t("r_" + reason) });
        }))),
        el("td", { text: order.store }),
        el("td", { dir: "auto", text: order.customer }),
        el("td", { dir: "auto", text: order.captain || t("unassigned") }),
        el("td", { class: "num", text: money(order.total) }),
        el("td", { class: "num" + (late ? " late-text" : ""), text: t("minutes", { n: order.minutes }) }),
        el("td", {}, [editLink("/admin/orders/order/" + order.id + "/change/")]),
      ]));
    });
  }

  // --- Captains ----------------------------------------------------------------

  function ensureMap() {
    if (map || !window.maplibregl) return;
    var styles = JSON.parse($("map-styles").textContent);
    var dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    map = new maplibregl.Map({
      container: "map",
      style: dark ? styles.dark : styles.light,
      center: [44.4214, 33.3045],
      zoom: 11,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
  }

  function renderCaptains(captains) {
    var list = $("captains");
    list.replaceChildren();
    if (!captains.length) list.appendChild(empty(t("noCaptains")));
    var seen = {};
    captains.forEach(function (c, i) {
      var minutes = Math.round(c.seconds_ago / 60);
      list.appendChild(el("li", { class: "person", style: "--i:" + Math.min(i, 12) }, [
        el("span", { class: "avatar" + (c.online ? " on" : "") }, [icon("moped")]),
        el("div", { class: "grow" }, [
          el("strong", { dir: "auto", text: c.name || c.phone }),
          el("span", { class: "muted", dir: "ltr", text: c.phone }),
        ]),
        el("div", { class: "end" }, [
          el("span", { class: "chip " + (c.online ? "on" : "off"), text: t(c.online ? "online" : "offline") }),
          el("span", { class: "muted small-text", text: c.order ? t("carrying", { id: c.order }) : (minutes < 1 ? t("seenNow") : t("seenAgo", { n: minutes })) }),
        ]),
      ]));
      if (map && c.lat != null) {
        seen[c.id] = true;
        var marker = markers[c.id];
        if (!marker) {
          var dot = el("div", { class: "cap-marker" + (c.online ? " on" : "") }, [icon("moped")]);
          marker = new maplibregl.Marker({ element: dot }).setLngLat([c.lng, c.lat]).addTo(map);
          markers[c.id] = marker;
        }
        marker.setLngLat([c.lng, c.lat]);
        marker.getElement().classList.toggle("on", c.online);
        marker.getElement().title = (c.name || c.phone) + (c.order ? " · #" + c.order : "");
      }
    });
    Object.keys(markers).forEach(function (id) {
      if (!seen[id]) { markers[id].remove(); delete markers[id]; }
    });
    // Frame the captains once; after that, staff pan and zoom freely.
    var points = captains.filter(function (c) { return c.lat != null; });
    if (map && points.length && !fitted) {
      fitted = true;
      var bounds = new maplibregl.LngLatBounds();
      points.forEach(function (c) { bounds.extend([c.lng, c.lat]); });
      map.fitBounds(bounds, { padding: 80, maxZoom: 14, duration: 0 });
    }
  }

  // --- Stores ----------------------------------------------------------------------

  function renderStores(stores) {
    var body = $("stores");
    body.replaceChildren();
    stores.forEach(function (store, i) {
      body.appendChild(el("tr", { style: "--i:" + Math.min(i, 12) }, [
        el("td", {}, [el("strong", { text: store.name })]),
        el("td", { dir: "auto", text: store.owner }),
        el("td", { class: "num", text: store.commission_rate + "%" }),
        el("td", { class: "num", text: number(store.orders_today) }),
        el("td", { class: "num", text: money(store.sales_today) }),
        el("td", {}, [toggle(store.is_open, store.name, function (on, input) {
          input.disabled = true;
          api("stores/" + store.id + "/open/", { is_open: on }).then(refresh, function () { input.checked = !on; })
            .finally(function () { input.disabled = false; });
        })]),
        el("td", {}, [editLink("/admin/vendors/vendor/" + store.id + "/change/")]),
      ]));
    });
  }

  // --- Payouts -----------------------------------------------------------------------

  var payoutStatus = "due";

  function renderPayouts(data) {
    $("p-due").textContent = money(data.due_total);
    var body = $("payouts");
    body.replaceChildren();
    if (!data.results.length) body.appendChild(el("tr", {}, [el("td", { colspan: "8", class: "empty-cell", text: t("noStatements") })]));
    data.results.forEach(function (s, i) {
      var action;
      if (s.status === "paid") {
        action = el("span", { class: "muted small-text", dir: "auto", text: s.paid_reference || "" });
      } else {
        var reference = el("input", { type: "text", class: "ref-input", placeholder: t("reference"), "aria-label": t("reference") });
        var pay = el("button", { type: "button", class: "small primary-small", text: t("markPaid") });
        pay.addEventListener("click", function () {
          pay.disabled = true;
          api("payouts/" + s.id + "/paid/", { reference: reference.value.trim() }).then(refresh, function () { pay.disabled = false; });
        });
        action = el("div", { class: "pay-row" }, [reference, pay]);
      }
      body.appendChild(el("tr", { style: "--i:" + Math.min(i, 12) }, [
        el("td", {}, [el("strong", { text: s.store_name })]),
        el("td", { class: "num", dir: "ltr", text: s.period_start + " → " + s.period_end }),
        el("td", { class: "num", text: number(s.orders_count) }),
        el("td", { class: "num", text: money(s.food_sales) }),
        el("td", { class: "num", text: money(s.commission) }),
        el("td", { class: "num" }, [el("strong", { text: money(s.payout) })]),
        el("td", {}, [el("span", { class: "chip " + (s.status === "paid" ? "on" : "warn"), text: t(s.status) })]),
        el("td", {}, [action]),
      ]));
    });
  }

  document.querySelectorAll("#payout-filter button").forEach(function (button) {
    button.addEventListener("click", function () {
      payoutStatus = button.dataset.status;
      document.querySelectorAll("#payout-filter button").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b === button));
      });
      refresh();
    });
  });
  $("close-weeks").addEventListener("click", function () {
    var button = $("close-weeks");
    button.disabled = true;
    api("payouts/close/", {}).then(refresh).finally(function () { button.disabled = false; });
  });

  // --- Accounts ---------------------------------------------------------------------

  function renderUsers(data) {
    var chips = $("roles");
    chips.replaceChildren();
    var all = Object.keys(data.counts).reduce(function (sum, key) { return sum + data.counts[key]; }, 0);
    [["", t("all"), all]].concat(Object.keys(data.counts).map(function (key) {
      return [key, t("role_" + key), data.counts[key]];
    })).forEach(function (option) {
      var chip = el("button", { type: "button", "aria-pressed": String(role === option[0]) }, [
        option[1], el("span", { class: "chip-count", text: number(option[2]) }),
      ]);
      chip.addEventListener("click", function () { role = option[0]; refresh(); });
      chips.appendChild(chip);
    });

    var body = $("users");
    body.replaceChildren();
    data.results.forEach(function (user, i) {
      body.appendChild(el("tr", { class: user.is_active ? "" : "inactive", style: "--i:" + Math.min(i, 12) }, [
        el("td", { dir: "ltr", class: "phone", text: user.phone }),
        el("td", { dir: "auto", text: user.name || "—" }),
        el("td", {}, [el("span", { class: "chip role-" + user.role, text: user.is_staff ? t("staff") : t("role_" + user.role) })]),
        el("td", { class: "num", text: number(user.orders) }),
        el("td", { class: "num", text: new Date(user.joined).toLocaleDateString(lang === "en" ? "en-GB" : "ar-IQ") }),
        el("td", {}, [user.is_staff ? el("span", { class: "muted", text: "—" }) : toggle(user.is_active, user.phone, function (on, input) {
          input.disabled = true;
          api("users/" + user.id + "/active/", { is_active: on }).then(refresh, function () { input.checked = !on; })
            .finally(function () { input.disabled = false; });
        })]),
        el("td", {}, [editLink("/admin/accounts/user/" + user.id + "/change/")]),
      ]));
    });
  }

  // --- Loop ------------------------------------------------------------------------

  var timer = null;

  function refresh() {
    clearTimeout(timer);
    var loads = [api("overview/").then(renderOverview)];
    if (view === "overview") loads.push(api("alerts/").then(renderAlerts));
    if (view === "orders") loads.push(api("orders/").then(renderOrders));
    if (view === "captains") { ensureMap(); loads.push(api("captains/").then(renderCaptains)); }
    if (view === "stores") loads.push(api("stores/").then(renderStores));
    if (view === "payouts") loads.push(api("payouts/" + (payoutStatus ? "?status=" + payoutStatus : "")).then(renderPayouts));
    if (view === "users") {
      var params = new URLSearchParams();
      if (role) params.set("role", role);
      if (query) params.set("q", query);
      loads.push(api("users/?" + params.toString()).then(renderUsers));
    }
    return Promise.all(loads)
      .then(function () { $("offline").hidden = true; })
      .catch(function (error) {
        if (error.message === "signed out") return;
        $("offline").textContent = t("connection");
        $("offline").hidden = false;
      })
      .finally(function () {
        if (!document.hidden) timer = setTimeout(refresh, REFRESH_MS);
      });
  }

  function show(name, quiet) {
    view = name;
    document.querySelectorAll(".tabs button").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.dataset.view === name));
    });
    document.querySelectorAll(".view").forEach(function (section) {
      section.hidden = section.id !== "view-" + name;
    });
    write("wasel_ops_view", name);
    if (!quiet) refresh();
    if (name === "captains" && map) setTimeout(function () { map.resize(); }, 0);
  }

  function applyLanguage(code) {
    lang = code;
    write("wasel_lang", code);
    document.documentElement.lang = code;
    document.documentElement.dir = code === "en" ? "ltr" : "rtl";
    document.title = (code === "en" ? "Wasel | " : "واصل | ") + t("tag");
    document.querySelectorAll("[data-i18n]").forEach(function (node) { node.textContent = t(node.dataset.i18n); });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (node) { node.placeholder = t(node.dataset.i18nPlaceholder); });
    document.querySelectorAll("[data-lang]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.dataset.lang === code));
    });
    refresh();
  }

  document.querySelectorAll(".tabs button").forEach(function (button) {
    button.addEventListener("click", function () { show(button.dataset.view); });
  });
  document.querySelectorAll("[data-lang]").forEach(function (button) {
    button.addEventListener("click", function () { applyLanguage(button.dataset.lang); });
  });
  var searchTimer = null;
  $("search").addEventListener("input", function (event) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { query = event.target.value.trim(); refresh(); }, 250);
  });
  document.addEventListener("visibilitychange", function () { if (!document.hidden) refresh(); });

  var saved = read("wasel_ops_view");
  if (saved && $("view-" + saved)) show(saved, true);
  applyLanguage(lang); // renders text and loads the data
})();
