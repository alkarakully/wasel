import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/session.dart';
import '../widgets/cart_bar.dart';
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
    final t = WaselTheme.of(context);
    final session = context.watch<Session>();
    // Reload when the phone's location arrives after the first load.
    if (_load == null || _loadedFor != session.deliveryPoint) _reload();

    return Scaffold(
      backgroundColor: t.canvas,
      bottomNavigationBar: const CartBar(),
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          onRefresh: () async {
            setState(_reload);
            await _load;
          },
          child: FutureBuilder(
            future: _load,
            builder: (context, snapshot) {
              final data = snapshot.data;
              return ListView(
                padding: const EdgeInsets.only(bottom: 28),
                children: [
                  _Header(session: session),
                  if (snapshot.hasError)
                    _Message(
                      text: s.t('err_network'),
                      onRetry: () => setState(_reload),
                    )
                  else ...[
                    _OfferBanners(offers: data?.$2 ?? const []),
                    _SectionTitle(s.t('craving')),
                    _CuisineRail(
                      selected: _cuisine,
                      onSelected: (value) => setState(() {
                        _cuisine = value;
                        _reload();
                      }),
                    ),
                    _SectionTitle(s.t('nearbyStores')),
                    if (data == null)
                      for (var i = 0; i < 4; i++) const _StoreSkeleton()
                    else if (data.$1.isEmpty)
                      _Message(text: s.t('noStores'))
                    else
                      for (final store in data.$1) _StoreCard(store: store),
                  ],
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

/// Where we deliver, plus orders and account.
class _Header extends StatelessWidget {
  const _Header({required this.session});
  final Session session;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 12, 8),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: scheme.secondaryContainer,
              shape: BoxShape.circle,
            ),
            child: Icon(Ph.mapPin, color: scheme.primary, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  s.t('deliverTo'),
                  style: TextStyle(fontSize: 13, color: t.muted),
                ),
                Text(
                  session.usingDeviceLocation
                      ? s.t('currentLocation')
                      : s.t('baghdad'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          _RoundButton(
            tooltip: s.t('myOrders'),
            icon: Ph.receipt,
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const OrdersScreen()),
            ),
          ),
          const SizedBox(width: 8),
          PopupMenuButton<String>(
            tooltip: '',
            position: PopupMenuPosition.under,
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
              PopupMenuItem(
                value: 'logout',
                child: Row(
                  children: [
                    const Icon(Ph.signOut, size: 20),
                    const SizedBox(width: 10),
                    Text(s.t('logout')),
                  ],
                ),
              ),
            ],
            child: const _RoundButton(icon: Ph.user),
          ),
        ],
      ),
    );
  }
}

class _RoundButton extends StatelessWidget {
  const _RoundButton({required this.icon, this.onPressed, this.tooltip});
  final IconData icon;
  final VoidCallback? onPressed;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final body = Container(
      width: 44,
      height: 44,
      decoration: BoxDecoration(
        color: t.surface,
        shape: BoxShape.circle,
        border: Border.all(color: t.hairline),
        boxShadow: t.raised,
      ),
      child: Icon(icon, size: 22, color: t.ink),
    );
    if (onPressed == null) return body;
    return Tooltip(
      message: tooltip ?? '',
      child: Pressable(onTap: onPressed, child: body),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(20, 22, 20, 12),
    child: Text(
      text,
      style: const TextStyle(
        fontSize: 19,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
      ),
    ),
  );
}

