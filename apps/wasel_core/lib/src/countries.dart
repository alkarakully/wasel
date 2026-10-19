/// Generated from GET /api/countries/ (backend/regions): every country a
/// phone number can come from, Iraq first, then the Gulf, then A–Z.
library;

class Country {
  const Country(this.code, this.dial, this.en, this.ar);
  final String code;
  final String dial;
  final String en;
  final String ar;

  /// The name in the app language (Kurdish readers get the Arabic one).
  String name(String lang) => lang == 'en' ? en : ar;

  /// A flag emoji from the two-letter code (for text outside the app font).
  String get flag =>
      String.fromCharCodes(code.codeUnits.map((c) => 0x1f1e6 + c - 65));
}

/// The countries Wasel runs stores in, each with its own currency and clock.
class Region {
  const Region(
    this.country,
    this.currency,
    this.decimals,
    this.lat,
    this.lng,
    this.tips,
  );
  final String country;
  final String currency;
  final int decimals;
  final double lat;
  final double lng;

  /// Quick tip choices at checkout, in the currency.
  final List<num> tips;
}

const shortList = ['IQ', 'SA', 'AE', 'KW', 'QA', 'BH', 'OM'];

const countries = <Country>[
  Country('IQ', '964', 'Iraq', 'العراق'),
  Country('SA', '966', 'Saudi Arabia', 'السعودية'),
  Country('AE', '971', 'United Arab Emirates', 'الإمارات'),
  Country('KW', '965', 'Kuwait', 'الكويت'),
  Country('QA', '974', 'Qatar', 'قطر'),
  Country('BH', '973', 'Bahrain', 'البحرين'),
  Country('OM', '968', 'Oman', 'عُمان'),
  Country('AF', '93', 'Afghanistan', 'أفغانستان'),
  Country('AL', '355', 'Albania', 'ألبانيا'),
  Country('DZ', '213', 'Algeria', 'الجزائر'),
  Country('AD', '376', 'Andorra', 'أندورا'),
  Country('AO', '244', 'Angola', 'أنغولا'),
  Country('AR', '54', 'Argentina', 'الأرجنتين'),
  Country('AM', '374', 'Armenia', 'أرمينيا'),
  Country('AU', '61', 'Australia', 'أستراليا'),
  Country('AT', '43', 'Austria', 'النمسا'),
  Country('AZ', '994', 'Azerbaijan', 'أذربيجان'),
  Country('BD', '880', 'Bangladesh', 'بنغلاديش'),
  Country('BY', '375', 'Belarus', 'بيلاروسيا'),
  Country('BE', '32', 'Belgium', 'بلجيكا'),
  Country('BJ', '229', 'Benin', 'بنين'),
  Country('BO', '591', 'Bolivia', 'بوليفيا'),
  Country('BA', '387', 'Bosnia and Herzegovina', 'البوسنة والهرسك'),
  Country('BW', '267', 'Botswana', 'بوتسوانا'),
  Country('BR', '55', 'Brazil', 'البرازيل'),
  Country('BN', '673', 'Brunei', 'بروناي'),
  Country('BG', '359', 'Bulgaria', 'بلغاريا'),
  Country('BF', '226', 'Burkina Faso', 'بوركينا فاسو'),
  Country('BI', '257', 'Burundi', 'بوروندي'),
  Country('KH', '855', 'Cambodia', 'كمبوديا'),
  Country('CM', '237', 'Cameroon', 'الكاميرون'),
  Country('CA', '1', 'Canada', 'كندا'),
  Country('TD', '235', 'Chad', 'تشاد'),
  Country('CL', '56', 'Chile', 'تشيلي'),
  Country('CN', '86', 'China', 'الصين'),
  Country('CO', '57', 'Colombia', 'كولومبيا'),
  Country('KM', '269', 'Comoros', 'جزر القمر'),
  Country('CG', '242', 'Congo', 'الكونغو'),
  Country('CD', '243', 'Congo (DRC)', 'الكونغو الديمقراطية'),
  Country('CR', '506', 'Costa Rica', 'كوستاريكا'),
  Country('HR', '385', 'Croatia', 'كرواتيا'),
  Country('CU', '53', 'Cuba', 'كوبا'),
  Country('CY', '357', 'Cyprus', 'قبرص'),
  Country('CZ', '420', 'Czechia', 'التشيك'),
  Country('CI', '225', 'Côte d’Ivoire', 'ساحل العاج'),
  Country('DK', '45', 'Denmark', 'الدنمارك'),
  Country('DJ', '253', 'Djibouti', 'جيبوتي'),
  Country('DO', '1', 'Dominican Republic', 'جمهورية الدومينيكان'),
  Country('EC', '593', 'Ecuador', 'الإكوادور'),
  Country('EG', '20', 'Egypt', 'مصر'),
  Country('SV', '503', 'El Salvador', 'السلفادور'),
  Country('ER', '291', 'Eritrea', 'إريتريا'),
  Country('EE', '372', 'Estonia', 'إستونيا'),
  Country('ET', '251', 'Ethiopia', 'إثيوبيا'),
  Country('FI', '358', 'Finland', 'فنلندا'),
  Country('FR', '33', 'France', 'فرنسا'),
  Country('GA', '241', 'Gabon', 'الغابون'),
  Country('GM', '220', 'Gambia', 'غامبيا'),
  Country('GE', '995', 'Georgia', 'جورجيا'),
  Country('DE', '49', 'Germany', 'ألمانيا'),
  Country('GH', '233', 'Ghana', 'غانا'),
  Country('GR', '30', 'Greece', 'اليونان'),
  Country('GT', '502', 'Guatemala', 'غواتيمالا'),
  Country('GN', '224', 'Guinea', 'غينيا'),
  Country('HT', '509', 'Haiti', 'هايتي'),
  Country('HN', '504', 'Honduras', 'هندوراس'),
  Country('HK', '852', 'Hong Kong', 'هونغ كونغ'),
  Country('HU', '36', 'Hungary', 'المجر'),
  Country('IS', '354', 'Iceland', 'آيسلندا'),
  Country('IN', '91', 'India', 'الهند'),
  Country('ID', '62', 'Indonesia', 'إندونيسيا'),
  Country('IR', '98', 'Iran', 'إيران'),
  Country('IE', '353', 'Ireland', 'أيرلندا'),
  Country('IT', '39', 'Italy', 'إيطاليا'),
  Country('JM', '1', 'Jamaica', 'جامايكا'),
  Country('JP', '81', 'Japan', 'اليابان'),
  Country('JO', '962', 'Jordan', 'الأردن'),
  Country('KZ', '7', 'Kazakhstan', 'كازاخستان'),
  Country('KE', '254', 'Kenya', 'كينيا'),
  Country('KG', '996', 'Kyrgyzstan', 'قيرغيزستان'),
  Country('LA', '856', 'Laos', 'لاوس'),
  Country('LV', '371', 'Latvia', 'لاتفيا'),
  Country('LB', '961', 'Lebanon', 'لبنان'),
  Country('LY', '218', 'Libya', 'ليبيا'),
  Country('LT', '370', 'Lithuania', 'ليتوانيا'),
  Country('LU', '352', 'Luxembourg', 'لوكسمبورغ'),
  Country('MG', '261', 'Madagascar', 'مدغشقر'),
  Country('MW', '265', 'Malawi', 'مالاوي'),
  Country('MY', '60', 'Malaysia', 'ماليزيا'),
  Country('MV', '960', 'Maldives', 'جزر المالديف'),
  Country('ML', '223', 'Mali', 'مالي'),
  Country('MT', '356', 'Malta', 'مالطا'),
  Country('MR', '222', 'Mauritania', 'موريتانيا'),
  Country('MU', '230', 'Mauritius', 'موريشيوس'),
  Country('MX', '52', 'Mexico', 'المكسيك'),
  Country('MD', '373', 'Moldova', 'مولدوفا'),
  Country('MC', '377', 'Monaco', 'موناكو'),
  Country('MN', '976', 'Mongolia', 'منغوليا'),
  Country('ME', '382', 'Montenegro', 'الجبل الأسود'),
  Country('MA', '212', 'Morocco', 'المغرب'),
  Country('MZ', '258', 'Mozambique', 'موزمبيق'),
  Country('MM', '95', 'Myanmar', 'ميانمار'),
  Country('NA', '264', 'Namibia', 'ناميبيا'),
  Country('NP', '977', 'Nepal', 'نيبال'),
  Country('NL', '31', 'Netherlands', 'هولندا'),
  Country('NZ', '64', 'New Zealand', 'نيوزيلندا'),
  Country('NI', '505', 'Nicaragua', 'نيكاراغوا'),
  Country('NE', '227', 'Niger', 'النيجر'),
  Country('NG', '234', 'Nigeria', 'نيجيريا'),
  Country('MK', '389', 'North Macedonia', 'مقدونيا الشمالية'),
  Country('NO', '47', 'Norway', 'النرويج'),
  Country('PK', '92', 'Pakistan', 'باكستان'),
  Country('PS', '970', 'Palestine', 'فلسطين'),
  Country('PA', '507', 'Panama', 'بنما'),
  Country('PY', '595', 'Paraguay', 'باراغواي'),
  Country('PE', '51', 'Peru', 'بيرو'),
  Country('PH', '63', 'Philippines', 'الفلبين'),
  Country('PL', '48', 'Poland', 'بولندا'),
  Country('PT', '351', 'Portugal', 'البرتغال'),
  Country('RO', '40', 'Romania', 'رومانيا'),
  Country('RU', '7', 'Russia', 'روسيا'),
  Country('RW', '250', 'Rwanda', 'رواندا'),
  Country('SN', '221', 'Senegal', 'السنغال'),
  Country('RS', '381', 'Serbia', 'صربيا'),
  Country('SL', '232', 'Sierra Leone', 'سيراليون'),
  Country('SG', '65', 'Singapore', 'سنغافورة'),
  Country('SK', '421', 'Slovakia', 'سلوفاكيا'),
  Country('SI', '386', 'Slovenia', 'سلوفينيا'),
  Country('SO', '252', 'Somalia', 'الصومال'),
  Country('ZA', '27', 'South Africa', 'جنوب أفريقيا'),
  Country('KR', '82', 'South Korea', 'كوريا الجنوبية'),
  Country('SS', '211', 'South Sudan', 'جنوب السودان'),
  Country('ES', '34', 'Spain', 'إسبانيا'),
  Country('LK', '94', 'Sri Lanka', 'سريلانكا'),
  Country('SD', '249', 'Sudan', 'السودان'),
  Country('SE', '46', 'Sweden', 'السويد'),
  Country('CH', '41', 'Switzerland', 'سويسرا'),
  Country('SY', '963', 'Syria', 'سوريا'),
  Country('TW', '886', 'Taiwan', 'تايوان'),
  Country('TJ', '992', 'Tajikistan', 'طاجيكستان'),
  Country('TZ', '255', 'Tanzania', 'تنزانيا'),
  Country('TH', '66', 'Thailand', 'تايلاند'),
  Country('TG', '228', 'Togo', 'توغو'),
  Country('TN', '216', 'Tunisia', 'تونس'),
  Country('TM', '993', 'Turkmenistan', 'تركمانستان'),
  Country('TR', '90', 'Türkiye', 'تركيا'),
  Country('UG', '256', 'Uganda', 'أوغندا'),
  Country('UA', '380', 'Ukraine', 'أوكرانيا'),
  Country('GB', '44', 'United Kingdom', 'المملكة المتحدة'),
  Country('US', '1', 'United States', 'الولايات المتحدة'),
  Country('UY', '598', 'Uruguay', 'الأوروغواي'),
  Country('UZ', '998', 'Uzbekistan', 'أوزبكستان'),
  Country('VE', '58', 'Venezuela', 'فنزويلا'),
  Country('VN', '84', 'Vietnam', 'فيتنام'),
  Country('YE', '967', 'Yemen', 'اليمن'),
  Country('ZM', '260', 'Zambia', 'زامبيا'),
  Country('ZW', '263', 'Zimbabwe', 'زيمبابوي'),
];

