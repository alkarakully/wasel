import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../l10n.dart';
import '../state/session.dart';
import '../widgets/cart_bar.dart';
import '../widgets/language_switch.dart';
import 'orders_screen.dart';
import 'store_screen.dart';

const cuisines = [
  'popular',
  'eastern',
  'western',
  'fast_food',
  'sweets',
  'drinks',
];

/// Stores that deliver to the customer's spot, open ones first.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String? _cuisine;
  Future<(List<Vendor>, List<Offer>)>? _load;
  GeoPoint? _loadedFor;

  void _reload() {
    final session = context.read<Session>();
    final api = context.read<ApiClient>();
    _loadedFor = session.deliveryPoint;
    _load = (() async {
      final results = await Future.wait([
        api.vendors(at: session.deliveryPoint, cuisine: _cuisine),
        api.bannerOffers(),
      ]);
      return (results[0] as List<Vendor>, results[1] as List<Offer>);
    })();
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final session = context.watch<Session>();
    // Reload when the phone's location arrives after the first load.
    if (_load == null || _loadedFor != session.deliveryPoint) _reload();

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 20,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              s.t('deliverTo'),
              style: TextStyle(
                fontSize: 13,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            Text(
              session.usingDeviceLocation
                  ? s.t('currentLocation')
                  : s.t('baghdad'),
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: s.t('myOrders'),
            icon: const Icon(Icons.receipt_long_outlined),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const OrdersScreen()),
            ),
          ),
          PopupMenuButton<String>(
            icon: const Icon(Icons.person_outline),
            onSelected: (value) => value == 'logout' ? session.signOut() : null,
            itemBuilder: (_) => [
              PopupMenuItem(
                enabled: false,
                child: Text(
                  session.user?.phone ?? '',
                  textDirection: TextDirection.ltr,
                ),
              ),
              const PopupMenuItem(enabled: false, child: LanguageSwitch()),
              PopupMenuItem(value: 'logout', child: Text(s.t('logout'))),
            ],
          ),
          const SizedBox(width: 8),
        ],
      ),
      bottomNavigationBar: const CartBar(),
      body: RefreshIndicator(
        onRefresh: () async {
          setState(_reload);
          await _load;
        },
        child: FutureBuilder(
          future: _load,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return _Message(
                text: s.t('err_network'),
                onRetry: () => setState(_reload),
              );
            }
            final data = snapshot.data;
            return ListView(
              padding: const EdgeInsets.only(bottom: 24),
              children: [
                if (data != null && data.$2.isNotEmpty)
                  _OfferBanners(offers: data.$2),
                _CuisineChips(
                  selected: _cuisine,
                  onSelected: (value) => setState(() {
                    _cuisine = value;
                    _reload();
                  }),
                ),
                if (data == null)
                  for (var i = 0; i < 4; i++) const _StoreSkeleton()
                else if (data.$1.isEmpty)
                  _Message(text: s.t('noStores'))
                else
                  for (final store in data.$1) _StoreCard(store: store),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _OfferBanners extends StatelessWidget {
  const _OfferBanners({required this.offers});
  final List<Offer> offers;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      height: 112,
      child: PageView(
        controller: PageController(viewportFraction: 0.88),
        padEnds: false,
        children: [
          for (final offer in offers)
            Container(
              margin: const EdgeInsetsDirectional.only(
                start: 16,
                top: 8,
                bottom: 8,
              ),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: scheme.primary,
                borderRadius: BorderRadius.circular(16),
              ),
              alignment: AlignmentDirectional.centerStart,
              child: Text(
                offer.title,
                style: TextStyle(
                  color: scheme.onPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _CuisineChips extends StatelessWidget {
  const _CuisineChips({required this.selected, required this.onSelected});
  final String? selected;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return SizedBox(
      height: 56,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        children: [
          for (final cuisine in [null, ...cuisines])
            Padding(
              padding: const EdgeInsetsDirectional.only(end: 8),
              child: ChoiceChip(
                label: Text(
                  s.t(cuisine ?? 'all'),
                  // Keep two-word labels like الأكثر طلباً on one line.
                  maxLines: 1,
                  softWrap: false,
                ),
                selected: selected == cuisine,
                showCheckmark: false,
                onSelected: (_) => onSelected(cuisine),
              ),
            ),
        ],
      ),
    );
  }
}

class _StoreCard extends StatelessWidget {
  const _StoreCard({required this.store});
  final Vendor store;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final scheme = Theme.of(context).colorScheme;
    final muted = TextStyle(color: scheme.onSurfaceVariant, fontSize: 14);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 6),
      child: Opacity(
        opacity: store.isOpen ? 1 : 0.6,
        child: Card(
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => StoreScreen(storeId: store.id)),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: scheme.primaryContainer,
                    child: Text(
                      store.name.characters.first,
                      style: TextStyle(
                        fontSize: 22,
                        color: scheme.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                store.name,
                                style: const TextStyle(
                                  fontSize: 17,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            _OpenBadge(open: store.isOpen),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          [
                            if (store.cuisine.isNotEmpty) s.t(store.cuisine),
                            if (store.deliveryFee != null)
                              s.t('deliveryFee', {
                                'fee': s.money(store.deliveryFee!),
                              }),
                            if (store.distanceKm != null)
                              s.t('km', {
                                'km': store.distanceKm!.toStringAsFixed(1),
                              }),
                          ].join(' · '),
                          style: muted,
                        ),
                      ],
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

class _OpenBadge extends StatelessWidget {
  const _OpenBadge({required this.open});
  final bool open;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
      decoration: BoxDecoration(
        color: open ? scheme.primaryContainer : scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        S.of(context).t(open ? 'open' : 'closed'),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: open ? scheme.primary : scheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _StoreSkeleton extends StatelessWidget {
  const _StoreSkeleton();

  @override
  Widget build(BuildContext context) {
    final bone = Theme.of(context).colorScheme.outline;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 6),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(radius: 26, backgroundColor: bone),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(height: 14, width: 140, color: bone),
                    const SizedBox(height: 10),
                    Container(height: 12, width: 200, color: bone),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.text, this.onRetry});
  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        children: [
          Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16),
          ),
          if (onRetry != null) ...[
            const SizedBox(height: 16),
            OutlinedButton(
              onPressed: onRetry,
              child: Text(S.of(context).t('retry')),
            ),
          ],
        ],
      ),
    );
  }
}
