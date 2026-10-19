import 'package:flutter/foundation.dart';
import 'package:wasel_core/wasel_core.dart';

class CartLine {
  CartLine({
    required this.product,
    required this.quantity,
    required this.modifiers,
  });

  final Product product;
  double quantity;
  final List<Modifier> modifiers;

  num get unitPrice =>
      product.price + modifiers.fold<num>(0, (sum, m) => sum + m.priceDelta);

  /// An estimate for the cart; the quote from the server has the exact price.
  num get lineTotal => unitPrice * quantity;

  /// Same product with the same options adds to one line.
  bool sameChoiceAs(CartLine other) {
    if (other.product.id != product.id) return false;
    final mine = modifiers.map((m) => m.id).toSet();
    final theirs = other.modifiers.map((m) => m.id).toSet();
    return mine.length == theirs.length && mine.containsAll(theirs);
  }

  Map<String, dynamic> toJson() => {
    'product': product.id,
    'quantity': product.soldByKg
        ? quantity.toStringAsFixed(3)
        : quantity.round(),
    'modifiers': [for (final m in modifiers) m.id],
  };
}

/// One store's cart. Adding from another store asks the user to start over.
class Cart extends ChangeNotifier {
  int? vendorId;
  String vendorName = '';

  /// The store's currency; every price in the cart is in it.
  String currency = 'IQD';
  final List<CartLine> lines = [];

  bool get isEmpty => lines.isEmpty;
  int get itemCount => lines.fold(
    0,
    (sum, l) => sum + (l.product.soldByKg ? 1 : l.quantity.round()),
  );
  num get subtotal => lines.fold<num>(0, (sum, l) => sum + l.lineTotal);

  bool belongsToOtherStore(int storeId) =>
      vendorId != null && vendorId != storeId && lines.isNotEmpty;

  void add(Vendor store, CartLine line) {
    if (belongsToOtherStore(store.id)) clear(notify: false);
    vendorId = store.id;
    vendorName = store.name;
    currency = store.currency;
    final existing = lines.where((l) => l.sameChoiceAs(line)).firstOrNull;
    if (existing != null) {
      existing.quantity += line.quantity;
    } else {
      lines.add(line);
    }
    notifyListeners();
  }

  void changeQuantity(CartLine line, double delta) {
    line.quantity += delta;
    if (line.quantity <= 0.0001) lines.remove(line);
    if (lines.isEmpty) vendorId = null;
    notifyListeners();
  }

  void clear({bool notify = true}) {
    lines.clear();
    vendorId = null;
    vendorName = '';
    if (notify) notifyListeners();
  }

  List<Map<String, dynamic>> itemsJson() => [for (final l in lines) l.toJson()];
}
