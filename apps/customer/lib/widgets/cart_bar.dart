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
    final reduce = MediaQuery.of(context).disableAnimations;
    return AnimatedSwitcher(
      duration: reduce ? Duration.zero : Motion.medium,
      switchInCurve: Motion.spring,
      switchOutCurve: Motion.out,
      transitionBuilder: (child, animation) => SlideTransition(
        position: Tween(
          begin: const Offset(0, 1),
          end: Offset.zero,
        ).animate(animation),
        child: FadeTransition(opacity: animation, child: child),
      ),
      child: cart.isEmpty
          ? const SizedBox.shrink(key: ValueKey('empty'))
          : _bar(context, cart, reduce),
    );
  }

  Widget _bar(BuildContext context, Cart cart, bool reduce) {
    final s = S.of(context);
    return SafeArea(
      key: const ValueKey('bar'),
      minimum: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      child: Semantics(
        button: true,
        child: Pressable(
          key: const Key('view-cart'),
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const CartScreen()),
          ),
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(100),
              boxShadow: [
                BoxShadow(
                  color: Lapis.c900.withValues(alpha: 0.35),
                  blurRadius: 24,
                  spreadRadius: -8,
                  offset: const Offset(0, 12),
                ),
              ],
            ),
            child: GlazePanel(
              radius: 100,
              padding: const EdgeInsetsDirectional.fromSTEB(8, 8, 22, 8),
              child: Row(
                children: [
                  TweenAnimationBuilder<double>(
                    key: ValueKey(cart.itemCount),
                    tween: Tween(begin: reduce ? 1 : 1.3, end: 1),
                    duration: Motion.medium,
                    curve: Motion.spring,
                    builder: (context, scale, child) =>
                        Transform.scale(scale: scale, child: child),
                    child: Container(
                      width: 42,
                      height: 42,
                      alignment: Alignment.center,
                      decoration: const BoxDecoration(
                        color: Gold.c400,
                        shape: BoxShape.circle,
                      ),
                      child: Text(
                        '${cart.itemCount}',
                        style: const TextStyle(
                          color: Lapis.c950,
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      s.t('cart'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Text(
                    s.money(cart.subtotal),
                    style: const TextStyle(
                      color: Gold.c300,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
