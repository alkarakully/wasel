import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/captain_session.dart';
import '../state/location_sharer.dart';
import 'delivery_screen.dart';
import 'offer_sheet.dart';

/// Online switch, the captain's current delivery, and orders to take.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Order> _available = [];
  Order? _current;
  bool _loading = true;
  String? _error;
  int? _taking;
  StreamSubscription? _live;
  final _closedOffers = StreamController<int>.broadcast();
  bool _offerShowing = false;
  bool _wasOnline = false;
  late final CaptainSession _session = context.read<CaptainSession>();

  @override
  void initState() {
    super.initState();
    _refresh();
    _live = context.read<LiveUpdates>().events.listen(_onEvent);
    _session.addListener(_onSessionChanged);
    _onSessionChanged();
  }

  @override
  void dispose() {
    _live?.cancel();
    _session.removeListener(_onSessionChanged);
    _closedOffers.close();
    super.dispose();
  }

  void _onEvent(Map<String, dynamic> event) {
    if (!mounted) return;
    switch (event['type']) {
      case 'order.available':
        final order = Order.fromJson(event['order']);
        setState(
          () => _available = [
            ..._available.where((o) => o.id != order.id),
            order,
          ],
        );
      case 'order.unavailable':
        setState(
          () => _available = _available
              .where((o) => o.id != event['order_id'])
              .toList(),
        );
      case 'order.updated':
        // One of my orders changed (delivered, cancelled, picked up elsewhere).
        _refresh();
      case 'dispatch.offer':
        _showOffer(DispatchOffer.fromJson(event['offer']));
      case 'dispatch.offer_closed':
        _closedOffers.add(event['offer_id'] as int);
      case 'connected':
        _refresh(); // catch up after reconnecting
        _checkOffer();
    }
  }

  Future<void> _refresh() async {
    final api = context.read<ApiClient>();
    final me = context.read<BaseSession>().user?.id;
    try {
      final results = await Future.wait([api.orders(), api.availableOrders()]);
      final mine = results[0].where((o) => o.isTracked && o.captainId == me);
      setState(() {
        _current = mine.isEmpty ? null : mine.first;
        _available = results[1];
        _loading = false;
        _error = null;
      });
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'err_${error.code}';
        });
      }
    }
  }

  /// An offer may have arrived while the app was reconnecting or offline.
  Future<void> _checkOffer() async {
    if (!context.read<CaptainSession>().online) return;
    try {
      final offer = await context.read<ApiClient>().currentOffer();
      if (offer != null) _showOffer(offer);
    } on ApiException {
      // The live socket will deliver the next one.
    }
  }

  Future<void> _showOffer(DispatchOffer offer) async {
    if (_offerShowing || !mounted || offer.timeLeft == Duration.zero) return;
    _offerShowing = true;
    HapticFeedback.heavyImpact();
    SystemSound.play(SystemSoundType.alert);
    final order = await showModalBottomSheet<Order>(
      context: context,
      isDismissible: false,
      enableDrag: false,
      showDragHandle: true,
      builder: (_) => OfferSheet(offer: offer, closed: _closedOffers.stream),
    );
    _offerShowing = false;
    if (!mounted) return;
    if (order != null) {
      await _open(order);
    } else {
      _refresh();
    }
  }

  Future<void> _goOnline(bool value) =>
      context.read<CaptainSession>().setOnline(value);

  /// Look for an offer whenever the captain goes online (switch or notification).
  void _onSessionChanged() {
    final online = context.read<CaptainSession>().online;
    if (online && !_wasOnline) _checkOffer();
    _wasOnline = online;
  }

  Future<void> _take(Order order) async {
    setState(() => _taking = order.id);
    try {
      final claimed = await context.read<ApiClient>().claim(order.id);
      if (!mounted) return;
      await _open(claimed);
    } on ApiException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(S.read(context).t('err_${error.code}'))),
      );
      _refresh();
    } finally {
      if (mounted) setState(() => _taking = null);
    }
  }

  Future<void> _open(Order order) async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => DeliveryScreen(orderId: order.id)),
    );
    if (mounted) _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final session = context.watch<CaptainSession>();
    final sharer = context.watch<LocationSharer>();
    final scheme = Theme.of(context).colorScheme;
    final t = WaselTheme.of(context);
    final name = session.user?.name ?? '';

    return Scaffold(
      backgroundColor: t.canvas,
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Row(
                children: [
                  const Wordmark(size: 30, latinColor: Wordmark.logoBlue),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: t.muted, fontSize: 15),
                    ),
                  ),
                  PopupMenuButton<String>(
                    tooltip: '',
                    position: PopupMenuPosition.under,
                    onSelected: (value) =>
                        value == 'logout' ? session.signOut() : null,
                    itemBuilder: (_) => [
                      PopupMenuItem(
                        enabled: false,
                        child: Text(
                          session.user?.phone ?? '',
                          textDirection: TextDirection.ltr,
                        ),
                      ),
                      const PopupMenuItem(
                        enabled: false,
                        child: LanguageSwitch(),
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
                    child: Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: t.surface,
                        shape: BoxShape.circle,
                        border: Border.all(color: t.hairline),
                        boxShadow: t.raised,
                      ),
                      child: Icon(Ph.user, size: 22, color: t.ink),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              _StatusCard(
                online: session.online,
                hint: sharer.permissionDenied
                    ? s.t('gpsOff')
                    : s.t(session.online ? 'onlineHint' : 'goOnlineHint'),
                warn: sharer.permissionDenied,
                // Stay online while carrying an order so the customer keeps
                // seeing you.
                onChanged: _current != null && session.online
                    ? null
                    : _goOnline,
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 16),
                  child: Text(
                    s.t(_error!),
                    style: TextStyle(color: scheme.error),
                  ),
                ),
              if (_current != null) ...[
                _Heading(s.t('currentDelivery')),
                _OrderCard(
                  order: _current!,
                  highlight: true,
                  onTap: () => _open(_current!),
                ),
              ],
              if (session.online && _current == null) ...[
                _Heading(s.t('available'), count: _available.length),
                if (_loading)
                  const Padding(
                    padding: EdgeInsets.all(32),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (_available.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      vertical: 28,
                      horizontal: 24,
                    ),
                    child: Column(
                      children: [
                        Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            color: t.sunk,
                            shape: BoxShape.circle,
                          ),
                          child: Icon(Ph.hourglass, size: 28, color: t.muted),
                        ),
                        const SizedBox(height: 14),
                        Text(
                          s.t('noAvailable'),
                          textAlign: TextAlign.center,
                          style: TextStyle(color: t.muted, height: 1.5),
                        ),
                      ],
                    ),
                  )
                else
                  for (final (i, order) in _available.indexed)
                    Reveal(
                      key: ValueKey(order.id),
                      index: i,
                      child: _OrderCard(
                        order: order,
                        action: PillButton(
                          label: s.t('takeOrder'),
                          busy: _taking == order.id,
                          onPressed: _taking == null
                              ? () => _take(order)
                              : null,
                        ),
                      ),
                    ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Online state: glazed lapis while working, a quiet tray while off.
class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.online,
    required this.hint,
    required this.warn,
    required this.onChanged,
  });
  final bool online;
  final String hint;
  final bool warn;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final content = Row(
      children: [
        Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: online ? Gold.c400 : t.sunk,
          ),
          child: Icon(
            online ? Ph.moped : Ph.power,
            size: 26,
            color: online ? Lapis.c950 : t.muted,
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                s.t(online ? 'online' : 'offline'),
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: online ? Colors.white : t.ink,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                hint,
                style: TextStyle(
                  fontSize: 13,
                  height: 1.45,
                  color: warn
                      ? (online
                            ? Gold.c300
                            : Theme.of(context).colorScheme.error)
                      : (online ? Lapis.c200 : t.muted),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Switch(
          key: const Key('online'),
          value: online,
          onChanged: onChanged,
          activeTrackColor: Colors.white.withValues(alpha: 0.24),
        ),
      ],
    );

    return AnimatedSwitcher(
      duration: Motion.medium,
      switchInCurve: Motion.out,
      switchOutCurve: Motion.out,
      child: online
          ? DecoratedBox(
              key: const ValueKey('on'),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(Radii.xl),
                boxShadow: [
                  BoxShadow(
                    color: Lapis.c900.withValues(alpha: 0.30),
                    blurRadius: 28,
                    spreadRadius: -10,
                    offset: const Offset(0, 16),
                  ),
                ],
              ),
              child: GlazePanel(
                radius: Radii.xl,
                padding: const EdgeInsets.fromLTRB(18, 20, 14, 20),
                child: content,
              ),
            )
          : BezelCard(
              key: const ValueKey('off'),
              radius: Radii.xl,
              padding: const EdgeInsets.fromLTRB(16, 18, 12, 18),
              child: content,
            ),
    );
  }
}

