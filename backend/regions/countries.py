"""
Every country a phone number can come from, Iraq first, then the Gulf.

Each row: ISO code, dial code, English name, Arabic name. The first seven are
the short list shown at the top of every country picker; they are also the
countries Wasel can run stores in (see regions.py).
"""

SHORT_LIST = ["IQ", "SA", "AE", "KW", "QA", "BH", "OM"]

# National mobile numbers (without the trunk 0) where we know the rule;
# anywhere else any 6 to 14 digits are accepted.
MOBILE_RULES = {
    "IQ": r"7[3-9]\d{8}",
    "SA": r"5\d{8}",
    "AE": r"5\d{8}",
    "KW": r"[569]\d{7}",
    "QA": r"[3567]\d{7}",
    "BH": r"[36]\d{7}",
    "OM": r"[79]\d{7}",
}

COUNTRIES = [
    ("IQ", "964", "Iraq", "العراق"),
    ("SA", "966", "Saudi Arabia", "السعودية"),
    ("AE", "971", "United Arab Emirates", "الإمارات"),
    ("KW", "965", "Kuwait", "الكويت"),
    ("QA", "974", "Qatar", "قطر"),
    ("BH", "973", "Bahrain", "البحرين"),
    ("OM", "968", "Oman", "عُمان"),
    ("AF", "93", "Afghanistan", "أفغانستان"),
    ("AL", "355", "Albania", "ألبانيا"),
    ("DZ", "213", "Algeria", "الجزائر"),
    ("AD", "376", "Andorra", "أندورا"),
    ("AO", "244", "Angola", "أنغولا"),
    ("AR", "54", "Argentina", "الأرجنتين"),
    ("AM", "374", "Armenia", "أرمينيا"),
    ("AU", "61", "Australia", "أستراليا"),
    ("AT", "43", "Austria", "النمسا"),
    ("AZ", "994", "Azerbaijan", "أذربيجان"),
    ("BD", "880", "Bangladesh", "بنغلاديش"),
    ("BY", "375", "Belarus", "بيلاروسيا"),
    ("BE", "32", "Belgium", "بلجيكا"),
    ("BJ", "229", "Benin", "بنين"),
    ("BO", "591", "Bolivia", "بوليفيا"),
    ("BA", "387", "Bosnia and Herzegovina", "البوسنة والهرسك"),
    ("BW", "267", "Botswana", "بوتسوانا"),
    ("BR", "55", "Brazil", "البرازيل"),
    ("BN", "673", "Brunei", "بروناي"),
    ("BG", "359", "Bulgaria", "بلغاريا"),
    ("BF", "226", "Burkina Faso", "بوركينا فاسو"),
    ("BI", "257", "Burundi", "بوروندي"),
    ("KH", "855", "Cambodia", "كمبوديا"),
    ("CM", "237", "Cameroon", "الكاميرون"),
    ("CA", "1", "Canada", "كندا"),
    ("TD", "235", "Chad", "تشاد"),
    ("CL", "56", "Chile", "تشيلي"),
    ("CN", "86", "China", "الصين"),
    ("CO", "57", "Colombia", "كولومبيا"),
    ("KM", "269", "Comoros", "جزر القمر"),
    ("CG", "242", "Congo", "الكونغو"),
    ("CD", "243", "Congo (DRC)", "الكونغو الديمقراطية"),
    ("CR", "506", "Costa Rica", "كوستاريكا"),
    ("CI", "225", "Côte d’Ivoire", "ساحل العاج"),
    ("HR", "385", "Croatia", "كرواتيا"),
    ("CU", "53", "Cuba", "كوبا"),
    ("CY", "357", "Cyprus", "قبرص"),
    ("CZ", "420", "Czechia", "التشيك"),
    ("DK", "45", "Denmark", "الدنمارك"),
    ("DJ", "253", "Djibouti", "جيبوتي"),
    ("DO", "1", "Dominican Republic", "جمهورية الدومينيكان"),
    ("EC", "593", "Ecuador", "الإكوادور"),
    ("EG", "20", "Egypt", "مصر"),
    ("SV", "503", "El Salvador", "السلفادور"),
    ("ER", "291", "Eritrea", "إريتريا"),
    ("EE", "372", "Estonia", "إستونيا"),
    ("ET", "251", "Ethiopia", "إثيوبيا"),
    ("FI", "358", "Finland", "فنلندا"),
    ("FR", "33", "France", "فرنسا"),
    ("GA", "241", "Gabon", "الغابون"),
    ("GM", "220", "Gambia", "غامبيا"),
    ("GE", "995", "Georgia", "جورجيا"),
    ("DE", "49", "Germany", "ألمانيا"),
    ("GH", "233", "Ghana", "غانا"),
    ("GR", "30", "Greece", "اليونان"),
    ("GT", "502", "Guatemala", "غواتيمالا"),
    ("GN", "224", "Guinea", "غينيا"),
    ("HT", "509", "Haiti", "هايتي"),
    ("HN", "504", "Honduras", "هندوراس"),
    ("HK", "852", "Hong Kong", "هونغ كونغ"),
    ("HU", "36", "Hungary", "المجر"),
    ("IS", "354", "Iceland", "آيسلندا"),
    ("IN", "91", "India", "الهند"),
    ("ID", "62", "Indonesia", "إندونيسيا"),
    ("IR", "98", "Iran", "إيران"),
    ("IE", "353", "Ireland", "أيرلندا"),
    ("IT", "39", "Italy", "إيطاليا"),
    ("JM", "1", "Jamaica", "جامايكا"),
    ("JP", "81", "Japan", "اليابان"),
    ("JO", "962", "Jordan", "الأردن"),
    ("KZ", "7", "Kazakhstan", "كازاخستان"),
    ("KE", "254", "Kenya", "كينيا"),
    ("KR", "82", "South Korea", "كوريا الجنوبية"),
    ("KG", "996", "Kyrgyzstan", "قيرغيزستان"),
    ("LA", "856", "Laos", "لاوس"),
    ("LV", "371", "Latvia", "لاتفيا"),
    ("LB", "961", "Lebanon", "لبنان"),
    ("LY", "218", "Libya", "ليبيا"),
    ("LT", "370", "Lithuania", "ليتوانيا"),
    ("LU", "352", "Luxembourg", "لوكسمبورغ"),
    ("MG", "261", "Madagascar", "مدغشقر"),
    ("MW", "265", "Malawi", "مالاوي"),
    ("MY", "60", "Malaysia", "ماليزيا"),
    ("MV", "960", "Maldives", "جزر المالديف"),
    ("ML", "223", "Mali", "مالي"),
    ("MT", "356", "Malta", "مالطا"),
    ("MR", "222", "Mauritania", "موريتانيا"),
    ("MU", "230", "Mauritius", "موريشيوس"),
    ("MX", "52", "Mexico", "المكسيك"),
    ("MD", "373", "Moldova", "مولدوفا"),
    ("MC", "377", "Monaco", "موناكو"),
    ("MN", "976", "Mongolia", "منغوليا"),
    ("ME", "382", "Montenegro", "الجبل الأسود"),
    ("MA", "212", "Morocco", "المغرب"),
    ("MZ", "258", "Mozambique", "موزمبيق"),
    ("MM", "95", "Myanmar", "ميانمار"),
    ("NA", "264", "Namibia", "ناميبيا"),
    ("NP", "977", "Nepal", "نيبال"),
    ("NL", "31", "Netherlands", "هولندا"),
    ("NZ", "64", "New Zealand", "نيوزيلندا"),
    ("NI", "505", "Nicaragua", "نيكاراغوا"),
    ("NE", "227", "Niger", "النيجر"),
    ("NG", "234", "Nigeria", "نيجيريا"),
    ("MK", "389", "North Macedonia", "مقدونيا الشمالية"),
    ("NO", "47", "Norway", "النرويج"),
    ("PK", "92", "Pakistan", "باكستان"),
    ("PS", "970", "Palestine", "فلسطين"),
    ("PA", "507", "Panama", "بنما"),
    ("PY", "595", "Paraguay", "باراغواي"),
    ("PE", "51", "Peru", "بيرو"),
    ("PH", "63", "Philippines", "الفلبين"),
    ("PL", "48", "Poland", "بولندا"),
    ("PT", "351", "Portugal", "البرتغال"),
    ("RO", "40", "Romania", "رومانيا"),
    ("RU", "7", "Russia", "روسيا"),
    ("RW", "250", "Rwanda", "رواندا"),
    ("SN", "221", "Senegal", "السنغال"),
    ("RS", "381", "Serbia", "صربيا"),
    ("SL", "232", "Sierra Leone", "سيراليون"),
    ("SG", "65", "Singapore", "سنغافورة"),
    ("SK", "421", "Slovakia", "سلوفاكيا"),
    ("SI", "386", "Slovenia", "سلوفينيا"),
    ("SO", "252", "Somalia", "الصومال"),
    ("ZA", "27", "South Africa", "جنوب أفريقيا"),
    ("SS", "211", "South Sudan", "جنوب السودان"),
    ("ES", "34", "Spain", "إسبانيا"),
    ("LK", "94", "Sri Lanka", "سريلانكا"),
    ("SD", "249", "Sudan", "السودان"),
    ("SE", "46", "Sweden", "السويد"),
    ("CH", "41", "Switzerland", "سويسرا"),
    ("SY", "963", "Syria", "سوريا"),
    ("TW", "886", "Taiwan", "تايوان"),
    ("TJ", "992", "Tajikistan", "طاجيكستان"),
    ("TZ", "255", "Tanzania", "تنزانيا"),
    ("TH", "66", "Thailand", "تايلاند"),
    ("TG", "228", "Togo", "توغو"),
    ("TN", "216", "Tunisia", "تونس"),
    ("TR", "90", "Türkiye", "تركيا"),
    ("TM", "993", "Turkmenistan", "تركمانستان"),
    ("UG", "256", "Uganda", "أوغندا"),
    ("UA", "380", "Ukraine", "أوكرانيا"),
    ("GB", "44", "United Kingdom", "المملكة المتحدة"),
    ("US", "1", "United States", "الولايات المتحدة"),
    ("UY", "598", "Uruguay", "الأوروغواي"),
    ("UZ", "998", "Uzbekistan", "أوزبكستان"),
    ("VE", "58", "Venezuela", "فنزويلا"),
    ("VN", "84", "Vietnam", "فيتنام"),
    ("YE", "967", "Yemen", "اليمن"),
    ("ZM", "260", "Zambia", "زامبيا"),
    ("ZW", "263", "Zimbabwe", "زيمبابوي"),
]

BY_CODE = {row[0]: row for row in COUNTRIES}
# For "+1..." numbers, which several countries share, pick the United States.
_PREFERRED = {"1": "US", "7": "RU"}


def dial_code(country):
    return BY_CODE[country][1]


def country_for_dial(digits):
    """The country whose dial code starts these international digits (longest match), or None."""
    for length in (3, 2, 1):
        prefix = digits[:length]
        if prefix in _PREFERRED and length == len(prefix):
            return _PREFERRED[prefix], prefix
        matches = [code for code, dial, *_ in COUNTRIES if dial == prefix]
        if matches:
            return matches[0], prefix
    return None, None


def ordered():
    """Short list first (Iraq on top), then the rest A–Z by English name."""
    rest = sorted((row for row in COUNTRIES if row[0] not in SHORT_LIST), key=lambda row: row[2])
    return [BY_CODE[code] for code in SHORT_LIST] + rest
