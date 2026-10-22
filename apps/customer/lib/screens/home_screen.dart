import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/session.dart';
import '../widgets/cart_bar.dart';
import '../widgets/store_card.dart';
import 'orders_screen.dart';
import 'search_screen.dart';
import 'store_screen.dart';

const cuisines = [
  'popular',
  'eastern',
  'western',
  'fast_food',
  'sweets',
  'drinks',
];

/// Stores that deliver to the customer's spot, open ones first: search,
/// kinds of store, cuisines for restaurants, and offers nearby.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

typedef _HomeData = ({
  List<Vendor> stores,
  List<Offer> banners,
  List<Vendor> withOffers,
});

class _HomeScreenState extends State<HomeScreen> {
  String? _type;
  String? _cuisine;
  Future<_HomeData>? _load;
  GeoPoint? _loadedFor;

  void _reload() {
    final session = context.read<Session>();
    final api = context.read<ApiClient>();
    final at = session.deliveryPoint;
    _loadedFor = at;
    _load = (() async {
      final results = await Future.wait([
        api.vendors(at: at, type: _type, cuisine: _cuisine),
        api.bannerOffers(),
        api.vendors(at: at, type: _type, offersOnly: true),
      ]);
      return (
        stores: results[0] as List<Vendor>,
        banners: results[1] as List<Offer>,
        withOffers: results[2] as List<Vendor>,
      );
    })();
  }