class _Heading extends StatelessWidget {
  const _Heading(this.text, {this.count});
  final String text;
  final int? count;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 26, 4, 12),
      child: Row(
        children: [
          Expanded(
            child: Text(
              text,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
          ),
          if (count != null && count! > 0)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
              decoration: ShapeDecoration(
                color: scheme.secondaryContainer,
                shape: const StadiumBorder(),
              ),
              child: Text(
                '$count',
                style: TextStyle(
                  color: scheme.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  const _OrderCard({
    required this.order,
    this.action,
    this.onTap,
    this.highlight = false,
  });
  final Order order;
  final Widget? action;
  final VoidCallback? onTap;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final cash = order.cashToCollect > 0;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Pressable(
        scale: onTap == null ? 1 : 0.98,
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: t.surface,
            borderRadius: BorderRadius.circular(Radii.lg),
            border: Border.all(
              color: highlight ? scheme.primary : t.hairline,
              width: highlight ? 1.5 : 1,
            ),
            boxShadow: t.raised,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: scheme.secondaryContainer,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Ph.storefront, size: 22, color: scheme.primary),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          order.vendorName,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Text(
                          s.t('status_${order.status}'),
                          style: TextStyle(
                            color: scheme.primary,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    s.t('orderNumber', {'id': order.id}),
                    style: TextStyle(color: t.muted, fontSize: 13),
                  ),
                  if (onTap != null) ...[
                    const SizedBox(width: 6),
                    Icon(
                      Directionality.of(context) == TextDirection.rtl
                          ? Ph.caretLeft
                          : Ph.caretRight,
                      size: 18,
                      color: t.muted,
                    ),
                  ],
                ],
              ),
              if (order.deliveryAddress.isNotEmpty) ...[
                const SizedBox(height: 12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Ph.mapPin, size: 18, color: t.muted),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${s.t('deliverTo')}: ${order.deliveryAddress}',
                        style: TextStyle(color: t.muted, height: 1.4),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: cash ? goldWash(context) : t.sunk,
                  borderRadius: BorderRadius.circular(Radii.sm),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      cash ? Ph.money : Ph.checkCircle,
                      size: 18,
                      color: cash ? t.goldText : t.success,
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        cash
                            ? s.t('collectCash', {
                                'amount': s.money(
                                  order.cashToCollect,
                                  order.currency,
                                ),
                              })
                            : s.t('paidInApp'),
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: cash ? t.goldText : t.ink,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              if (action != null) ...[const SizedBox(height: 14), action!],
            ],
          ),
        ),
      ),
    );
  }
}
