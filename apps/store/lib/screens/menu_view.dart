import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/board.dart';

/// Every item with an in-stock switch. Out-of-stock items can't be ordered.
class MenuView extends StatelessWidget {
  const MenuView({super.key});

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final board = context.watch<StoreBoard>();
    final store = board.store;
    if (store == null) return const Center(child: CircularProgressIndicator());

    final sections = <String, List<Product>>{};
    for (final product in store.products) {
      sections.putIfAbsent(product.menuSection, () => []).add(product);
    }

    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 820),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            for (final entry in sections.entries) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(6, 22, 6, 10),
                child: Row(
                  children: [
                    Transform.rotate(
                      angle: 0.785398,
                      child: Container(width: 7, height: 7, color: Gold.c400),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      entry.key.isEmpty ? s.t('menu') : entry.key,
                      style: const TextStyle(
                        fontSize: 19,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                decoration: BoxDecoration(
                  color: t.surface,
                  borderRadius: BorderRadius.circular(Radii.lg),
                  border: Border.all(color: t.hairline),
                  boxShadow: t.raised,
                ),
                clipBehavior: Clip.antiAlias,
                child: Column(
                  children: [
                    for (final (i, product) in entry.value.indexed) ...[
                      if (i > 0) Divider(height: 1, color: t.hairline),
                      AnimatedContainer(
                        duration: Motion.fast,
                        color: board.isAvailable(product)
                            ? Colors.transparent
                            : t.sunk,
                        padding: const EdgeInsets.fromLTRB(18, 10, 12, 10),
                        child: Row(
                          children: [
                            Expanded(
                              child: Text(
                                product.name(s.lang),
                                style: TextStyle(
                                  fontSize: 17,
                                  fontWeight: FontWeight.w600,
                                  color: board.isAvailable(product)
                                      ? t.ink
                                      : t.muted,
                                  decoration: board.isAvailable(product)
                                      ? null
                                      : TextDecoration.lineThrough,
                                ),
                              ),
                            ),
                            Text(
                              s.money(product.price, store.currency),
                              style: TextStyle(
                                fontWeight: FontWeight.w600,
                                color: scheme.primary,
                              ),
                            ),
                            const SizedBox(width: 18),
                            SizedBox(
                              width: 96,
                              child: Text(
                                s.t(
                                  board.isAvailable(product)
                                      ? 'available'
                                      : 'outOfStock',
                                ),
                                textAlign: TextAlign.end,
                                style: TextStyle(
                                  fontWeight: FontWeight.w600,
                                  color: board.isAvailable(product)
                                      ? t.success
                                      : t.muted,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Switch(
                              key: Key('stock-${product.id}'),
                              value: board.isAvailable(product),
                              onChanged: (on) {
                                HapticFeedback.selectionClick();
                                board.setAvailable(product, on);
                              },
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