  void _pickType(String? type) => setState(() {
    _type = type;
    // Cuisines only narrow restaurants.
    if (type != null && type != 'restaurant') _cuisine = null;
    _reload();
  });

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final session = context.watch<Session>();
    // Reload when the phone's location arrives after the first load.
    if (_load == null || _loadedFor != session.deliveryPoint) _reload();
    final showCuisines = _type == null || _type == 'restaurant';

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
                  const _SearchBar(),
                  _IconRail(
                    key: const Key('type-rail'),
                    items: [
                      (null, s.t('all'), Ph.storefront),
                      for (final type in storeTypes)
                        (type, s.t('type_$type'), CuisineArt.iconForType(type)),
                    ],
                    selected: _type,
                    onSelected: _pickType,
                  ),
                  if (snapshot.hasError)
                    ListMessage(
                      text: s.t('err_network'),
                      onRetry: () => setState(_reload),
                    )
                  else ...[
                    _OfferBanners(offers: data?.banners ?? const []),
                    if (showCuisines) ...[
                      _SectionTitle(s.t('craving')),
                      _IconRail(
                        key: const Key('cuisine-rail'),
                        items: [
                          (null, s.t('all'), Ph.forkKnife),
                          for (final cuisine in cuisines)
                            (
                              cuisine,
                              s.t(cuisine),
                              CuisineArt.iconFor(cuisine),
                            ),
                        ],
                        selected: _cuisine,
                        onSelected: (value) => setState(() {
                          _cuisine = value;
                          _reload();
                        }),
                      ),
                    ],
                    if (data != null && data.withOffers.isNotEmpty) ...[
                      _SectionTitle(s.t('offersNear')),
                      _OfferRow(stores: data.withOffers),
                    ],
                    _SectionTitle(
                      _type == null ? s.t('nearbyStores') : s.t('type_$_type'),
                    ),
                    if (data == null)
                      const StoreSkeletons()
                    else if (data.stores.isEmpty)
                      ListMessage(
                        text: s.t('noStores'),
                        icon: _type == null
                            ? Ph.storefront
                            : CuisineArt.iconForType(_type!),
                      )
                    else
                      for (final (i, store) in data.stores.indexed)
                        Reveal(
                          key: ValueKey('store-${store.id}-$_type-$_cuisine'),
                          index: i,
                          child: StoreCard(store: store),
                        ),
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

/// Looks like a search field; opens the search screen.
class _SearchBar extends StatelessWidget {
  const _SearchBar();

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
      child: Semantics(
        button: true,
        label: s.t('searchHint'),
        child: Pressable(
          scale: 0.99,
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const SearchScreen()),
          ),
          child: Container(
            key: const Key('search-bar'),
            height: 52,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: ShapeDecoration(
              color: t.surface,
              shape: StadiumBorder(side: BorderSide(color: t.hairline)),
              shadows: t.raised,
            ),
            child: Row(
              children: [
                Icon(Ph.magnifyingGlass, size: 22, color: t.muted),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    s.t('searchHint'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 15, color: t.muted),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Stores running an offer, as a sideways row of compact cards.
class _OfferRow extends StatelessWidget {
  const _OfferRow({required this.stores});
  final List<Vendor> stores;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    return SizedBox(
      height: 96,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: stores.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (context, i) {
          final store = stores[i];
          return Reveal(
            index: i,
            child: Pressable(
              scale: 0.98,
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => StoreScreen(storeId: store.id),
                ),
              ),
              child: Container(
                width: 250,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: t.surface,
                  borderRadius: BorderRadius.circular(Radii.lg),
                  border: Border.all(color: Gold.c400.withValues(alpha: 0.5)),
                  boxShadow: t.raised,
                ),
                child: Row(
                  children: [
                    CuisineArt(
                      cuisine: store.cuisine,
                      type: store.type,
                      size: 74,
                      radius: Radii.md,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            store.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          if (store.offer != null)
                            OfferBadge(text: offerHeadline(s, store.offer!)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
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
                      : session.fallbackCountry == 'IQ'
                      ? s.t('baghdad')
                      : countryFor(session.fallbackCountry).name(s.lang),
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
            onSelected: (value) => value == 'logout'
                ? session.signOut()
                : Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const AccountScreen()),
                  ),
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
                value: 'account',
                child: Row(
                  children: [
                    const Icon(Ph.key, size: 20),
                    const SizedBox(width: 10),
                    Text(s.t('account')),
                  ],
                ),
              ),
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
/// Offers on glazed lapis, turning every few seconds; gold dots show where
/// you are. Turning pauses while a finger is on it.
class _OfferBanners extends StatefulWidget {
  const _OfferBanners({required this.offers});
  final List<Offer> offers;

  @override
  State<_OfferBanners> createState() => _OfferBannersState();
}

class _OfferBannersState extends State<_OfferBanners> {
  PageController? _pages;
  Timer? _turn;
  int _page = 0;

  List<Offer> get offers => widget.offers;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _pages ??= PageController(viewportFraction: offers.length <= 1 ? 1 : 0.86);
    _schedule();
  }

  @override
  void didUpdateWidget(_OfferBanners old) {
    super.didUpdateWidget(old);
    _schedule();
  }

  void _schedule() {
    _turn?.cancel();
    if (offers.length < 2 || MediaQuery.of(context).disableAnimations) return;
    _turn = Timer.periodic(const Duration(seconds: 5), (_) {
      final pages = _pages;
      if (pages == null || !pages.hasClients) return;
      pages.animateToPage(
        (_page + 1) % offers.length,
        duration: Motion.slow,
        curve: Motion.spring,
      );
    });
  }

  @override
  void dispose() {
    _turn?.cancel();
    _pages?.dispose();
    super.dispose();
  }

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
    final pageView = SizedBox(
      height: 168,
      child: Listener(
        // A finger on the banner stops it turning until it's let go.
        onPointerDown: (_) => _turn?.cancel(),
        onPointerUp: (_) => _schedule(),
        onPointerCancel: (_) => _schedule(),
        child: PageView(
          controller: _pages,
          padEnds: false,
          onPageChanged: (page) => setState(() => _page = page),
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
      ),
    );
    if (items.length < 2) return pageView;
    return Column(
      children: [
        pageView,
        const SizedBox(height: 10),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var i = 0; i < items.length; i++)
              AnimatedContainer(
                duration: Motion.medium,
                curve: Motion.spring,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: i == _page ? 22 : 7,
                height: 7,
                decoration: ShapeDecoration(
                  color: i == _page
                      ? Gold.c400
                      : WaselTheme.of(context).hairline,
                  shape: const StadiumBorder(),
                ),
              ),
          ],
        ),
      ],
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

/// A sideways picker of icon tiles (kinds of store, cuisines); the chosen
/// one is glazed. A null key means "all".
class _IconRail extends StatelessWidget {
  const _IconRail({
    super.key,
    required this.items,
    required this.selected,
    required this.onSelected,
  });
  final List<(String?, String, IconData)> items;
  final String? selected;
  final ValueChanged<String?> onSelected;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      height: 98,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        children: [
          for (final (key, label, icon) in items)
            Semantics(
              button: true,
              selected: selected == key,
              child: Pressable(
                onTap: () => onSelected(key),
                child: SizedBox(
                  width: 84,
                  child: Column(
                    children: [
                      AnimatedContainer(
                        duration: Motion.medium,
                        curve: Motion.spring,
                        width: 60,
                        height: 60,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(Radii.md + 4),
                          gradient: selected == key
                              ? GlazePanel.gradient
                              : null,
                          color: selected == key ? null : t.surface,
                          border: Border.all(
                            color: selected == key
                                ? Colors.transparent
                                : t.hairline,
                          ),
                          boxShadow: selected == key ? t.floating : t.raised,
                        ),
                        child: Icon(
                          icon,
                          size: 28,
                          color: selected == key ? Gold.c400 : scheme.primary,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: selected == key
                              ? FontWeight.w700
                              : FontWeight.w500,
                          color: selected == key ? t.ink : t.muted,
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
