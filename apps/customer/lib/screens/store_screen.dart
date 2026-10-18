import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/cart.dart';
import '../widgets/cart_bar.dart';
import 'product_sheet.dart';

/// A store's menu, grouped by section.
class StoreScreen extends StatefulWidget {
  const StoreScreen({super.key, required this.storeId});
  final int storeId;

  @override
  State<StoreScreen> createState() => _StoreScreenState();
}

class _StoreScreenState extends State<StoreScreen> {
  late Future<VendorDetail> _store = context.read<ApiClient>().vendor(
    widget.storeId,
  );

  Future<void> _open(VendorDetail store, Product product) async {
    final line = await showModalBottomSheet<CartLine>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => ProductSheet(product: product),
    );
    if (line == null || !mounted) return;

    final cart = context.read<Cart>();
    if (cart.belongsToOtherStore(store.id)) {
      final s = S.read(context);
      final replace = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text(s.t('replaceCartTitle')),
          content: Text(s.t('replaceCartBody', {'store': cart.vendorName})),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: Text(s.t('cancel')),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: Text(s.t('replace')),
            ),
          ],
        ),
      );
      if (replace != true) return;
    }
    cart.add(store, line);
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    return Scaffold(
      backgroundColor: t.canvas,
      bottomNavigationBar: const CartBar(),
      body: FutureBuilder<VendorDetail>(
        future: _store,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Scaffold(
              appBar: AppBar(),
              body: Center(
                child: OutlinedButton(
                  onPressed: () => setState(
                    () => _store = context.read<ApiClient>().vendor(
                      widget.storeId,
                    ),
                  ),
                  child: Text(s.t('retry')),
                ),
              ),
            );
          }
          final store = snapshot.data;
          if (store == null) {
            return Scaffold(
              appBar: AppBar(),
              body: const Center(child: CircularProgressIndicator()),
            );
          }

          final sections = <String, List<Product>>{};
          for (final product in store.products) {
            sections.putIfAbsent(product.menuSection, () => []).add(product);
          }
          return CustomScrollView(
            slivers: [
              _StoreHero(store: store),
              for (final entry in sections.entries) ...[
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 24, 20, 10),
                    child: Row(
                      children: [
                        Transform.rotate(
                          angle: 0.785398,
                          child: Container(
                            width: 6,
                            height: 6,
                            color: Gold.c400,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            entry.key.isEmpty ? s.t('menu') : entry.key,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        Text(
                          '${entry.value.length}',
                          style: TextStyle(color: t.muted, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ),
                SliverToBoxAdapter(
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: t.surface,
                      borderRadius: BorderRadius.circular(Radii.lg),
                      border: Border.all(color: t.hairline),
                      boxShadow: t.raised,
                    ),
                    child: Column(
                      children: [
                        for (final (i, product) in entry.value.indexed) ...[
                          if (i > 0)
                            Divider(
                              height: 1,
                              indent: 18,
                              endIndent: 18,
                              color: t.hairline,
                            ),
                          Reveal(
                            index: i,
                            child: _ProductRow(
                              product: product,
                              enabled: store.isOpen && product.isAvailable,
                              onTap: () => _open(store, product),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
              const SliverToBoxAdapter(child: SizedBox(height: 32)),
            ],
          );
        },
      ),
    );
  }
}

/// Glazed header with the store's name and delivery facts; collapses to a
/// lapis bar with the name.
class _StoreHero extends StatelessWidget {
  const _StoreHero({required this.store});
  final VendorDetail store;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final top = MediaQuery.paddingOf(context).top;
    return SliverAppBar(
      pinned: true,
      expandedHeight: 250,
      backgroundColor: Lapis.c900,
      surfaceTintColor: Colors.transparent,
      foregroundColor: Colors.white,
      leading: Padding(
        padding: const EdgeInsets.all(8),
        child: Material(
          color: Colors.white.withValues(alpha: 0.12),
          shape: CircleBorder(
            side: BorderSide(color: Colors.white.withValues(alpha: 0.18)),
          ),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: () => Navigator.maybePop(context),
            child: Icon(
              Directionality.of(context) == TextDirection.rtl
                  ? Ph.arrowRight
                  : Ph.arrowLeft,
              size: 20,
            ),
          ),
        ),
      ),
      flexibleSpace: LayoutBuilder(
        builder: (context, box) {
          final collapsed = box.maxHeight < kToolbarHeight + top + 30;
          return Stack(
            fit: StackFit.expand,
            children: [
              GlazePanel(
                padding: EdgeInsets.fromLTRB(20, top + kToolbarHeight, 20, 20),
                child: AnimatedOpacity(
                  opacity: collapsed ? 0 : 1,
                  duration: Motion.fast,
                  child: ClipRect(
                    child: OverflowBox(
                      alignment: AlignmentDirectional.bottomStart,
                      maxHeight: double.infinity,
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  store.name,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 28,
                                    height: 1.25,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 10),
                                const GoldRule(width: 56),
                                const SizedBox(height: 14),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: [
                                    _HeroPill(
                                      icon: store.isOpen
                                          ? Ph.checkCircle
                                          : Ph.clock,
                                      text: s.t(
                                        store.isOpen ? 'open' : 'closed',
                                      ),
                                      gold: store.isOpen,
                                    ),
                                    if (store.cuisine.isNotEmpty)
                                      _HeroPill(
                                        icon: CuisineArt.iconFor(store.cuisine),
                                        text: s.t(store.cuisine),
                                      ),
                                    if (store.deliveryFee != null)
                                      _HeroPill(
                                        icon: Ph.moped,
                                        text: s.money(store.deliveryFee!),
                                      ),
                                    if (store.distanceKm != null)
                                      _HeroPill(
                                        icon: Ph.navigationArrow,
                                        text: s.t('km', {
                                          'km': store.distanceKm!
                                              .toStringAsFixed(1),
                                        }),
                                      ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 16),
                          Reveal(
                            index: 1,
                            child: Container(
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(Radii.lg),
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.18),
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: Lapis.c950.withValues(alpha: 0.4),
                                    blurRadius: 20,
                                    offset: const Offset(0, 10),
                                  ),
                                ],
                              ),
                              child: CuisineArt(
                                cuisine: store.cuisine,
                                type: store.type,
                                size: 78,
                                radius: Radii.lg,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Positioned(
                top: top,
                left: 56,
                right: 56,
                height: kToolbarHeight,
                child: AnimatedOpacity(
                  opacity: collapsed ? 1 : 0,
                  duration: Motion.fast,
                  child: Center(
                    child: Text(
                      store.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _HeroPill extends StatelessWidget {
  const _HeroPill({required this.icon, required this.text, this.gold = false});
  final IconData icon;
  final String text;
  final bool gold;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
      decoration: ShapeDecoration(
        color: Colors.white.withValues(alpha: 0.10),
        shape: StadiumBorder(
          side: BorderSide(color: Colors.white.withValues(alpha: 0.16)),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: gold ? Gold.c400 : Lapis.c200),
          const SizedBox(width: 6),
          Text(
            text,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _ProductRow extends StatelessWidget {
  const _ProductRow({
    required this.product,
    required this.enabled,
    required this.onTap,
  });
  final Product product;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      onTap: enabled ? onTap : null,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(18, 14, 14, 14),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.name(s.lang),
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: enabled ? t.ink : t.muted,
                    ),
                  ),
                  const SizedBox(height: 4),
                  if (product.isAvailable)
                    Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(
                            text: s.money(product.price),
                            style: TextStyle(
                              color: scheme.primary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          if (product.soldByKg)
                            TextSpan(
                              text: ' ${s.t('perKg')}',
                              style: TextStyle(color: t.muted),
                            ),
                        ],
                      ),
                      style: const TextStyle(fontSize: 14),
                    )
                  else
                    Text(
                      s.t('outOfStock'),
                      style: TextStyle(color: t.muted, fontSize: 14),
                    ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Tooltip(
              message: s.t('add'),
              child: Semantics(
                button: true,
                label: s.t('add'),
                child: AnimatedContainer(
                  duration: Motion.fast,
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: enabled ? scheme.primary : t.sunk,
                  ),
                  child: Icon(
                    Ph.plus,
                    size: 20,
                    color: enabled ? scheme.onPrimary : t.muted,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
