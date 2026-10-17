import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../l10n.dart';
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
    return Scaffold(
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
              SliverAppBar.large(
                title: Text(store.name),
                actions: [
                  if (!store.isOpen)
                    Padding(
                      padding: const EdgeInsetsDirectional.only(end: 16),
                      child: Chip(label: Text(s.t('closed'))),
                    ),
                ],
              ),
              for (final entry in sections.entries) ...[
                if (entry.key.isNotEmpty)
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
                      child: Text(
                        entry.key,
                        style: const TextStyle(
                          fontSize: 19,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                SliverList.list(
                  children: [
                    for (final product in entry.value)
                      _ProductRow(
                        product: product,
                        enabled: store.isOpen && product.isAvailable,
                        onTap: () => _open(store, product),
                      ),
                  ],
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
    return ListTile(
      enabled: enabled,
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
      title: Text(
        product.name(s.lang),
        style: const TextStyle(fontWeight: FontWeight.w600),
      ),
      subtitle: Text(
        product.isAvailable
            ? '${s.money(product.price)}${product.soldByKg ? ' ${s.t('perKg')}' : ''}'
            : s.t('outOfStock'),
      ),
      trailing: IconButton.filledTonal(
        tooltip: s.t('add'),
        onPressed: enabled ? onTap : null,
        icon: const Icon(Icons.add),
      ),
    );
  }
}