const regions = <Region>[
  Region('IQ', 'IQD', 0, 33.3152, 44.3661, [500, 1000, 2000]),
  Region('SA', 'SAR', 2, 24.7136, 46.6753, [2, 5, 10]),
  Region('AE', 'AED', 2, 25.2048, 55.2708, [2, 5, 10]),
  Region('KW', 'KWD', 3, 29.3759, 47.9774, [0.25, 0.5, 1]),
  Region('QA', 'QAR', 2, 25.2854, 51.531, [2, 5, 10]),
  Region('BH', 'BHD', 3, 26.2285, 50.586, [0.25, 0.5, 1]),
  Region('OM', 'OMR', 3, 23.588, 58.3829, [0.25, 0.5, 1]),
];

Country countryFor(String code) =>
    countries.firstWhere((c) => c.code == code, orElse: () => countries.first);

Region regionFor(String country) => regions.firstWhere(
  (r) => r.country == country,
  orElse: () => regions.first,
);

Region regionForCurrency(String currency) => regions.firstWhere(
  (r) => r.currency == currency,
  orElse: () => regions.first,
);

/// Decimals the currency is shown with: 0 for IQD, 2 for SAR, 3 for KWD.
int currencyDecimals(String currency) => regionForCurrency(currency).decimals;

/// A stored E.164 number for people: Iraqi ones as +964 770 123 4567, others
/// as +966 501234567.
String displayPhone(String e164) {
  if (e164.startsWith('+964') && e164.length == 14) {
    final local = e164.substring(4);
    return '+964 ${local.substring(0, 3)} ${local.substring(3, 6)} ${local.substring(6)}';
  }
  if (!e164.startsWith('+')) return e164;
  for (final n in const [3, 2, 1]) {
    if (e164.length <= n + 1) continue;
    final dial = e164.substring(1, 1 + n);
    if (countries.any((c) => c.dial == dial)) {
      return '+$dial ${e164.substring(1 + n)}';
    }
  }
  return e164;
}
