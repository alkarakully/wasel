/// Data from the Wasel API. Money comes as strings with exactly its currency's
/// decimals ("18000" dinars, "12.50" riyals, "0.750" Kuwaiti dinars), next to a
/// currency code. Kept as numbers for showing; totals always come from the server.
num _money(dynamic value) => value == null ? 0 : num.parse(value.toString());

double? _double(dynamic value) =>
    value == null ? null : (value as num).toDouble();

class GeoPoint {
  const GeoPoint(this.lat, this.lng);
  final double lat;
  final double lng;

  static GeoPoint? fromJson(dynamic json) => json == null
      ? null
      : GeoPoint(
          (json['lat'] as num).toDouble(),
          (json['lng'] as num).toDouble(),
        );
}

/// Picks the product's name in the app language, falling back to Arabic.
String localizedName(String lang, String ar, String ku, String en) {
  if (lang == 'ku' && ku.isNotEmpty) return ku;
  if (lang == 'en' && en.isNotEmpty) return en;
  return ar;
}

class User {
  User({
    required this.id,
    required this.phone,
    required this.name,
    required this.role,
    required this.languagePref,
    this.country = 'IQ',
  });
  final int id;
  final String phone;
  final String name;
  final String role;
  final String languagePref;

  /// The account's country (its phone's); the wallet is in its currency.
  final String country;

  factory User.fromJson(Map<String, dynamic> json) => User(
    id: json['id'],
    phone: json['phone'],
    name: json['name'] ?? '',
    role: json['role'],
    languagePref: json['language_pref'] ?? 'ar',
    country: json['country'] ?? 'IQ',
  );
}

class Vendor {
  Vendor({
    required this.id,
    required this.name,
    required this.type,
    required this.cuisine,
    required this.isOpen,
    this.distanceKm,
    this.deliveryFee,
    this.country = 'IQ',
    this.currency = 'IQD',
  });
  final int id;
  final String name;
  final String type;
  final String cuisine;
  final bool isOpen;

  /// Where the store trades; its prices and fees are in [currency].
  final String country;
  final String currency;
  final double? distanceKm;
  final num? deliveryFee;

  factory Vendor.fromJson(Map<String, dynamic> json) => Vendor(
    id: json['id'],
    name: json['name'],
    type: json['type'],
    cuisine: json['cuisine'] ?? '',
    isOpen: json['is_open'] ?? false,
    distanceKm: _double(json['distance_km']),
    deliveryFee: json['delivery_fee'] == null
        ? null
        : _money(json['delivery_fee']),
    country: json['country'] ?? 'IQ',
    currency: json['currency'] ?? 'IQD',
  );
}

class Modifier {
  Modifier({
    required this.id,
    required this.groupName,
    required this.nameAr,
    required this.nameKu,
    required this.nameEn,
    required this.priceDelta,
    required this.isRequired,
  });
  final int id;
  final String groupName;
  final String nameAr;
  final String nameKu;
  final String nameEn;
  final num priceDelta;
  final bool isRequired;

  String name(String lang) => localizedName(lang, nameAr, nameKu, nameEn);

  factory Modifier.fromJson(Map<String, dynamic> json) => Modifier(
    id: json['id'],
    groupName: json['group_name'],
    nameAr: json['name_ar'],
    nameKu: json['name_ku'] ?? '',
    nameEn: json['name_en'] ?? '',
    priceDelta: _money(json['price_delta']),
    isRequired: json['is_required'] ?? false,
  );
}

class Product {
  Product({
    required this.id,
    required this.nameAr,
    required this.nameKu,
    required this.nameEn,
    required this.menuSection,
    required this.price,
    required this.unitType,
    required this.isAvailable,
    required this.modifiers,
  });
  final int id;
  final String nameAr;
  final String nameKu;
  final String nameEn;
  final String menuSection;
  final num price;
  final String unitType;
  final bool isAvailable;
  final List<Modifier> modifiers;

  bool get soldByKg => unitType == 'kg';
  String name(String lang) => localizedName(lang, nameAr, nameKu, nameEn);

  /// Option groups in menu order; a group is required if any option in it is.
  Map<String, List<Modifier>> get modifierGroups {
    final groups = <String, List<Modifier>>{};
    for (final modifier in modifiers) {
      groups.putIfAbsent(modifier.groupName, () => []).add(modifier);
    }
    return groups;
  }