/// Offers on glazed lapis; without offers, the brand line takes the spot.
class _OfferBanners extends StatelessWidget {
  const _OfferBanners({required this.offers});
  final List<Offer> offers;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final single = offers.length <= 1;
    final items = offers.isEmpty
        ? [_Banner(eyebrow: null, title: s.t('brandLine'), icon: Ph.moped)]
        : [
            for (final (i, offer) in offers.indexed)
              _Banner(
                eyebrow: s.t('offerTag'),
                title: offer.title,
                icon: const [Ph.sparkle, Ph.moped, Ph.star][i % 3],
              ),
          ];
    return SizedBox(
      height: 168,
      child: PageView(
        controller: PageController(viewportFraction: single ? 1 : 0.86),
        padEnds: false,
        children: [
          for (final (i, item) in items.indexed)
            Padding(
              padding: EdgeInsetsDirectional.only(
                start: i == 0 ? 16 : 6,
                end: single || i == items.length - 1 ? 16 : 6,
                top: 8,
              ),
              child: item,
            ),
        ],
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({
    required this.eyebrow,
    required this.title,
    required this.icon,
  });
  final String? eyebrow;
  final String title;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(Radii.lg),
        boxShadow: [
          BoxShadow(
            color: Lapis.c900.withValues(alpha: 0.28),
            blurRadius: 24,
            spreadRadius: -10,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: GlazePanel(
        radius: Radii.lg,
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 20),
        child: Stack(
          children: [
            PositionedDirectional(
              end: -28,
              bottom: -34,
              child: Icon(
                icon,
                size: 132,
                color: Gold.c400.withValues(alpha: 0.12),
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (eyebrow != null) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 3,
                    ),
                    decoration: const ShapeDecoration(
                      color: Gold.c400,
                      shape: StadiumBorder(),
                    ),
                    child: Text(
                      eyebrow!,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: Lapis.c950,
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                ] else ...[
                  const Wordmark(size: 30),
                  const SizedBox(height: 4),
                ],
                FractionallySizedBox(
                  widthFactor: 0.78,
                  alignment: AlignmentDirectional.centerStart,
                  child: Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: eyebrow == null ? 16 : 22,
                      height: 1.35,
                      fontWeight: eyebrow == null
                          ? FontWeight.w500
                          : FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                const GoldRule(width: 48),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Cuisine picker: an icon tile per cuisine, the chosen one glazed.
class _CuisineRail extends StatelessWidget {
  const _CuisineRail({required this.selected, required this.onSelected});
  final String? selected;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      height: 98,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        children: [
          for (final cuisine in [null, ...cuisines])
            Semantics(
              button: true,
              selected: selected == cuisine,
              child: Pressable(
                onTap: () => onSelected(cuisine),
                child: SizedBox(
                  width: 78,
                  child: Column(
                    children: [
                      AnimatedContainer(
                        duration: Motion.medium,
                        curve: Motion.spring,
                        width: 60,
                        height: 60,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(Radii.md + 4),
                          gradient: selected == cuisine
                              ? GlazePanel.gradient
                              : null,
                          color: selected == cuisine ? null : t.surface,
                          border: Border.all(
                            color: selected == cuisine
                                ? Colors.transparent
                                : t.hairline,
                          ),
                          boxShadow: selected == cuisine
                              ? t.floating
                              : t.raised,
                        ),
                        child: Icon(
                          cuisine == null
                              ? Ph.forkKnife
                              : CuisineArt.iconFor(cuisine),
                          size: 28,
                          color: selected == cuisine
                              ? Gold.c400
                              : scheme.primary,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        s.t(cuisine ?? 'all'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: selected == cuisine
                              ? FontWeight.w700
                              : FontWeight.w500,
                          color: selected == cuisine ? t.ink : t.muted,
                        ),
                      ),
                    ],
                  ),
                ),
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
    final t = WaselTheme.of(context);
    final meta = TextStyle(color: t.muted, fontSize: 13);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 5, 16, 5),
      child: Opacity(
        opacity: store.isOpen ? 1 : 0.55,
        child: Pressable(
          scale: 0.98,
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => StoreScreen(storeId: store.id)),
          ),
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: t.surface,
              borderRadius: BorderRadius.circular(Radii.lg),
              border: Border.all(color: t.hairline),
              boxShadow: t.raised,
            ),
            child: Row(
              children: [
                CuisineArt(
                  cuisine: store.cuisine,
                  type: store.type,
                  size: 76,
                  radius: Radii.md,
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
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          _OpenBadge(open: store.isOpen),
                        ],
                      ),
                      if (store.cuisine.isNotEmpty)
                        Text(s.t(store.cuisine), style: meta),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 14,
                        runSpacing: 4,
                        children: [
                          if (store.deliveryFee != null)
                            _Meta(
                              icon: Ph.moped,
                              text: s.t('deliveryFee', {
                                'fee': s.money(store.deliveryFee!),
                              }),
                            ),
                          if (store.distanceKm != null)
                            _Meta(
                              icon: Ph.navigationArrow,
                              text: s.t('km', {
                                'km': store.distanceKm!.toStringAsFixed(1),
                              }),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 4),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Meta extends StatelessWidget {
  const _Meta({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: t.muted),
        const SizedBox(width: 4),
        Text(text, style: TextStyle(fontSize: 13, color: t.ink)),
      ],
    );
  }
}

class _OpenBadge extends StatelessWidget {
  const _OpenBadge({required this.open});
  final bool open;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final color = open ? t.success : t.muted;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 7,
          height: 7,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 5),
        Text(
          S.of(context).t(open ? 'open' : 'closed'),
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }
}

class _StoreSkeleton extends StatelessWidget {
  const _StoreSkeleton();

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    Widget bone(double w, double h, [double r = 6]) => Container(
      width: w,
      height: h,
      decoration: BoxDecoration(
        color: t.sunk,
        borderRadius: BorderRadius.circular(r),
      ),
    );
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 5, 16, 5),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: t.surface,
          borderRadius: BorderRadius.circular(Radii.lg),
          border: Border.all(color: t.hairline),
        ),
        child: Row(
          children: [
            bone(76, 76, Radii.md),
            const SizedBox(width: 14),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                bone(140, 14),
                const SizedBox(height: 10),
                bone(80, 12),
                const SizedBox(height: 12),
                bone(170, 12),
              ],
            ),
          ],
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
    final t = WaselTheme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(32, 40, 32, 32),
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(color: t.sunk, shape: BoxShape.circle),
            child: Icon(
              onRetry == null ? Ph.storefront : Ph.warningCircle,
              size: 30,
              color: t.muted,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            text,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 15, color: t.muted, height: 1.5),
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
