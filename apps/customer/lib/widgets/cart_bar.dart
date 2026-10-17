import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../screens/cart_screen.dart';
import '../state/cart.dart';

/// "View cart" button pinned to the bottom while the cart has items.
class CartBar extends StatelessWidget {
  const CartBar({super.key});

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<Cart>();
    if (cart.isEmpty) return const SizedBox.shrink();
    final s = S.of(context);
    return SafeArea(
      minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      child: FilledButton(
        key: const Key('view-cart'),
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const CartScreen()),
        ),
        child: Row(
          children: [
            Text(s.t('viewCart', {'count': cart.itemCount})),
            const Spacer(),
            Text(s.money(cart.subtotal)),
          ],
        ),
      ),
    );
  }
}
