import 'package:flutter/material.dart';
import 'package:wasel_core/wasel_core.dart';

import '../screens/store_screen.dart';

/// The store types customers can browse, in rail order.
const storeTypes = [
  'restaurant',
  'supermarket',
  'cafe',
  'pharmacy',
  'convenience',
  'flowers',
];

/// "15% off", "3,000 IQD off" or "Free delivery".
String offerHeadline(S s, Offer offer) => switch (offer.type) {
  'percent' => s.t('offerPercent', {
    'value': offer.value.toStringAsFixed(offer.value % 1 == 0 ? 0 : 1),
  }),
  'fixed' => s.t('offerFixed', {'value': s.money(offer.value, offer.currency)}),
  _ => s.t('offerFree'),
};

/// A store in a list: art, name, open or closed, what it is, fees and
/// distance, its headline offer, and in a search the dishes that matched.
class StoreCard extends StatelessWidget {
  const StoreCard({super.key, required this.store});
  final Vendor store;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final meta = TextStyle(color: t.muted, fontSize: 13);
    final kind = store.type == 'restaurant'
        ? (store.cuisine.isEmpty ? '' : s.t(store.cuisine))
        : s.t('kind_${store.type}');
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
                Stack(
                  clipBehavior: Clip.none,
                  children: [
                    CuisineArt(
                      cuisine: store.cuisine,
                      type: store.type,
                      size: 76,
                      radius: Radii.md,
                    ),
                    if (store.offer != null)
                      PositionedDirectional(
                        start: -4,
                        bottom: -6,
                        child: OfferBadge(text: offerHeadline(s, store.offer!)),
                      ),
                  ],
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
                      if (kind.isNotEmpty) Text(kind, style: meta),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 14,
                        runSpacing: 4,
                        children: [
                          if (store.deliveryFee != null)
                            _Meta(
                              icon: Ph.moped,
                              text: s.t('deliveryFee', {
                                'fee': s.money(
                                  store.deliveryFee!,
                                  store.currency,
                                ),
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
                      if (store.matches.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Icon(
                              Ph.magnifyingGlass,
                              size: 14,
                              color: t.goldText,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                store.matches
                                    .map((m) => m.name(s.lang))
                                    .join(' · '),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 13,
                                  color: t.goldText,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
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

/// A gold pill with an offer's headline.
class OfferBadge extends StatelessWidget {
  const OfferBadge({super.key, required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: ShapeDecoration(
        color: Gold.c400,
        shape: const StadiumBorder(),
        shadows: [
          BoxShadow(
            color: Lapis.c950.withValues(alpha: 0.25),
            blurRadius: 8,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Ph.sealPercent, size: 13, color: Lapis.c950),
          const SizedBox(width: 4),
          Text(
            text,
            style: const TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              color: Lapis.c950,
            ),
          ),
        ],
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

/// Card-shaped placeholders while stores load.
class StoreSkeletons extends StatelessWidget {
  const StoreSkeletons({super.key, this.count = 4});
  final int count;

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
    return Shimmer(
      child: Column(
        children: [
          for (var i = 0; i < count; i++)
            Padding(
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
            ),
        ],
      ),
    );
  }
}

/// A quiet message with an icon, and a retry button after an error.
class ListMessage extends StatelessWidget {
  const ListMessage({
    super.key,
    required this.text,
    this.onRetry,
    this.icon = Ph.storefront,
  });
  final String text;
  final VoidCallback? onRetry;
  final IconData icon;

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
              onRetry == null ? icon : Ph.warningCircle,
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
