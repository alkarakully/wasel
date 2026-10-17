import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../l10n.dart';
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
  int _tip = 0;
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
      'tip': _tip,
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

    if (cart.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text(s.t('cart'))),
        body: Center(child: Text(s.t('emptyCart'))),
      );
    }

    final quote = _quote;
    return Scaffold(
      appBar: AppBar(title: Text(cart.vendorName)),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
        child: FilledButton(
          key: const Key('place-order'),
          onPressed: quote == null || _placing ? null : _place,
          child: Text(
            quote == null
                ? s.t('placeOrder', {'total': '...'})
                : s.t('placeOrder', {'total': s.money(quote.total)}),
          ),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          for (final line in cart.lines)
            _LineRow(line: line, onChange: _requote),
          const Divider(height: 32),
          if (quote != null) _Breakdown(quote: quote),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                s.t(_error!),
                style: TextStyle(
                  color: scheme.error,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          const SizedBox(height: 24),
          Text(
            s.t('address'),
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          TextField(
            key: const Key('address'),
            controller: _address,
            autocorrect: false,
            enableSuggestions: false,
            decoration: InputDecoration(hintText: s.t('addressHint')),
            textInputAction: TextInputAction.done,
          ),
          const SizedBox(height: 24),
          Text(s.t('tip'), style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              for (final amount in [0, 500, 1000, 2000])
                ChoiceChip(
                  label: Text(amount == 0 ? s.t('noTip') : s.money(amount)),
                  selected: _tip == amount,
                  showCheckmark: false,
                  onSelected: (_) {
                    setState(() => _tip = amount);
                    _requote();
                  },
                ),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            s.t('payment'),
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          RadioGroup<String>(
            groupValue: _payment,
            onChanged: (value) => setState(() => _payment = value!),
            child: Column(
              children: [
                RadioListTile(
                  contentPadding: EdgeInsets.zero,
                  value: 'cod',
                  title: Text(s.t('cash')),
                ),
                RadioListTile(
                  contentPadding: EdgeInsets.zero,
                  value: 'wallet',
                  title: Text(s.t('wallet')),
                ),
                RadioListTile(
                  contentPadding: EdgeInsets.zero,
                  value: 'card',
                  enabled: false,
                  title: Text(s.t('card')),
                ),
              ],
            ),
          ),
        ],
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
    final cart = context.read<Cart>();
    final step = line.product.soldByKg ? 0.5 : 1.0;
    final quantity = line.product.soldByKg
        ? '${line.quantity.toStringAsFixed(1)} kg'
        : '${line.quantity.round()}';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
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
                    style: TextStyle(
                      fontSize: 13,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                Text(s.money(line.lineTotal)),
              ],
            ),
          ),
          IconButton(
            onPressed: () {
              cart.changeQuantity(line, -step);
              onChange();
            },
            icon: const Icon(Icons.remove_circle_outline),
          ),
          Text(quantity, style: const TextStyle(fontWeight: FontWeight.w600)),
          IconButton(
            onPressed: () {
              cart.changeQuantity(line, step);
              onChange();
            },
            icon: const Icon(Icons.add_circle_outline),
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
        row(s.t('subtotal'), s.money(quote.subtotal)),
        row(
          quote.waselPlus
              ? '${s.t('delivery')} (${s.t('waselPlus')})'
              : s.t('delivery'),
          quote.deliveryFee == 0 ? s.t('free') : s.money(quote.deliveryFee),
        ),
        row(s.t('serviceFee'), s.money(quote.serviceFee)),
        if (quote.discount > 0) row(s.t('discount'), s.money(-quote.discount)),
        if (quote.tip > 0) row(s.t('tip'), s.money(quote.tip)),
        const Divider(),
        row(s.t('total'), s.money(quote.total), bold: true),
      ],
    );
  }
}
