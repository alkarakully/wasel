import type { Lang, Names } from './api'

// Vendor portal text. Kurdish (Sorani) should be reviewed by a native speaker.
const strings = {
  ar: {
    brandLine: 'لوحة متاجر واصل. استقبل الطلبات وجهّزها.',
    portalTag: 'بوابة المتاجر',
    loginTitle: 'دخول المتجر',
    loginLead: 'أدخل رقم هاتف صاحب المتجر وسنرسل لك رمز الدخول.',
    phone: 'رقم الهاتف',
    phoneHelp: 'رقم عراقي يبدأ بـ 07',
    sendCode: 'أرسل الرمز',
    codeTitle: 'أدخل الرمز',
    codeLead: 'أرسلنا رمزاً من 6 أرقام إلى {phone}.',
    code: 'رمز الدخول',
    confirm: 'تأكيد',
    changeNumber: 'تغيير الرقم',
    orders: 'الطلبات',
    menu: 'القائمة',
    logout: 'تسجيل الخروج',
    storeOpen: 'المتجر مفتوح',
    storeClosed: 'المتجر مغلق',
    soundOn: 'الصوت يعمل',
    soundOff: 'شغّل صوت الطلبات',
    soundBlocked: 'اضغط هنا لتشغيل صوت تنبيه الطلبات الجديدة.',
    mute: 'إيقاف الرنين',
    col_received: 'طلبات جديدة',
    col_preparing: 'قيد التحضير',
    col_ready: 'جاهزة للاستلام',
    emptyColumn: 'لا شيء هنا',
    minutesAgo: 'قبل {n} د',
    justNow: 'الآن',
    readyIn: 'جاهز خلال {n} د',
    late: 'متأخر {n} د',
    accept: 'قبول',
    prepTime: 'وقت التحضير',
    reject: 'رفض',
    rejectTitle: 'رفض الطلب #{id}',
    rejectReason: 'سبب الرفض',
    reason_out_of_stock: 'نفذت بعض المواد',
    reason_busy: 'المطعم مزدحم جداً',
    reason_closing: 'سنغلق قريباً',
    otherReason: 'سبب آخر',
    cancel: 'إلغاء',
    confirmReject: 'رفض الطلب',
    markReady: 'جاهز',
    waitingCaptain: 'بانتظار كابتن',
    captainComing: 'الكابتن في الطريق للاستلام',
    cash: 'نقداً',
    paid: 'مدفوع',
    total: 'المجموع',
    min: 'د',
    available: 'متوفر',
    outOfStock: 'نفذت الكمية',
    noStores: 'لا يوجد متجر مرتبط بهذا الحساب.',
    currency: 'د.ع',
    err_invalid_phone: 'رقم الهاتف غير صحيح. أدخل رقماً عراقياً يبدأ بـ 07.',
    err_invalid_code: 'الرمز غير صحيح أو انتهت صلاحيته.',
    err_too_soon: 'انتظر قليلاً قبل طلب رمز جديد.',
    err_too_many_requests: 'طلبات كثيرة لهذا الرقم. حاول بعد ساعة.',
    err_not_vendor: 'هذا الرقم ليس حساب متجر. تواصل مع فريق واصل.',
    err_invalid_transition: 'تغيّرت حالة الطلب. تم تحديث اللوحة.',
    err_network: 'تعذّر الاتصال. تحقق من الإنترنت.',
    err_generic: 'حدث خطأ. حاول مرة أخرى.',
    offline: 'انقطع الاتصال. نعيد المحاولة...',
  },
  ku: {
    brandLine: 'پانێڵی دووکانەکانی واصل. داواکارییەکان وەربگرە و ئامادەیان بکە.',
    portalTag: 'پانێڵی دووکان',
    loginTitle: 'چوونەژوورەوەی دووکان',
    loginLead: 'ژمارەی مۆبایلی خاوەن دووکان بنووسە و کۆدی چوونەژوورەوەت بۆ دەنێرین.',
    phone: 'ژمارەی مۆبایل',
    phoneHelp: 'ژمارەیەکی عێراقی کە بە 07 دەست پێدەکات',
    sendCode: 'کۆدەکە بنێرە',
    codeTitle: 'کۆدەکە بنووسە',
    codeLead: 'کۆدێکی 6 ژمارەییمان نارد بۆ {phone}.',
    code: 'کۆدی چوونەژوورەوە',
    confirm: 'پشتڕاستکردنەوە',
    changeNumber: 'گۆڕینی ژمارە',
    orders: 'داواکارییەکان',
    menu: 'لیستی خواردن',
    logout: 'چوونەدەرەوە',
    storeOpen: 'دووکان کراوەیە',
    storeClosed: 'دووکان داخراوە',
    soundOn: 'دەنگ کار دەکات',
    soundOff: 'دەنگی داواکاری چالاک بکە',
    soundBlocked: 'لێرە دابگرە بۆ چالاککردنی دەنگی داواکارییە نوێیەکان.',
    mute: 'وەستاندنی زەنگ',
    col_received: 'داواکاری نوێ',
    col_preparing: 'لە ئامادەکردندایە',
    col_ready: 'ئامادەیە بۆ وەرگرتن',
    emptyColumn: 'هیچ نییە',
    minutesAgo: 'پێش {n} خ',
    justNow: 'ئێستا',
    readyIn: 'ئامادە دەبێت لە {n} خ',
    late: '{n} خ دواکەوتووە',
    accept: 'قبوڵکردن',
    prepTime: 'کاتی ئامادەکردن',
    reject: 'ڕەتکردنەوە',
    rejectTitle: 'ڕەتکردنەوەی داواکاری #{id}',
    rejectReason: 'هۆکاری ڕەتکردنەوە',
    reason_out_of_stock: 'هەندێک شت نەماوە',
    reason_busy: 'چێشتخانەکە زۆر قەرەباڵغە',
    reason_closing: 'بەم زووانە دادەخەین',
    otherReason: 'هۆکاری تر',
    cancel: 'هەڵوەشاندنەوە',
    confirmReject: 'ڕەتکردنەوەی داواکاری',
    markReady: 'ئامادەیە',
    waitingCaptain: 'چاوەڕێی کاپتن',
    captainComing: 'کاپتن دێت بۆ وەرگرتن',
    cash: 'نەختینە',
    paid: 'پارەدراوە',
    total: 'کۆی گشتی',
    min: 'خ',
    available: 'بەردەستە',
    outOfStock: 'نەماوە',
    noStores: 'هیچ دووکانێک بەم هەژمارەوە نەبەستراوە.',
    currency: 'د.ع',
    err_invalid_phone: 'ژمارەکە هەڵەیە. ژمارەیەکی عێراقی بنووسە کە بە 07 دەست پێدەکات.',
    err_invalid_code: 'کۆدەکە هەڵەیە یان بەسەرچووە.',
    err_too_soon: 'کەمێک چاوەڕێ بکە پێش داواکردنی کۆدێکی نوێ.',
    err_too_many_requests: 'داواکاری زۆر بۆ ئەم ژمارەیە. دوای کاتژمێرێک هەوڵ بدەرەوە.',
    err_not_vendor: 'ئەم ژمارەیە هەژماری دووکان نییە. پەیوەندی بە تیمی واصلەوە بکە.',
    err_invalid_transition: 'دۆخی داواکارییەکە گۆڕا. پانێڵەکە نوێکرایەوە.',
    err_network: 'پەیوەندی نەکرا. ئینتەرنێتەکەت بپشکنە.',
    err_generic: 'هەڵەیەک ڕوویدا. دووبارە هەوڵ بدەرەوە.',
    offline: 'پەیوەندی پچڕا. هەوڵ دەدەینەوە...',
  },
  en: {
    brandLine: 'Wasel for stores. Take orders and get them ready.',
    portalTag: 'Store portal',
    loginTitle: 'Store login',
    loginLead: "Enter the store owner's phone number and we'll send a login code.",
    phone: 'Phone number',
    phoneHelp: 'An Iraqi number starting with 07',
    sendCode: 'Send code',
    codeTitle: 'Enter the code',
    codeLead: 'We sent a 6-digit code to {phone}.',
    code: 'Login code',
    confirm: 'Confirm',
    changeNumber: 'Change number',
    orders: 'Orders',
    menu: 'Menu',
    logout: 'Log out',
    storeOpen: 'Store open',
    storeClosed: 'Store closed',
    soundOn: 'Sound on',
    soundOff: 'Turn on order sound',
    soundBlocked: 'Click here to turn on the new-order sound.',
    mute: 'Stop ringing',
    col_received: 'New orders',
    col_preparing: 'Preparing',
    col_ready: 'Ready for pickup',
    emptyColumn: 'Nothing here',
    minutesAgo: '{n} min ago',
    justNow: 'Just now',
    readyIn: 'Ready in {n} min',
    late: '{n} min late',
    accept: 'Accept',
    prepTime: 'Prep time',
    reject: 'Reject',
    rejectTitle: 'Reject order #{id}',
    rejectReason: 'Reason',
    reason_out_of_stock: 'Some items ran out',
    reason_busy: "We're too busy",
    reason_closing: "We're closing soon",
    otherReason: 'Other reason',
    cancel: 'Cancel',
    confirmReject: 'Reject order',
    markReady: 'Ready',
    waitingCaptain: 'Waiting for a captain',
    captainComing: 'Captain on the way to collect',
    cash: 'Cash',
    paid: 'Paid',
    total: 'Total',
    min: 'min',
    available: 'Available',
    outOfStock: 'Out of stock',
    noStores: 'No store is linked to this account.',
    currency: 'IQD',
    err_invalid_phone: "That number isn't valid. Enter an Iraqi number starting with 07.",
    err_invalid_code: 'The code is wrong or has expired.',
    err_too_soon: 'Wait a moment before asking for a new code.',
    err_too_many_requests: 'Too many codes for this number. Try again in an hour.',
    err_not_vendor: "This number isn't a store account. Contact the Wasel team.",
    err_invalid_transition: 'The order changed. The board has been refreshed.',
    err_network: "Couldn't connect. Check your internet.",
    err_generic: 'Something went wrong. Try again.',
    offline: 'Connection lost. Reconnecting...',
  },
} satisfies Record<Lang, Record<string, string>>