  factory Product.fromJson(Map<String, dynamic> json) => Product(
    id: json['id'],
    nameAr: json['name_ar'],
    nameKu: json['name_ku'] ?? '',
    nameEn: json['name_en'] ?? '',
    menuSection: json['menu_section'] ?? '',
    price: _money(json['price']),
    unitType: json['unit_type'] ?? 'item',
    isAvailable: json['is_available'] ?? true,
    modifiers: [for (final m in json['modifiers'] ?? []) Modifier.fromJson(m)],
  );
}

class VendorDetail extends Vendor {
  VendorDetail({
    required super.id,
    required super.name,
    required super.type,
    required super.cuisine,
    required super.isOpen,
    super.country,
    super.currency,
    required this.products,
  });
  final List<Product> products;

  factory VendorDetail.fromJson(Map<String, dynamic> json) => VendorDetail(
    id: json['id'],
    name: json['name'],
    type: json['type'],
    cuisine: json['cuisine'] ?? '',
    isOpen: json['is_open'] ?? false,
    country: json['country'] ?? 'IQ',
    currency: json['currency'] ?? 'IQD',
    products: [for (final p in json['products'] ?? []) Product.fromJson(p)],
  );
}

class Offer {
  Offer({
    required this.id,
    required this.title,
    required this.type,
    required this.value,
  });
  final int id;
  final String title;
  final String type;
  final double value;

  factory Offer.fromJson(Map<String, dynamic> json) => Offer(
    id: json['id'],
    title: json['title'],
    type: json['type'],
    value: double.parse(json['value'].toString()),
  );
}

class Quote {
  Quote({
    required this.subtotal,
    required this.deliveryFee,
    required this.serviceFee,
    required this.discount,
    required this.tip,
    required this.total,
    required this.waselPlus,
    this.currency = 'IQD',
  });
  final String currency;
  final num subtotal;
  final num deliveryFee;
  final num serviceFee;
  final num discount;
  final num tip;
  final num total;
  final bool waselPlus;

  factory Quote.fromJson(Map<String, dynamic> json) => Quote(
    subtotal: _money(json['subtotal']),
    deliveryFee: _money(json['delivery_fee']),
    serviceFee: _money(json['service_fee']),
    discount: _money(json['discount']),
    tip: _money(json['tip']),
    total: _money(json['total_amount']),
    waselPlus: json['wasel_plus'] ?? false,
    currency: json['currency'] ?? 'IQD',
  );
}

class CaptainLocation {
  CaptainLocation({required this.point, required this.updatedAt});
  final GeoPoint point;
  final DateTime updatedAt;

  static CaptainLocation? fromJson(dynamic json) => json == null
      ? null
      : CaptainLocation(
          point: GeoPoint.fromJson(json)!,
          updatedAt: DateTime.parse(json['updated_at']),
        );
}

class Order {
  Order({
    required this.id,
    required this.vendorName,
    required this.status,
    required this.captainId,
    required this.total,
    required this.deliveryPin,
    required this.vendorLocation,
    required this.deliveryLocation,
    required this.captainLocation,
    required this.createdAt,
    this.deliveryAddress = '',
    this.paymentType = 'cod',
    this.customerName,
    this.customerPhone,
    this.vendorId,
    this.items = const [],
    this.estimatedReadyAt,
    this.currency = 'IQD',
  });
  final int id;

  /// Every amount on the order is in this currency (the store's when it was placed).
  final String currency;
  final int? vendorId;
  final String vendorName;
  final String status;
  final int? captainId;
  final num total;
  final String? deliveryPin;
  final GeoPoint? vendorLocation;
  final GeoPoint? deliveryLocation;
  final CaptainLocation? captainLocation;
  final DateTime createdAt;
  final String deliveryAddress;
  final String paymentType;

  /// Only sent to the order's captain and store while the order is active.
  final String? customerName;
  final String? customerPhone;

  /// What was ordered; the store's board shows it.
  final List<OrderItem> items;

  /// When the store said it would be ready (set on accept).
  final DateTime? estimatedReadyAt;

