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

  @override
  void initState() {
    super.initState();
    _refresh();
    _live = context.read<LiveUpdates>().events.listen(_onEvent);
  }

  @override
  void dispose() {
    _live?.cancel();
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

  Future<void> _goOnline(bool value) async {
    await context.read<CaptainSession>().setOnline(value);
    if (value) _checkOffer();
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

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 20,
        title: Text(
          session.user?.name.isNotEmpty == true
              ? session.user!.name
              : s.t('online'),
        ),
        actions: [
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
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 32),
          children: [
            Card(
              child: SwitchListTile(
                key: const Key('online'),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 6,
                ),
                value: session.online,
                // Stay online while carrying an order so the customer keeps seeing you.
                onChanged: _current != null && session.online
                    ? null
                    : _goOnline,
                title: Text(
                  s.t(session.online ? 'online' : 'offline'),
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: session.online ? scheme.primary : null,
                  ),
                ),
                subtitle: Text(
                  sharer.permissionDenied ? s.t('gpsOff') : s.t('goOnlineHint'),
                ),
              ),
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
              _OrderCard(order: _current!, onTap: () => _open(_current!)),
            ],
            if (session.online && _current == null) ...[
              _Heading(s.t('available')),
              if (_loading)
                const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_available.isEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 32),
                  child: Text(
                    s.t('noAvailable'),
                    textAlign: TextAlign.center,
                    style: TextStyle(color: scheme.onSurfaceVariant),
                  ),
                )
              else
                for (final order in _available)
                  _OrderCard(
                    order: order,
                    action: FilledButton(
                      onPressed: _taking == null ? () => _take(order) : null,
                      child: Text(s.t('takeOrder')),
                    ),
                  ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Heading extends StatelessWidget {
  const _Heading(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 24, 4, 10),
    child: Text(
      text,
      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
    ),
  );
}

class _OrderCard extends StatelessWidget {
  const _OrderCard({required this.order, this.action, this.onTap});
  final Order order;
  final Widget? action;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final scheme = Theme.of(context).colorScheme;
    final muted = TextStyle(color: scheme.onSurfaceVariant);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        order.vendorName,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Text(s.t('orderNumber', {'id': order.id}), style: muted),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  s.t('status_${order.status}'),
                  style: TextStyle(
                    color: scheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (order.deliveryAddress.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    '${s.t('deliverTo')}: ${order.deliveryAddress}',
                    style: muted,
                  ),
                ],
                const SizedBox(height: 4),
                Text(
                  order.cashToCollect > 0
                      ? s.t('collectCash', {
                          'amount': s.money(order.cashToCollect),
                        })
                      : s.t('paidInApp'),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                if (action != null) ...[const SizedBox(height: 14), action!],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
