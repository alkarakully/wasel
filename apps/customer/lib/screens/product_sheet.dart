import 'package:flutter/material.dart';

import '../api/models.dart';
import '../l10n.dart';
import '../state/cart.dart';

/// Choose options and quantity, then add to the cart.
/// Required groups are pick-one; optional groups allow several.
class ProductSheet extends StatefulWidget {
  const ProductSheet({super.key, required this.product});
  final Product product;

  @override
  State<ProductSheet> createState() => _ProductSheetState();
}

class _ProductSheetState extends State<ProductSheet> {
  late final Map<String, List<Modifier>> _groups =
      widget.product.modifierGroups;
  final Map<String, Modifier> _single = {}; // required group -> choice
  final Set<Modifier> _extras = {};
  double _quantity = 1;

  bool _required(String group) => _groups[group]!.any((m) => m.isRequired);

  bool get _complete =>
      _groups.keys.where(_required).every(_single.containsKey);

  CartLine get _line => CartLine(
    product: widget.product,
    quantity: _quantity,
    modifiers: [..._single.values, ..._extras],
  );

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final product = widget.product;
    final scheme = Theme.of(context).colorScheme;
    final step = product.soldByKg ? 0.5 : 1.0;
    final quantityLabel = product.soldByKg
        ? '${_quantity.toStringAsFixed(1)} kg'
        : _quantity.round().toString();

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              product.name(s.lang),
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            ),
            Text(
              '${s.money(product.price)}${product.soldByKg ? ' ${s.t('perKg')}' : ''}',
              style: TextStyle(color: scheme.onSurfaceVariant),
            ),
            Flexible(
              child: ListView(
                shrinkWrap: true,
                children: [
                  for (final entry in _groups.entries) ...[
                    Padding(
                      padding: const EdgeInsets.only(top: 18, bottom: 4),
                      child: Row(
                        children: [
                          Text(
                            entry.key,
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          if (_required(entry.key)) ...[
                            const SizedBox(width: 8),
                            Text(
                              s.t('required'),
                              style: TextStyle(
                                color: scheme.primary,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (_required(entry.key))
                      RadioGroup<Modifier>(
                        groupValue: _single[entry.key],
                        onChanged: (value) =>
                            setState(() => _single[entry.key] = value!),
                        child: Column(
                          children: [
                            for (final modifier in entry.value)
                              RadioListTile<Modifier>(
                                contentPadding: EdgeInsets.zero,
                                value: modifier,
                                title: Text(modifier.name(s.lang)),
                                secondary: _price(s, modifier),
                              ),
                          ],
                        ),
                      )
                    else
                      for (final modifier in entry.value)
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          controlAffinity: ListTileControlAffinity.leading,
                          value: _extras.contains(modifier),
                          onChanged: (on) => setState(
                            () => on!
                                ? _extras.add(modifier)
                                : _extras.remove(modifier),
                          ),
                          title: Text(modifier.name(s.lang)),
                          secondary: _price(s, modifier),
                        ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Text(
                  s.t('quantity'),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                IconButton.outlined(
                  onPressed: _quantity > step
                      ? () => setState(() => _quantity -= step)
                      : null,
                  icon: const Icon(Icons.remove),
                ),
                SizedBox(
                  width: 72,
                  child: Text(
                    quantityLabel,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                IconButton.outlined(
                  onPressed: _quantity < 50
                      ? () => setState(() => _quantity += step)
                      : null,
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
            const SizedBox(height: 16),
            FilledButton(
              key: const Key('add-to-cart'),
              onPressed: _complete ? () => Navigator.pop(context, _line) : null,
              child: Text(
                s.t('addToCart', {'price': s.money(_line.lineTotal)}),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget? _price(S s, Modifier modifier) => modifier.priceDelta == 0
      ? null
      : Text(
          '+${s.money(modifier.priceDelta)}',
          style: const TextStyle(fontSize: 14),
        );
}