  /// Cash the captain collects at the door (0 when paid in the app).
  num get cashToCollect => paymentType == 'cod' ? total : 0;

  static const steps = [
    'received',
    'preparing',
    'ready',
    'out_for_delivery',
    'delivered',
  ];

  /// Statuses the store's board shows: new, cooking, waiting for a captain.
  static const boardStatuses = ['received', 'preparing', 'ready'];
  bool get isFinished => status == 'delivered' || status == 'cancelled';
  bool get isTracked =>
      const ['preparing', 'ready', 'out_for_delivery'].contains(status);

  factory Order.fromJson(Map<String, dynamic> json) => Order(
    id: json['id'],
    vendorName: json['vendor_name'] ?? '',
    status: json['status'],
    captainId: json['captain'],
    total: _money(json['total_amount']),
    deliveryPin: json['delivery_pin'],
    vendorLocation: GeoPoint.fromJson(json['vendor_location']),
    deliveryLocation: GeoPoint.fromJson(json['delivery_location']),
    captainLocation: CaptainLocation.fromJson(json['captain_location']),
    createdAt: DateTime.parse(json['created_at']),
    deliveryAddress: json['delivery_address'] ?? '',
    paymentType: json['payment_type'] ?? 'cod',
    customerName: json['customer_contact']?['name'],
    customerPhone: json['customer_contact']?['phone'],
    vendorId: json['vendor'],
    items: [for (final i in json['items'] ?? []) OrderItem.fromJson(i)],
    estimatedReadyAt: json['estimated_ready_at'] == null
        ? null
        : DateTime.parse(json['estimated_ready_at']),
    currency: json['currency'] ?? 'IQD',
  );
}

/// One line of an order, as the store sees it.
class OrderItem {
  OrderItem({
    required this.names,
    required this.quantity,
    required this.unitType,
    this.modifiers = const [],
  });

  /// Name per language: ar, ku, en.
  final Map<String, String> names;
  final double quantity;
  final String unitType;

  /// Chosen options, each as a name per language.
  final List<Map<String, String>> modifiers;

  bool get soldByKg => unitType == 'kg';
  String name(String lang) => localizedName(
    lang,
    names['ar'] ?? '',
    names['ku'] ?? '',
    names['en'] ?? '',
  );

  factory OrderItem.fromJson(Map<String, dynamic> json) {
    Map<String, String> names(dynamic n) => {
      for (final lang in const ['ar', 'ku', 'en'])
        lang: (n?[lang] ?? '').toString(),
    };
    return OrderItem(
      names: names(json['name']),
      quantity: double.parse('${json['quantity']}'),
      unitType: json['unit_type'] ?? 'item',
      modifiers: [for (final m in json['modifiers'] ?? []) names(m['name'])],
    );
  }
}

/// An order offered to this captain alone, until [expiresAt].
class DispatchOffer {
  DispatchOffer({
    required this.id,
    required this.order,
    required this.distanceKm,
    required this.expiresAt,
  });

  final int id;
  final Order order;
  final double distanceKm;
  final DateTime expiresAt;

  Duration get timeLeft {
    final left = expiresAt.difference(DateTime.now());
    return left.isNegative ? Duration.zero : left;
  }

  factory DispatchOffer.fromJson(Map<String, dynamic> json) => DispatchOffer(
    id: json['id'],
    order: Order.fromJson(json['order']),
    distanceKm: (json['distance_km'] as num).toDouble(),
    expiresAt: DateTime.parse(json['expires_at']),
  );
}

/// An invite to join a store's team, as the invited person sees it.
class StoreInvite {
  StoreInvite({
    required this.id,
    required this.storeId,
    required this.storeName,
    required this.storeType,
    required this.role,
    required this.invitedBy,
  });

  final int id;
  final int storeId;
  final String storeName;
  final String storeType;

  /// "manager" or "cashier".
  final String role;
  final String invitedBy;

  factory StoreInvite.fromJson(Map<String, dynamic> json) => StoreInvite(
    id: json['id'],
    storeId: json['store']['id'],
    storeName: json['store']['name'],
    storeType: json['store']['type'] ?? 'restaurant',
    role: json['role'],
    invitedBy: json['invited_by'] ?? '',
  );
}
