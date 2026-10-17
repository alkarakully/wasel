(function () {
  "use strict";

  var ORDER_ID = window.WASEL_ORDER_ID;
  var STEPS = ["received", "preparing", "ready", "out_for_delivery", "delivered"];

  var STRINGS = {
    ar: {
      dir: "rtl",
      pageTitle: "واصل | تتبع الطلب",
      order: "طلب #{id}",
      steps: ["استلام", "تحضير", "جاهز", "بالطريق", "توصيل"],
      status: {
        received: "وصل طلبك للمطعم",
        preparing: "يتم تحضير طلبك",
        ready: "طلبك جاهز",
        out_for_delivery: "الكابتن في الطريق إليك",
        delivered: "تم التوصيل. بالعافية!",
        cancelled: "تم إلغاء الطلب"
      },
      pinLabel: "رمز التسليم",
      pinHelp: "أعطِ هذا الرمز للكابتن عند الباب.",
      captainWaiting: "بانتظار كابتن",
      captainNoGps: "تم تعيين كابتن. الموقع غير متاح بعد.",
      captainSeconds: "موقع الكابتن محدّث قبل {n} ثانية",
      captainMinutes: "موقع الكابتن محدّث قبل {n} دقيقة",
      needLogin: "سجّل دخولك لمتابعة طلبك.",
      login: "تسجيل الدخول",
      notFound: "لم نجد هذا الطلب.",
      offline: "انقطع الاتصال. نعيد المحاولة..."
    },
    ku: {
      dir: "rtl",
      pageTitle: "واصل | بەدواداچوونی داواکاری",
      order: "داواکاری #{id}",
      steps: ["وەرگرتن", "ئامادەکردن", "ئامادە", "لە ڕێگا", "گەیاندن"],
      status: {
        received: "داواکارییەکەت گەیشتە دووکان",
        preparing: "داواکارییەکەت ئامادە دەکرێت",
        ready: "داواکارییەکەت ئامادەیە",
        out_for_delivery: "کاپتن لە ڕێگایە بۆ لات",
        delivered: "گەیەندرا. نۆشی گیان!",
        cancelled: "داواکارییەکە هەڵوەشێنرایەوە"
      },
      pinLabel: "کۆدی وەرگرتن",
      pinHelp: "ئەم کۆدە بدە بە کاپتن لە بەردەم دەرگا.",
      captainWaiting: "چاوەڕێی کاپتن",
      captainNoGps: "کاپتن دیاریکرا. شوێنەکەی هێشتا بەردەست نییە.",
      captainSeconds: "شوێنی کاپتن پێش {n} چرکە نوێکرایەوە",
      captainMinutes: "شوێنی کاپتن پێش {n} خولەک نوێکرایەوە",
      needLogin: "بچۆ ژوورەوە بۆ بەدواداچوونی داواکارییەکەت.",
      login: "چوونەژوورەوە",
      notFound: "ئەم داواکارییە نەدۆزرایەوە.",
      offline: "پەیوەندی پچڕا. هەوڵ دەدەینەوە..."
    },
    en: {
      dir: "ltr",
      pageTitle: "Wasel | Track order",
      order: "Order #{id}",
      steps: ["Received", "Preparing", "Ready", "On the way", "Delivered"],
      status: {
        received: "The store has your order",
        preparing: "Your order is being prepared",
        ready: "Your order is ready",
        out_for_delivery: "Your captain is on the way",
        delivered: "Delivered. Enjoy!",
        cancelled: "This order was cancelled"
      },
      pinLabel: "Delivery PIN",
      pinHelp: "Give this PIN to the captain at the door.",
      captainWaiting: "Waiting for a captain",
      captainNoGps: "Captain assigned. Location not shared yet.",
      captainSeconds: "Captain's location updated {n}s ago",
      captainMinutes: "Captain's location updated {n} min ago",
      needLogin: "Log in to follow your order.",
      login: "Log in",
      notFound: "We couldn't find this order.",
      offline: "Connection lost. Reconnecting..."
    }
  };

  function storage(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }

  var $ = function (id) { return document.getElementById(id); };
  var lang = STRINGS[storage("wasel_lang")] ? storage("wasel_lang") : "ar";
  var S = STRINGS[lang];
  document.documentElement.lang = lang === "ku" ? "ckb" : lang;
  document.documentElement.dir = S.dir;
  document.title = S.pageTitle;

  var token = storage("wasel_token");
  var state = { order: null, captainAt: null, socket: null, retry: 0 };

  // --- Map -------------------------------------------------------------------

  var styles = JSON.parse($("map-styles").textContent);
  var dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Shapes Arabic and Kurdish street names correctly.
  maplibregl.setRTLTextPlugin("https://unpkg.com/@mapbox/mapbox-gl-rtl-text@0.2.3/mapbox-gl-rtl-text.min.js", true);

  var map = new maplibregl.Map({
    container: "map",
    style: dark ? styles.dark : styles.light,
    center: [44.3661, 33.3152], // Baghdad
    zoom: 11,
    attributionControl: { compact: true }
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), S.dir === "rtl" ? "top-left" : "top-right");

  function markerElement(iconName, isCaptain) {
    var el = document.createElement("span");
    el.className = "marker" + (isCaptain ? " captain" : "");
    var i = document.createElement("i");
    i.className = "ph ph-" + iconName;
    el.appendChild(i);
    return el;
  }

  var markers = { vendor: null, home: null, captain: null };
  var fitted = false;

  function placeMarker(key, point, iconName, isCaptain) {
    if (!point) return;
    var lngLat = [point.lng, point.lat];
    if (markers[key]) markers[key].setLngLat(lngLat);
    else markers[key] = new maplibregl.Marker({ element: markerElement(iconName, isCaptain) }).setLngLat(lngLat).addTo(map);
  }

  function panelPadding() {
    // Keep markers clear of the panel: beside it on desktop, above it on phones.
    var panel = document.querySelector(".panel").getBoundingClientRect();
    var pad = { top: 60, bottom: 60, left: 60, right: 60 };
    if (window.innerWidth < 768) pad.bottom += panel.height;
    else if (S.dir === "rtl") pad.right += panel.width + 24;
    else pad.left += panel.width + 24;
    return pad;
  }

  function fitAll() {
    var keys = Object.keys(markers).filter(function (k) { return markers[k]; });
    if (!keys.length) return;
    var bounds = new maplibregl.LngLatBounds();
    keys.forEach(function (k) { bounds.extend(markers[k].getLngLat()); });
    map.fitBounds(bounds, { padding: panelPadding(), maxZoom: 16, animate: fitted && !reduceMotion });
  }

  var glide = null;

  // Glide the captain between GPS fixes instead of jumping.
  function glideCaptain(to) {
    var marker = markers.captain;
    var from = marker.getLngLat();
    if (reduceMotion) { marker.setLngLat(to); return; }
    if (glide) cancelAnimationFrame(glide);
    var start = performance.now();
    var duration = 1800;
    function frame(now) {
      var t = Math.min(1, (now - start) / duration);
      marker.setLngLat([from.lng + (to[0] - from.lng) * t, from.lat + (to[1] - from.lat) * t]);
      if (t < 1) glide = requestAnimationFrame(frame);
    }
    glide = requestAnimationFrame(frame);
  }

  function moveCaptain(location) {
    if (!location) return;
    state.captainAt = new Date(location.updated_at);
    if (!markers.captain) {
      placeMarker("captain", location, "moped", true);
      fitAll();
    } else {
      glideCaptain([location.lng, location.lat]);
      if (!map.getBounds().contains([location.lng, location.lat])) map.panTo([location.lng, location.lat]);
    }
    renderCaptainLine();
  }

  function removeCaptain() {
    if (markers.captain) { markers.captain.remove(); markers.captain = null; }
  }

  // --- Panel -----------------------------------------------------------------

  function show(which) {
    $("state-loading").hidden = which !== "loading";
    $("state-message").hidden = which !== "message";
    $("state-order").hidden = which !== "order";
  }

  function message(text, linkText) {
    $("message-text").textContent = text;
    $("message-link").hidden = !linkText;
    if (linkText) $("message-link").textContent = linkText;
    show("message");
  }

  function renderSteps(status) {
    var list = $("steps");
    list.textContent = "";
    var current = STEPS.indexOf(status);
    STEPS.forEach(function (step, i) {
      var li = document.createElement("li");
      li.textContent = S.steps[i];
      if (current >= 0 && i < current) li.className = "done";
      if (i === current) {
        li.className = "current";
        li.setAttribute("aria-current", "step");
      }
      list.appendChild(li);
    });
  }

  function renderCaptainLine() {
    var order = state.order;
    if (!order) return;
    var active = ["preparing", "ready", "out_for_delivery"].indexOf(order.status) >= 0;
    $("captain-line").hidden = !active;
    if (!active) return;
    var text;
    if (!order.captain) text = S.captainWaiting;
    else if (!state.captainAt) text = S.captainNoGps;
    else {
      var seconds = Math.max(0, Math.round((Date.now() - state.captainAt.getTime()) / 1000));
      text = seconds < 60 ? S.captainSeconds.replace("{n}", seconds) : S.captainMinutes.replace("{n}", Math.round(seconds / 60));
    }
    $("captain-text").textContent = text;
  }

  function render(order) {
    state.order = order;
    $("vendor-name").textContent = order.vendor_name;
    $("order-number").textContent = S.order.replace("{id}", order.id);
    $("status-title").textContent = S.status[order.status] || order.status;
    $("state-order").classList.toggle("cancelled", order.status === "cancelled");
    renderSteps(order.status);

    var showPin = order.delivery_pin && ["delivered", "cancelled"].indexOf(order.status) < 0;
    $("pin-box").hidden = !showPin;
    if (showPin) {
      $("pin-label").textContent = S.pinLabel;
      $("pin-help").textContent = S.pinHelp;
      $("pin-code").textContent = order.delivery_pin;
    }

    // Show the card first so the map can measure it when fitting markers.
    show("order");
    placeMarker("vendor", order.vendor_location, "storefront");
    placeMarker("home", order.delivery_location, "house-line");
    if (order.captain_location) moveCaptain(order.captain_location);
    if (["delivered", "cancelled"].indexOf(order.status) >= 0) { removeCaptain(); state.captainAt = null; }
    if (!fitted) { fitAll(); fitted = true; }

    renderCaptainLine();
  }

  setInterval(renderCaptainLine, 1000);

  // --- Data ------------------------------------------------------------------

  function connect() {
    var scheme = location.protocol === "https:" ? "wss" : "ws";
    var socket = new WebSocket(scheme + "://" + location.host + "/ws/orders/?token=" + encodeURIComponent(token));
    state.socket = socket;

    socket.onopen = function () {
      state.retry = 0;
      $("offline").hidden = true;
    };
    socket.onmessage = function (event) {
      var data = JSON.parse(event.data);
      if (data.type === "order.updated" && data.order.id === ORDER_ID) render(data.order);
      if (data.type === "captain.location" && data.order_id === ORDER_ID) moveCaptain(data.location);
    };
    socket.onclose = function (event) {
      if (event.code === 4401) { message(S.needLogin, S.login); return; }
      $("offline").textContent = S.offline;
      $("offline").hidden = false;
      // Back off up to 30s, then catch up on anything missed.
      var wait = Math.min(30000, 1000 * Math.pow(2, state.retry++));
      setTimeout(function () { load().then(function (ok) { if (ok) connect(); }); }, wait);
    };
  }

  setInterval(function () {
    if (state.socket && state.socket.readyState === 1) state.socket.send(JSON.stringify({ type: "ping" }));
  }, 25000);

  function load() {
    return fetch("/api/orders/" + ORDER_ID + "/", { headers: { Authorization: "Token " + token, Accept: "application/json" } })
      .then(function (response) {
        if (response.status === 401) { message(S.needLogin, S.login); return false; }
        if (response.status === 404) { message(S.notFound); return false; }
        return response.json().then(function (order) { render(order); return true; });
      })
      .catch(function () { return true; });
  }

  if (!token) {
    message(S.needLogin, S.login);
    return;
  }
  show("loading");
  load().then(function (ok) { if (ok) connect(); });
})();
