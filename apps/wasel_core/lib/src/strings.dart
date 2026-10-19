import 'package:flutter/widgets.dart';
import 'package:provider/provider.dart';

import 'countries.dart';
import 'session.dart';

/// App text in Arabic, Kurdish (Sorani) and English.
///
/// Shared words (login, errors, order statuses) live here; each app adds its
/// own with [S.addStrings] at startup. Kurdish strings should be reviewed by a
/// native speaker before launch.
class S {
  S(this.lang);
  final String lang;

  static S of(BuildContext context) => S(context.watch<BaseSession>().lang);
  static S read(BuildContext context) => S(context.read<BaseSession>().lang);

  static final Map<String, Map<String, String>> _app = {};

  /// Adds (or overrides) strings for an app, keyed by language.
  static void addStrings(Map<String, Map<String, String>> strings) {
    strings.forEach((lang, values) => (_app[lang] ??= {}).addAll(values));
  }

  String t(String key, [Map<String, Object> vars = const {}]) {
    var text =
        _app[lang]?[key] ??
        _core[lang]?[key] ??
        _app['en']?[key] ??
        _core['en']![key] ??
        key;
    vars.forEach((name, value) => text = text.replaceAll('{$name}', '$value'));
    return text;
  }

  /// An amount in its currency, with that currency's decimals and
  /// thousands separators: "18,000 د.ع", "12.50 SAR", "3.150 د.ك".
  String money(num amount, [String currency = 'IQD']) {
    final decimals = currencyDecimals(currency);
    final fixed = amount.abs().toStringAsFixed(decimals);
    final whole = fixed.split('.').first;
    final buffer = StringBuffer();
    for (var i = 0; i < whole.length; i++) {
      if (i > 0 && (whole.length - i) % 3 == 0) buffer.write(',');
      buffer.write(whole[i]);
    }
    if (decimals > 0) buffer.write('.${fixed.split('.').last}');
    final sign = amount < 0 ? '-' : '';
    final symbol = lang == 'en'
        ? currency
        : (currencySymbols[currency] ?? currency);
    return '$sign$buffer $symbol';
  }

  /// Arabic-script symbols, used in Arabic and Kurdish.
  static const currencySymbols = {
    'IQD': 'د.ع',
    'SAR': 'ر.س',
    'AED': 'د.إ',
    'QAR': 'ر.ق',
    'KWD': 'د.ك',
    'BHD': 'د.ب',
    'OMR': 'ر.ع',
  };

