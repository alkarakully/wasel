(function () {
  "use strict";

  var STRINGS = {
    ar: {
      dir: "rtl",
      pageTitle: "واصل | تسجيل الدخول",
      brandLine: "اطلب من مطاعمك وأسواقك المفضلة، ويوصلك الطلب لباب البيت.",
      phoneTitle: "سجّل دخولك",
      phoneLead: "أدخل رقم هاتفك وسنرسل لك رمز الدخول.",
      phoneLabel: "رقم الهاتف",
      phoneHelp: "رقم عراقي يبدأ بـ 07",
      channelLabel: "أرسل الرمز عبر",
      whatsapp: "واتساب",
      sms: "رسالة نصية",
      sendCode: "أرسل الرمز",
      sending: "جارٍ الإرسال...",
      changeNumber: "تغيير الرقم",
      codeTitle: "أدخل الرمز",
      codeLead: "أرسلنا رمزاً من 6 أرقام إلى {phone} عبر {channel}.",
      codeLabel: "رمز الدخول",
      confirm: "تأكيد",
      checking: "جارٍ التحقق...",
      resend: "إعادة إرسال الرمز",
      resendIn: "يمكنك إعادة الإرسال بعد {s} ثانية",
      welcomeNew: "أهلاً بك في واصل",
      welcomeBack: "أهلاً بعودتك",
      logout: "تسجيل الخروج",
      errPhone: "رقم الهاتف غير صحيح. أدخل رقماً عراقياً يبدأ بـ 07.",
      errCodeFormat: "الرمز يتكون من 6 أرقام.",
      errCode: "الرمز غير صحيح أو انتهت صلاحيته.",
      errTooSoon: "انتظر {s} ثانية قبل طلب رمز جديد.",
      errTooMany: "طلبات كثيرة لهذا الرقم. حاول بعد ساعة.",
      errDelivery: "تعذّر إرسال الرمز الآن. حاول مرة أخرى بعد قليل.",
      errDisabled: "هذا الحساب موقوف. تواصل مع الدعم.",
      errNetwork: "تعذّر الاتصال. تحقق من الإنترنت وحاول مرة أخرى."
    },
    ku: {
      dir: "rtl",
      pageTitle: "واصل | چوونەژوورەوە",
      brandLine: "لە چێشتخانە و بازاڕە دڵخوازەکانت داوا بکە، تا بەردەم ماڵەکەت دەگات.",
      phoneTitle: "چوونەژوورەوە",
      phoneLead: "ژمارەی مۆبایلەکەت بنووسە و کۆدی چوونەژوورەوەت بۆ دەنێرین.",
      phoneLabel: "ژمارەی مۆبایل",
      phoneHelp: "ژمارەیەکی عێراقی کە بە 07 دەست پێدەکات",
      channelLabel: "کۆدەکە بنێرە لە ڕێگەی",
      whatsapp: "واتساپ",
      sms: "نامەی دەقی",
      sendCode: "کۆدەکە بنێرە",
      sending: "دەنێردرێت...",
      changeNumber: "گۆڕینی ژمارە",
      codeTitle: "کۆدەکە بنووسە",
      codeLead: "کۆدێکی 6 ژمارەییمان نارد بۆ {phone} لە ڕێگەی {channel}.",
      codeLabel: "کۆدی چوونەژوورەوە",
      confirm: "پشتڕاستکردنەوە",
      checking: "پشکنین...",
      resend: "دووبارە ناردنەوەی کۆد",
      resendIn: "دوای {s} چرکە دەتوانیت دووبارە بینێریتەوە",
      welcomeNew: "بەخێربێیت بۆ واصل",
      welcomeBack: "بەخێربێیتەوە",
      logout: "چوونەدەرەوە",
      errPhone: "ژمارەکە هەڵەیە. ژمارەیەکی عێراقی بنووسە کە بە 07 دەست پێدەکات.",
      errCodeFormat: "کۆدەکە 6 ژمارەیە.",
      errCode: "کۆدەکە هەڵەیە یان بەسەرچووە.",
      errTooSoon: "{s} چرکە چاوەڕێ بکە پێش داواکردنی کۆدێکی نوێ.",
      errTooMany: "داواکاری زۆر بۆ ئەم ژمارەیە. دوای کاتژمێرێک هەوڵ بدەرەوە.",
      errDelivery: "ئێستا ناتوانین کۆدەکە بنێرین. کەمێکی تر هەوڵ بدەرەوە.",
      errDisabled: "ئەم هەژمارە ڕاگیراوە. پەیوەندی بە پشتگیرییەوە بکە.",
      errNetwork: "پەیوەندی نەکرا. ئینتەرنێتەکەت بپشکنە و دووبارە هەوڵ بدەرەوە."
    },
    en: {
      dir: "ltr",
      pageTitle: "Wasel | Log in",
      brandLine: "Order from your favourite restaurants and markets, delivered to your door.",
      phoneTitle: "Log in",
      phoneLead: "Enter your phone number and we'll send you a login code.",
      phoneLabel: "Phone number",
      phoneHelp: "An Iraqi number starting with 07",
      channelLabel: "Send the code by",
      whatsapp: "WhatsApp",
      sms: "Text message",
      sendCode: "Send code",
      sending: "Sending...",
      changeNumber: "Change number",
      codeTitle: "Enter the code",
      codeLead: "We sent a 6-digit code to {phone} by {channel}.",
      codeLabel: "Login code",
      confirm: "Confirm",
      checking: "Checking...",
      resend: "Resend code",
      resendIn: "You can resend in {s}s",
      welcomeNew: "Welcome to Wasel",
      welcomeBack: "Welcome back",
      logout: "Log out",
      errPhone: "That number isn't valid. Enter an Iraqi number starting with 07.",
      errCodeFormat: "The code is 6 digits.",
      errCode: "The code is wrong or has expired.",
      errTooSoon: "Wait {s}s before asking for a new code.",
      errTooMany: "Too many codes for this number. Try again in an hour.",
      errDelivery: "We couldn't send the code right now. Try again shortly.",
      errDisabled: "This account is disabled. Contact support.",
      errNetwork: "Couldn't connect. Check your internet and try again."
    }
  };

  var TOKEN_KEY = "wasel_token";
  var LANG_KEY = "wasel_lang";

  var state = { lang: "ar", phone: null, channel: "whatsapp", resendAt: 0, timer: null, user: null, isNew: false };

  var $ = function (id) { return document.getElementById(id); };
  var steps = { phone: $("step-phone"), code: $("step-code"), done: $("step-done") };

  function storage(action, key, value) {
    try {
      if (action === "get") return window.localStorage.getItem(key);
      if (action === "set") window.localStorage.setItem(key, value);
      if (action === "remove") window.localStorage.removeItem(key);
    } catch (e) { /* private mode or blocked storage */ }
    return null;
  }

  function t(key, vars) {
    var text = STRINGS[state.lang][key] || STRINGS.en[key] || key;
    Object.keys(vars || {}).forEach(function (name) { text = text.replace("{" + name + "}", vars[name]); });
    return text;
  }

  function formatPhone(e164) {
    // +9647701234567 -> +964 770 123 4567
    var local = e164.replace(/^\+964/, "");
    return "+964 " + local.slice(0, 3) + " " + local.slice(3, 6) + " " + local.slice(6);
  }

  function applyLanguage(lang) {
    state.lang = STRINGS[lang] ? lang : "ar";
    document.documentElement.lang = state.lang === "ku" ? "ckb" : state.lang;
    document.documentElement.dir = STRINGS[state.lang].dir;
    document.title = t("pageTitle");
    document.querySelectorAll("[data-i18n]").forEach(function (el) { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-lang]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang));
    });
    renderDynamicText();
    storage("set", LANG_KEY, state.lang);
  }

  function renderDynamicText() {
    if (state.phone) {
      var lead = $("code-lead");
      lead.textContent = "";
      var parts = t("codeLead", { channel: t(state.channel) }).split("{phone}");
      lead.append(parts[0]);
      var bdi = document.createElement("bdi");
      bdi.dir = "ltr";
      bdi.textContent = formatPhone(state.phone);
      lead.append(bdi, parts[1] || "");
    }
    if (state.user) {
      $("done-title").textContent = t(state.isNew ? "welcomeNew" : "welcomeBack");
      $("done-phone").textContent = formatPhone(state.user.phone);
    }
    updateResend();
  }

  function show(name) {
    Object.keys(steps).forEach(function (key) { steps[key].hidden = key !== name; });
    var focusTarget = { phone: "phone", code: "code", done: "logout" }[name];
    $(focusTarget).focus();
  }

  function setError(field, message) {
    var input = $(field);
    var error = $(field + "-error");
    error.textContent = message || "";
    error.hidden = !message;
    input.setAttribute("aria-invalid", message ? "true" : "false");
  }

  function busy(button, labelKey) {
    // The label is a child span when the button also holds an icon.
    var label = button.querySelector("[data-i18n]") || button;
    var idle = label.dataset.i18n;
    button.disabled = true;
    label.textContent = t(labelKey);
    return function () {
      button.disabled = false;
      label.textContent = t(idle);
    };
  }

  function api(path, options) {
    options = options || {};
    var headers = { "Content-Type": "application/json", Accept: "application/json" };
    var token = storage("get", TOKEN_KEY);
    if (options.auth && token) headers.Authorization = "Token " + token;
    return fetch("/api/auth/" + path, {
      method: options.method || "GET",
      headers: headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      credentials: "omit"
    }).then(function (response) {
      if (response.status === 204) return { ok: true, status: 204, data: {} };
      return response.json().catch(function () { return {}; }).then(function (data) {
        return { ok: response.ok, status: response.status, data: data };
      });
    });
  }

  function errorMessage(result) {
    var data = result.data || {};
    switch (data.error) {
      case "too_soon": return t("errTooSoon", { s: data.retry_after });
      case "too_many_requests": return t("errTooMany");
      case "delivery_failed": return t("errDelivery");
      case "account_disabled": return t("errDisabled");
      case "invalid_code": return t("errCode");
    }
    if (data.phone) return t("errPhone");
    if (data.code) return t("errCodeFormat");
    if (result.status === 429) return t("errTooMany");
    return t("errNetwork");
  }

  // --- Resend countdown ----------------------------------------------------

  function updateResend() {
    var wait = Math.ceil((state.resendAt - Date.now()) / 1000);
    var label = $("resend-wait");
    var button = $("resend");
    if (wait > 0) {
      label.textContent = t("resendIn", { s: wait });
      button.hidden = true;
    } else {
      label.textContent = "";
      button.hidden = false;
      clearInterval(state.timer);
    }
  }

  function startResendTimer(seconds) {
    state.resendAt = Date.now() + seconds * 1000;
    clearInterval(state.timer);
    state.timer = setInterval(updateResend, 1000);
    updateResend();
  }

  // --- Actions -------------------------------------------------------------

  function requestCode(phone, channel, button, errorField) {
    var done = busy(button, "sending");
    return api("otp/request/", { method: "POST", body: { phone: phone, channel: channel } })
      .then(function (result) {
        if (!result.ok) {
          setError(errorField, errorMessage(result));
          if (result.data && result.data.retry_after) startResendTimer(result.data.retry_after);
          return false;
        }
        state.phone = result.data.phone;
        state.channel = result.data.channel;
        startResendTimer(result.data.resend_in);
        return true;
      })
      .catch(function () { setError(errorField, t("errNetwork")); return false; })
      .finally(done);
  }

  steps.phone.addEventListener("submit", function (event) {
    event.preventDefault();
    var phone = $("phone").value.trim();
    if (phone.replace(/\D/g, "").length < 10 && !/[٠-٩۰-۹]/.test(phone)) {
      setError("phone", t("errPhone"));
      return;
    }
    setError("phone", "");
    var channel = steps.phone.querySelector("input[name=channel]:checked").value;
    var button = steps.phone.querySelector("button[type=submit]");
    requestCode(phone, channel, button, "phone").then(function (sent) {
      if (!sent) return;
      $("code").value = "";
      setError("code", "");
      renderDynamicText();
      show("code");
    });
  });

  steps.code.addEventListener("submit", function (event) {
    event.preventDefault();
    var code = $("code").value.trim();
    if (!/^\d{6}$/.test(code)) {
      setError("code", t("errCodeFormat"));
      return;
    }
    // Typing the 6th digit submits, so a quick Enter must not send it twice.
    var button = steps.code.querySelector("button[type=submit]");
    if (button.disabled) return;
    setError("code", "");
    var done = busy(button, "checking");
    api("otp/verify/", { method: "POST", body: { phone: state.phone, code: code } })
      .then(function (result) {
        if (!result.ok) {
          setError("code", errorMessage(result));
          $("code").select();
          return;
        }
        storage("set", TOKEN_KEY, result.data.token);
        signedIn(result.data.user, result.data.is_new_user);
      })
      .catch(function () { setError("code", t("errNetwork")); })
      .finally(done);
  });

  // Submit as soon as 6 digits are typed or pasted. Converts Arabic-Indic
  // digits, and keeps the last 6 so pasting a whole message ("Your Wasel
  // code for +964...: 482913") still gives the code, not the phone number.
  $("code").addEventListener("input", function (event) {
    var input = event.target;
    var digits = input.value
      .replace(/[٠-٩]/g, function (d) { return String(d.charCodeAt(0) - 0x0660); })
      .replace(/[۰-۹]/g, function (d) { return String(d.charCodeAt(0) - 0x06f0); })
      .replace(/\D/g, "")
      .slice(-6);
    input.value = digits;
    if (digits.length === 6) steps.code.requestSubmit();
  });

  $("resend").addEventListener("click", function () {
    setError("code", "");
    requestCode(state.phone, state.channel, $("resend"), "code").then(function (sent) {
      if (sent) renderDynamicText();
      $("code").focus();
    });
  });

  $("change-number").addEventListener("click", function () {
    clearInterval(state.timer);
    show("phone");
  });

  $("logout").addEventListener("click", function () {
    var done = busy($("logout"), "logout");
    api("logout/", { method: "POST", auth: true }).finally(function () {
      storage("remove", TOKEN_KEY);
      state.user = null;
      state.phone = null;
      $("phone").value = "";
      done();
      show("phone");
    });
  });

  document.querySelectorAll("[data-lang]").forEach(function (button) {
    button.addEventListener("click", function () { applyLanguage(button.dataset.lang); });
  });

  function signedIn(user, isNew) {
    state.user = user;
    state.isNew = isNew;
    clearInterval(state.timer);
    renderDynamicText();
    show("done");
  }

  // --- Start ---------------------------------------------------------------

  applyLanguage(storage("get", LANG_KEY) || "ar");

  if (storage("get", TOKEN_KEY)) {
    api("me/", { auth: true })
      .then(function (result) {
        if (result.ok) signedIn(result.data, false);
        else storage("remove", TOKEN_KEY);
      })
      .catch(function () {});
  }
})();
