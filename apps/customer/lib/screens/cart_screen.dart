import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/cart.dart';
import '../state/session.dart';
import 'tracking_screen.dart';

/// Cart, full price breakdown from the server, and checkout.
class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  final _address = TextEditingController();
  String _payment = 'cod';
  num _tip = 0;
  Quote? _quote;
  String? _error;
  bool _placing = false;
  Timer? _debounce;
  int _quoteRequest = 0;

  @override
  void initState() {
    super.initState();
    _requote();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _address.dispose();
    super.dispose();
  }

  Map<String, dynamic> _cartBody() {
    final cart = context.read<Cart>();
    final at = context.read<Session>().deliveryPoint;
    return {
      'vendor': cart.vendorId,
      'items': cart.itemsJson(),
      'delivery_latitude': at.lat,
      'delivery_longitude': at.lng,
      'tip': _tip.toString(),
    };
  }

  /// Ask the server for the real price; wait a moment after quick taps.
  void _requote() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () async {
      final cart = context.read<Cart>();
      if (cart.isEmpty) return;
      final request = ++_quoteRequest;
      try {
        final quote = await context.read<ApiClient>().quote(_cartBody());
        if (mounted && request == _quoteRequest) {
          setState(() {
            _quote = quote;
            _error = null;
          });
        }
      } on ApiException catch (error) {
        if (mounted && request == _quoteRequest) {
          setState(() {
            _quote = null;
            _error = 'err_${error.code}';
          });
        }
      }
    });
  }

  Future<void> _place() async {
    if (_address.text.trim().isEmpty) {
      setState(() => _error = 'addressRequired');
      return;
    }
    setState(() {
      _placing = true;
      _error = null;
    });
    try {
      final order = await context.read<ApiClient>().placeOrder({
        ..._cartBody(),
        'delivery_address': _address.text.trim(),
        'payment_type': _payment,
      });
      if (!mounted) return;
      context.read<Cart>().clear();
      Navigator.of(context)
        ..popUntil((route) => route.isFirst)
        ..push(
          MaterialPageRoute(builder: (_) => TrackingScreen(orderId: order.id)),
        );
    } on ApiException catch (error) {
      setState(() => _error = 'err_${error.code}');
    } finally {
      if (mounted) setState(() => _placing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final cart = context.watch<Cart>();
    final scheme = Theme.of(context).colorScheme;
    final t = WaselTheme.of(context);

    if (cart.isEmpty) {
      return Scaffold(
        backgroundColor: t.canvas,
        appBar: AppBar(title: Text(s.t('cart'))),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: t.sunk,
                  shape: BoxShape.circle,
                ),
                child: Icon(Ph.shoppingBag, size: 32, color: t.muted),
              ),
              const SizedBox(height: 16),
              Text(s.t('emptyCart'), style: TextStyle(color: t.muted)),
            ],
          ),
        ),
      );
    }

    final quote = _quote;
    return Scaffold(
      backgroundColor: t.canvas,
      appBar: AppBar(
        backgroundColor: t.canvas,
        title: Text(
          cart.vendorName,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: PillButton(
          key: const Key('place-order'),
          busy: _placing,
          onPressed: quote == null ? null : _place,
          label: quote == null
              ? s.t('placeOrder', {'total': '...'})
              : s.t('placeOrder', {
                  'total': s.money(quote.total, quote.currency),
                }),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          _Section(
            child: Column(
              children: [
                for (final (i, line) in cart.lines.indexed) ...[
                  if (i > 0) Divider(height: 1, color: t.hairline),
                  _LineRow(line: line, onChange: _requote),
                ],
              ],
            ),
          ),
          _Section(
            title: s.t('address'),
            icon: Ph.mapPin,
            child: TextField(
              key: const Key('address'),
              controller: _address,
              autocorrect: false,
              enableSuggestions: false,
              decoration: InputDecoration(hintText: s.t('addressHint')),
              textInputAction: TextInputAction.done,
            ),
          ),
          _Section(
            title: s.t('tip'),
            icon: Ph.moped,
            child: Row(
              children: [
                // Tip choices in the store's currency.
                for (final (i, amount) in <num>[
                  0,
                  ...regionForCurrency(cart.currency).tips,
                ].indexed) ...[
                  if (i > 0) const SizedBox(width: 8),
                  Expanded(
                    child: _Choice(
                      selected: _tip == amount,
                      onTap: () {
                        setState(() => _tip = amount);
                        _requote();
                      },
                      compact: true,
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          amount == 0
                              ? s.t('noTip')
                              : s.money(amount, cart.currency),
                          maxLines: 1,
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          _Section(
            title: s.t('payment'),
            icon: Ph.wallet,
            child: Column(
              children: [
                for (final (value, icon) in [
                  ('cod', Ph.money),
                  ('wallet', Ph.wallet),
                  ('card', Ph.creditCard),
                ]) ...[
                  _Choice(
                    selected: _payment == value,
                    onTap: value == 'card'
                        ? null
                        : () => setState(() => _payment = value),
                    child: Row(
                      children: [
                        Icon(icon, size: 22),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(s.t(value == 'cod' ? 'cash' : value)),
                        ),
                        if (_payment == value)
                          Icon(Ph.checkCircle, color: scheme.primary),
                      ],
                    ),
                  ),
                  if (value != 'card') const SizedBox(height: 8),
                ],
              ],
            ),
          ),
          if (quote != null) BezelCard(child: _Breakdown(quote: quote)),
          if (_error != null)
            Container(
              margin: const EdgeInsets.only(top: 12),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: scheme.errorContainer,
                borderRadius: BorderRadius.circular(Radii.md),
              ),
              child: Row(
                children: [
                  Icon(Ph.warningCircle, color: scheme.error),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      s.t(_error!),
                      style: TextStyle(
                        color: scheme.onErrorContainer,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// A titled white card on the canvas.
class _Section extends StatelessWidget {
  const _Section({required this.child, this.title, this.icon});
  final Widget child;
  final String? title;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: title == null
          ? const EdgeInsets.symmetric(horizontal: 16, vertical: 4)
          : const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: t.surface,
        borderRadius: BorderRadius.circular(Radii.lg),
        border: Border.all(color: t.hairline),
        boxShadow: t.raised,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (title != null) ...[
            Row(
              children: [
                if (icon != null) ...[
                  Icon(icon, size: 20, color: t.muted),
                  const SizedBox(width: 8),
                ],
                Text(
                  title!,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 12),
          ],
          child,
        ],
      ),
    );
  }
}

/// A selectable tile: tinted with a lapis edge when chosen.
class _Choice extends StatelessWidget {
  const _Choice({
    required this.selected,
    required this.child,
    this.onTap,
    this.compact = false,
  });
  final bool selected;
  final bool compact;
  final Widget child;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      selected: selected,
      enabled: onTap != null,
      child: Pressable(
        onTap: onTap,
        child: Opacity(
          opacity: onTap == null ? 0.5 : 1,
          child: AnimatedContainer(
            duration: Motion.fast,
            curve: Motion.out,
            constraints: const BoxConstraints(minHeight: 48),
            padding: EdgeInsets.symmetric(
              horizontal: compact ? 6 : 14,
              vertical: 12,
            ),
            alignment: AlignmentDirectional.center,
            decoration: BoxDecoration(
              color: selected ? scheme.secondaryContainer : t.sunk,
              borderRadius: BorderRadius.circular(Radii.md),
              border: Border.all(
                color: selected ? scheme.primary : t.hairline,
                width: selected ? 1.5 : 1,
              ),
            ),
            child: DefaultTextStyle.merge(
              style: TextStyle(
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                color: selected ? scheme.primary : t.ink,
              ),
              child: IconTheme.merge(
                data: IconThemeData(color: selected ? scheme.primary : t.muted),
                child: child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LineRow extends StatelessWidget {
  const _LineRow({required this.line, required this.onChange});
  final CartLine line;
  final VoidCallback onChange;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final cart = context.read<Cart>();
    final step = line.product.soldByKg ? 0.5 : 1.0;
    final quantity = line.product.soldByKg
        ? '${line.quantity.toStringAsFixed(1)} kg'
        : '${line.quantity.round()}';
    Widget stepButton(IconData icon, double delta) => Semantics(
      button: true,
      child: Pressable(
        onTap: () {
          cart.changeQuantity(line, delta);
          onChange();
        },
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: t.surface,
            shape: BoxShape.circle,
            boxShadow: t.raised,
          ),
          child: Icon(icon, size: 16, color: scheme.primary),
        ),
      ),
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  line.product.name(s.lang),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                if (line.modifiers.isNotEmpty)
                  Text(
                    line.modifiers.map((m) => m.name(s.lang)).join('، '),
                    style: TextStyle(fontSize: 13, color: t.muted),
                  ),
                const SizedBox(height: 2),
                Text(
                  s.money(line.lineTotal, cart.currency),
                  style: TextStyle(
                    color: scheme.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.all(3),
            decoration: ShapeDecoration(
              color: t.sunk,
              shape: StadiumBorder(side: BorderSide(color: t.hairline)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                stepButton(Ph.minus, -step),
                SizedBox(
                  width: 44,
                  child: Text(
                    quantity,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                stepButton(Ph.plus, step),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Breakdown extends StatelessWidget {
  const _Breakdown({required this.quote});
  final Quote quote;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    Widget row(String label, String value, {bool bold = false}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Text(
            label,
            style: TextStyle(
              fontWeight: bold ? FontWeight.w700 : null,
              fontSize: bold ? 17 : null,
            ),
          ),
          const Spacer(),
          Text(
            value,
            style: TextStyle(
              fontWeight: bold ? FontWeight.w700 : null,
              fontSize: bold ? 17 : null,
            ),
          ),
        ],
      ),
    );
    return Column(
      children: [
        row(s.t('subtotal'), s.money(quote.subtotal, quote.currency)),
        row(
          quote.waselPlus
              ? '${s.t('delivery')} (${s.t('waselPlus')})'
              : s.t('delivery'),
          quote.deliveryFee == 0
              ? s.t('free')
              : s.money(quote.deliveryFee, quote.currency),
        ),
        row(s.t('serviceFee'), s.money(quote.serviceFee, quote.currency)),
        if (quote.discount > 0)
          row(s.t('discount'), s.money(-quote.discount, quote.currency)),
        if (quote.tip > 0) row(s.t('tip'), s.money(quote.tip, quote.currency)),
        const SizedBox(height: 8),
        const Divider(height: 1),
        const SizedBox(height: 8),
        row(s.t('total'), s.money(quote.total, quote.currency), bold: true),
      ],
    );
  }
}