  static const _core = <String, Map<String, String>>{
    'ar': {
      'err_not_allowed': 'لا يمكن لهذا الحساب استخدام هذا التطبيق.',
      'currency': 'د.ع',
      'brandLine': 'اطلب من مطاعمك وأسواقك المفضلة، ويوصلك الطلب لباب البيت.',
      'loginTitle': 'سجّل دخولك',
      'loginLead': 'أدخل رقم هاتفك وسنرسل لك رمز الدخول.',
      'phone': 'رقم الهاتف',
      'phoneHelp': 'اختر الدولة ثم اكتب رقمك',
      'phoneCountry': 'دولة الرقم',
      'searchCountries': 'ابحث عن دولة',
      'allCountries': 'كل الدول',
      'err_wallet_currency_mismatch': 'محفظتك بعملة أخرى. اختر الدفع نقداً.',
      'sendBy': 'أرسل الرمز عبر',
      'whatsapp': 'واتساب',
      'sms': 'رسالة نصية',
      'sendCode': 'أرسل الرمز',
      'codeTitle': 'أدخل الرمز',
      'codeLead': 'أرسلنا رمزاً من 6 أرقام إلى {phone} عبر {channel}.',
      'code': 'رمز الدخول',
      'confirm': 'تأكيد',
      'resendIn': 'يمكنك إعادة الإرسال بعد {s} ثانية',
      'resend': 'إعادة إرسال الرمز',
      'changeNumber': 'تغيير الرقم',
      'language': 'اللغة',
      'logout': 'تسجيل الخروج',
      'km': '{km} كم',
      'retry': 'إعادة المحاولة',
      'cancel': 'إلغاء',
      'status_received': 'وصل طلبك للمطعم',
      'status_preparing': 'يتم تحضير طلبك',
      'status_ready': 'طلبك جاهز',
      'status_out_for_delivery': 'الكابتن في الطريق إليك',
      'status_delivered': 'تم التوصيل. بالعافية!',
      'status_cancelled': 'تم إلغاء الطلب',
      'step_received': 'استلام',
      'step_preparing': 'تحضير',
      'step_ready': 'جاهز',
      'step_out_for_delivery': 'بالطريق',
      'step_delivered': 'توصيل',
      'pin': 'رمز التسليم',
      'orderNumber': 'طلب #{id}',
      'err_invalid_phone': 'رقم الهاتف غير صحيح. تأكد من الدولة والرقم.',
      'err_invalid_code': 'الرمز غير صحيح أو انتهت صلاحيته.',
      'err_too_soon': 'انتظر قليلاً قبل طلب رمز جديد.',
      'err_too_many_requests': 'طلبات كثيرة لهذا الرقم. حاول بعد ساعة.',
      'err_delivery_failed': 'تعذّر إرسال الرمز الآن. حاول مرة أخرى بعد قليل.',
      'err_account_disabled': 'هذا الحساب موقوف. تواصل مع الدعم.',
      'err_vendor_closed': 'المتجر مغلق الآن.',
      'err_out_of_delivery_area': 'المتجر لا يوصل إلى موقعك.',
      'err_product_unavailable': 'أحد المنتجات نفذت كميته.',
      'err_insufficient_wallet_balance': 'رصيد محفظتك لا يكفي لهذا الطلب.',
      'err_network': 'تعذّر الاتصال. تحقق من الإنترنت وحاول مرة أخرى.',
      'err_generic': 'حدث خطأ. حاول مرة أخرى.',
    },
    'ku': {
      'err_not_allowed': 'ئەم هەژمارە ناتوانێت ئەم ئەپە بەکاربهێنێت.',
      'currency': 'د.ع',
      'brandLine':
          'لە چێشتخانە و بازاڕە دڵخوازەکانت داوا بکە، تا بەردەم ماڵەکەت دەگات.',
      'loginTitle': 'چوونەژوورەوە',
      'loginLead': 'ژمارەی مۆبایلەکەت بنووسە و کۆدی چوونەژوورەوەت بۆ دەنێرین.',
      'phone': 'ژمارەی مۆبایل',
      'phoneHelp': 'وڵات هەڵبژێرە و ژمارەکەت بنووسە',
      'phoneCountry': 'وڵاتی ژمارەکە',
      'searchCountries': 'گەڕان بۆ وڵات',
      'allCountries': 'هەموو وڵاتەکان',
      'err_wallet_currency_mismatch':
          'جزدانەکەت بە دراوێکی ترە. پارەدانی کاش هەڵبژێرە.',
      'sendBy': 'کۆدەکە بنێرە لە ڕێگەی',
      'whatsapp': 'واتساپ',
      'sms': 'نامەی دەقی',
      'sendCode': 'کۆدەکە بنێرە',
      'codeTitle': 'کۆدەکە بنووسە',
      'codeLead': 'کۆدێکی 6 ژمارەییمان نارد بۆ {phone} لە ڕێگەی {channel}.',
      'code': 'کۆدی چوونەژوورەوە',
      'confirm': 'پشتڕاستکردنەوە',
      'resendIn': 'دوای {s} چرکە دەتوانیت دووبارە بینێریتەوە',
      'resend': 'دووبارە ناردنەوەی کۆد',
      'changeNumber': 'گۆڕینی ژمارە',
      'language': 'زمان',
      'logout': 'چوونەدەرەوە',
      'km': '{km} کم',
      'retry': 'دووبارە هەوڵ بدەرەوە',
      'cancel': 'هەڵوەشاندنەوە',
      'status_received': 'داواکارییەکەت گەیشتە دووکان',
      'status_preparing': 'داواکارییەکەت ئامادە دەکرێت',
      'status_ready': 'داواکارییەکەت ئامادەیە',
      'status_out_for_delivery': 'کاپتن لە ڕێگایە بۆ لات',
      'status_delivered': 'گەیەندرا. نۆشی گیان!',
      'status_cancelled': 'داواکارییەکە هەڵوەشێنرایەوە',
      'step_received': 'وەرگرتن',
      'step_preparing': 'ئامادەکردن',
      'step_ready': 'ئامادە',
      'step_out_for_delivery': 'لە ڕێگا',
      'step_delivered': 'گەیاندن',
      'pin': 'کۆدی وەرگرتن',
      'orderNumber': 'داواکاری #{id}',
      'err_invalid_phone': 'ژمارەکە هەڵەیە. وڵات و ژمارەکە بپشکنە.',
      'err_invalid_code': 'کۆدەکە هەڵەیە یان بەسەرچووە.',
      'err_too_soon': 'کەمێک چاوەڕێ بکە پێش داواکردنی کۆدێکی نوێ.',
      'err_too_many_requests':
          'داواکاری زۆر بۆ ئەم ژمارەیە. دوای کاتژمێرێک هەوڵ بدەرەوە.',
      'err_delivery_failed':
          'ئێستا ناتوانین کۆدەکە بنێرین. کەمێکی تر هەوڵ بدەرەوە.',
      'err_account_disabled':
          'ئەم هەژمارە ڕاگیراوە. پەیوەندی بە پشتگیرییەوە بکە.',
      'err_vendor_closed': 'دووکانەکە ئێستا داخراوە.',
      'err_out_of_delivery_area': 'دووکانەکە بۆ شوێنەکەت ناگەیەنێت.',
      'err_product_unavailable': 'یەکێک لە بەرهەمەکان نەماوە.',
      'err_insufficient_wallet_balance':
          'باڵانسی جزدانەکەت بەس نییە بۆ ئەم داواکارییە.',
      'err_network':
          'پەیوەندی نەکرا. ئینتەرنێتەکەت بپشکنە و دووبارە هەوڵ بدەرەوە.',
      'err_generic': 'هەڵەیەک ڕوویدا. دووبارە هەوڵ بدەرەوە.',
    },
    'en': {
      'err_not_allowed': "This account can't use this app.",
      'currency': 'IQD',
      'brandLine': 'Order from your favourite restaurants and markets, delivered to your door.',
      'loginTitle': 'Log in',
      'loginLead': "Enter your phone number and we'll send you a login code.",
      'phone': 'Phone number',
      'phoneHelp': 'Pick the country, then type your number',
      'phoneCountry': 'Phone country',
      'searchCountries': 'Search countries',
      'allCountries': 'All countries',
      'err_wallet_currency_mismatch':
          'Your wallet is in another currency. Pay cash instead.',
      'sendBy': 'Send the code by',
      'whatsapp': 'WhatsApp',
      'sms': 'Text message',
      'sendCode': 'Send code',
      'codeTitle': 'Enter the code',
      'codeLead': 'We sent a 6-digit code to {phone} by {channel}.',
      'code': 'Login code',
      'confirm': 'Confirm',
      'resendIn': 'You can resend in {s}s',
      'resend': 'Resend code',
      'changeNumber': 'Change number',
      'language': 'Language',
      'logout': 'Log out',
      'km': '{km} km',
      'retry': 'Try again',
      'cancel': 'Cancel',
      'status_received': 'The store has your order',
      'status_preparing': 'Your order is being prepared',
      'status_ready': 'Your order is ready',
      'status_out_for_delivery': 'Your captain is on the way',
      'status_delivered': 'Delivered. Enjoy!',
      'status_cancelled': 'This order was cancelled',
      'step_received': 'Received',
      'step_preparing': 'Preparing',
      'step_ready': 'Ready',
      'step_out_for_delivery': 'On the way',
      'step_delivered': 'Delivered',
      'pin': 'Delivery PIN',
      'orderNumber': 'Order #{id}',
      'err_invalid_phone':
          "That number isn't valid. Check the country and the number.",
      'err_invalid_code': 'The code is wrong or has expired.',
      'err_too_soon': 'Wait a moment before asking for a new code.',
      'err_too_many_requests':
          'Too many codes for this number. Try again in an hour.',
      'err_delivery_failed':
          "We couldn't send the code right now. Try again shortly.",
      'err_account_disabled': 'This account is disabled. Contact support.',
      'err_vendor_closed': 'This store is closed right now.',
      'err_out_of_delivery_area':
          "This store doesn't deliver to your location.",
      'err_product_unavailable': 'Something in your cart is out of stock.',
      'err_insufficient_wallet_balance':
          'Your wallet balance is too low for this order.',
      'err_network': "Couldn't connect. Check your internet and try again.",
      'err_generic': 'Something went wrong. Try again.',
    },
  };
}
