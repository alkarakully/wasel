"""
Push notification text in Arabic, Kurdish (Sorani) and English.
Kurdish should be reviewed by a native speaker before launch.
"""

MESSAGES = {
    "offer": {
        "ar": ("طلب جديد لك", "{store} على بعد {km} كم. لديك {seconds} ثانية للقبول."),
        "ku": ("داواکارییەکی نوێ بۆ تۆ", "{store} {km} کم دوورە. {seconds} چرکەت هەیە بۆ قبوڵکردن."),
        "en": ("New order for you", "{store} is {km} km away. You have {seconds} seconds to accept."),
    },
    "order_preparing": {
        "ar": ("{store} قبل طلبك", "سيكون جاهزاً خلال {minutes} دقيقة تقريباً."),
        "ku": ("{store} داواکارییەکەتی قبوڵ کرد", "نزیکەی {minutes} خولەکی تر ئامادە دەبێت."),
        "en": ("{store} accepted your order", "It'll be ready in about {minutes} minutes."),
    },
    "order_out_for_delivery": {
        "ar": ("الكابتن في الطريق إليك", "افتح التطبيق لمتابعة الكابتن على الخريطة."),
        "ku": ("کاپتن لە ڕێگایە بۆ لات", "ئەپەکە بکەرەوە بۆ بینینی کاپتن لەسەر نەخشە."),
        "en": ("Your captain is on the way", "Open the app to follow them on the map."),
    },
    "order_delivered": {
        "ar": ("تم التوصيل. بالعافية!", "شكراً لطلبك من {store}."),
        "ku": ("گەیەندرا. نۆشی گیان!", "سوپاس بۆ داواکردنت لە {store}."),
        "en": ("Delivered. Enjoy!", "Thanks for ordering from {store}."),
    },
    "order_cancelled": {
        "ar": ("أُلغي طلبك من {store}", "{reason}"),
        "ku": ("داواکارییەکەت لە {store} هەڵوەشێنرایەوە", "{reason}"),
        "en": ("Your order from {store} was cancelled", "{reason}"),
    },
    "store_new_order": {
        "ar": ("طلب جديد #{order_id}", "{store}: اقبل الطلب الآن حتى لا ينتظر الزبون."),
        "ku": ("داواکاری نوێ #{order_id}", "{store}: ئێستا قبوڵی بکە با کڕیار چاوەڕێ نەکات."),
        "en": ("New order #{order_id}", "{store}: accept it now so the customer isn't kept waiting."),
    },
    "store_order_cancelled": {
        "ar": ("أُلغي الطلب #{order_id}", "ألغى الزبون الطلب من {store}. لا تحضّره."),
        "ku": ("داواکاری #{order_id} هەڵوەشێنرایەوە", "کڕیار داواکارییەکەی لە {store} هەڵوەشاندەوە. ئامادەی مەکە."),
        "en": ("Order #{order_id} was cancelled", "The customer cancelled their order from {store}. Don't prepare it."),
    },
    "store_approved": {
        "ar": ("تمت الموافقة على {store}", "متجرك جاهز على واصل. أضف قائمتك وافتح المتجر لاستقبال الطلبات."),
        "ku": ("{store} پەسەند کرا", "دووکانەکەت لە واصل ئامادەیە. لیستەکەت زیاد بکە و دووکان بکەرەوە بۆ وەرگرتنی داواکاری."),
        "en": ("{store} is approved", "Your store is ready on Wasel. Add your menu and open the store to take orders."),
    },
    "store_rejected": {
        "ar": ("لم نوافق على {store}", "{reason}"),
        "ku": ("{store} پەسەند نەکرا", "{reason}"),
        "en": ("{store} wasn't approved", "{reason}"),
    },
    "store_invite": {
        "ar": ("دعوة للانضمام إلى {store}", "سجّل الدخول إلى تطبيق المتجر لقبول الدعوة أو رفضها."),
        "ku": ("بانگهێشت بۆ بەشداریکردن لە {store}", "بچۆ ژوورەوە بۆ ئەپی دووکان بۆ قبوڵکردن یان ڕەتکردنەوەی بانگهێشتەکە."),
        "en": ("You're invited to join {store}", "Sign in to the store app to accept or decline."),
    },
    "plus_trial_ended": {
        "ar": ("انتهت تجربة واصل بلس", "اشترك للاستمرار في التوصيل المجاني."),
        "ku": ("تاقیکردنەوەی واصل پلەس کۆتایی هات", "بەشداربە بۆ بەردەوامبوونی گەیاندنی بەخۆڕایی."),
        "en": ("Your Wasel Plus trial has ended", "Subscribe to keep free delivery."),
    },
}


def render(kind, lang, context):
    """Title and body for one notification, in the user's language."""
    texts = MESSAGES[kind]
    title, body = texts.get(lang) or texts["ar"]
    return title.format(**context), body.format(**context)