export type StringKey = keyof (typeof strings)['en']

export function translate(lang: Lang, key: StringKey, vars: Record<string, string | number> = {}): string {
  let text: string = strings[lang][key] ?? strings.en[key] ?? key
  for (const [name, value] of Object.entries(vars)) text = text.replaceAll(`{${name}}`, String(value))
  return text
}

/** Looks up an error code's message, falling back to the generic one. */
export function errorText(lang: Lang, code: string): string {
  const key = `err_${code}` as StringKey
  return key in strings.en ? translate(lang, key) : translate(lang, 'err_generic')
}

export function pickName(lang: Lang, names: Names): string {
  return (lang !== 'ar' && names[lang]) || names.ar
}

export function money(lang: Lang, amount: string | number): string {
  const whole = Math.round(Number(amount))
  return `${whole.toLocaleString('en-US')} ${translate(lang, 'currency')}`
}

export const LANGUAGES: { code: Lang; label: string }[] = [
  { code: 'ar', label: 'العربية' },
  { code: 'ku', label: 'کوردی' },
  { code: 'en', label: 'English' },
]

export const isRtl = (lang: Lang) => lang !== 'en'

/**
 * The code from whatever was typed or pasted: Arabic-Indic digits become
 * 0-9, and the last 6 digits are kept, so pasting a whole message
 * ("Your Wasel code for +964...: 482913") gives the code, not the phone number.
 */
export function codeDigits(text: string): string {
  return text
    .replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/[۰-۹]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/\D/g, '')
    .slice(-6)
}
