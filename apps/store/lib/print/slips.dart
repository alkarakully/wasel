import 'package:wasel_core/wasel_core.dart';

/// One item line on a slip: "2×" and the name, with chosen options below.
class SlipLine {
  const SlipLine(this.quantity, this.name, [this.options = '']);
  final String quantity;
  final String name;
  final String options;
}

/// What goes on the two printed slips, in the tablet's language. The delivery
/// PIN and the customer's phone are never printed.
class OrderSlips {
  OrderSlips({
    required this.orderNumber,
    required this.storeName,
    required this.kitchenTitle,
    required this.packageTitle,
    required this.placed,
    required this.readyBy,
    required this.lines,
    required this.itemsCount,
    required this.customer,
    required this.payment,
    required this.checkItems,
    required this.thanks,
    required this.rtl,
  });

  final String orderNumber;
  final String storeName;
  final String kitchenTitle;
  final String packageTitle;

  /// "Placed  14:05" and "Ready by  14:25" (empty when not accepted yet).
  final String placed;
  final String readyBy;
  final List<SlipLine> lines;
  final String itemsCount;

  /// "Customer: Zainab", or empty when the customer has no name.
  final String customer;

  /// Cash to collect, or paid in the app.
  final String payment;
  final String checkItems;
  final String thanks;
  final bool rtl;

  factory OrderSlips.of(Order order, S s, {required String storeName}) {
    String time(DateTime? at) {
      if (at == null) return '';
      final local = at.toLocal();
      return '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
    }

    String qty(OrderItem item) {
      final q = item.quantity == item.quantity.roundToDouble()
          ? item.quantity.round().toString()
          : item.quantity.toStringAsFixed(1);
      return item.soldByKg ? '$q ${s.t('kg')}' : '$q×';
    }

    final count = order.items.fold<int>(
      0,
      (sum, item) => sum + (item.soldByKg ? 1 : item.quantity.round()),
    );
    final name = order.customerName?.trim() ?? '';

    return OrderSlips(
      orderNumber: '#${order.id}',
      storeName: storeName,
      kitchenTitle: s.t('kitchenTicket'),
      packageTitle: s.t('packageSlip'),
      placed: '${s.t('placed')}  ${time(order.createdAt)}',
      readyBy: order.estimatedReadyAt == null
          ? ''
          : '${s.t('readyBy')}  ${time(order.estimatedReadyAt)}',
      lines: [
        for (final item in order.items)
          SlipLine(
            qty(item),
            item.name(s.lang),
            item.modifiers
                .map((m) => localizedName(s.lang, m['ar']!, m['ku']!, m['en']!))
                .join('، '),
          ),
      ],
      itemsCount: s.t('itemsCount', {'n': count}),
      customer: name.isEmpty ? '' : '${s.t('customer')}: $name',
      payment: order.paymentType == 'cod'
          ? s.t('collectCash', {'amount': s.money(order.total, order.currency)})
          : s.t('paidInApp'),
      checkItems: s.t('checkItems'),
      thanks: s.t('thanks', {'store': storeName}),
      rtl: s.lang != 'en',
    );
  }
}
