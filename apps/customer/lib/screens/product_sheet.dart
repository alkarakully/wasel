import 'package:flutter/material.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/cart.dart';

/// Choose options and quantity, then add to the cart.
/// Required groups are pick-one; optional groups allow several.
class ProductSheet extends StatefulWidget {
  const ProductSheet({
    super.key,
    required this.product,
    this.currency = 'IQD',
    this.imageUrl,
  });
  final Product product;

  /// The product photo's full address, if it has one.
  final String? imageUrl;

  /// The store's currency.
  final String currency;

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
    final t = WaselTheme.of(context);
    final step = product.soldByKg ? 0.5 : 1.0;
    final quantityLabel = product.soldByKg
        ? '${_quantity.toStringAsFixed(1)} kg'
        : _quantity.round().toString();

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(22, 0, 22, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (widget.imageUrl != null) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(Radii.lg),
                child: AspectRatio(
                  aspectRatio: 16 / 10,
                  child: Image.network(
                    widget.imageUrl!,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => Container(color: t.sunk),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            Text(
              product.name(s.lang),
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.2,
              ),
            ),
            const SizedBox(height: 4),
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: s.money(product.price, widget.currency),
                    style: TextStyle(
                      color: scheme.primary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (product.soldByKg) TextSpan(text: ' ${s.t('perKg')}'),
                ],
              ),
              style: TextStyle(color: t.muted, fontSize: 16),
            ),
            if (product.description(s.lang).isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                product.description(s.lang),
                style: TextStyle(color: t.muted, fontSize: 15, height: 1.5),
              ),
            ],
            const SizedBox(height: 14),
            const GoldRule(width: 48),
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
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 2,
                              ),
                              decoration: ShapeDecoration(
                                color: _single.containsKey(entry.key)
                                    ? t.sunk
                                    : scheme.secondaryContainer,
                                shape: const StadiumBorder(),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  if (_single.containsKey(entry.key)) ...[
                                    Icon(Ph.check, size: 12, color: t.success),
                                    const SizedBox(width: 4),
                                  ],
                                  Text(
                                    s.t('required'),
                                    style: TextStyle(
                                      color: _single.containsKey(entry.key)
                                          ? t.muted
                                          : scheme.primary,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
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
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: ShapeDecoration(
                    color: t.sunk,
                    shape: StadiumBorder(side: BorderSide(color: t.hairline)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _StepButton(
                        icon: Ph.minus,
                        onPressed: _quantity > step
                            ? () => setState(() => _quantity -= step)
                            : null,
                      ),
                      SizedBox(
                        width: 64,
                        child: Text(
                          quantityLabel,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      _StepButton(
                        icon: Ph.plus,
                        onPressed: _quantity < 50
                            ? () => setState(() => _quantity += step)
                            : null,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            FilledButton(
              key: const Key('add-to-cart'),
              onPressed: _complete ? () => Navigator.pop(context, _line) : null,
              child: Text(
                s.t('addToCart', {
                  'price': s.money(_line.lineTotal, widget.currency),
                }),
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
          '+${s.money(modifier.priceDelta, widget.currency)}',
          style: const TextStyle(fontSize: 14),
        );
}

/// A round + or - inside the quantity pill.
class _StepButton extends StatelessWidget {
  const _StepButton({required this.icon, required this.onPressed});
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      enabled: onPressed != null,
      child: Pressable(
        onTap: onPressed,
        child: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: t.surface,
            boxShadow: onPressed == null ? null : t.raised,
          ),
          child: Icon(
            icon,
            size: 18,
            color: onPressed == null ? t.muted : scheme.primary,
          ),
        ),
      ),
    );
  }
}
