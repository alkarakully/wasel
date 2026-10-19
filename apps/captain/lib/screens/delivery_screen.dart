import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:wasel_core/wasel_core.dart';

import '../config.dart';
import '../state/location_sharer.dart';

/// One delivery: map, then the next step (pick up, or PIN at the door).
class DeliveryScreen extends StatefulWidget {
  const DeliveryScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<DeliveryScreen> createState() => _DeliveryScreenState();
}

class _DeliveryScreenState extends State<DeliveryScreen> {
  Order? _order;
  String? _error;
  bool _busy = false;
  final _pin = TextEditingController();
  StreamSubscription? _live;
  late final LocationSharer _sharer = context.read<LocationSharer>();

  MapLibreMapController? _map;
  bool _styleReady = false;
  Circle? _meDot;
  bool _fitted = false;

  @override
  void initState() {
    super.initState();
    _load();
    _live = context.read<LiveUpdates>().events.listen((event) {
      if (event['type'] == 'order.updated' &&
          event['order']['id'] == widget.orderId) {
        // Socket copies leave out the customer's phone; keep the one we have.
        final fresh = Order.fromJson(event['order']);
        _apply(
          fresh.customerPhone == null && _order != null
              ? _withContact(fresh, _order!)
              : fresh,
        );
      }
    });
    _sharer.addListener(_drawMe);
  }

  @override
  void dispose() {
    _live?.cancel();
    _sharer.removeListener(_drawMe);
    _pin.dispose();
    super.dispose();
  }

  Order _withContact(Order fresh, Order old) => Order(
    id: fresh.id,
    vendorName: fresh.vendorName,
    status: fresh.status,
    captainId: fresh.captainId,
    total: fresh.total,
    deliveryPin: fresh.deliveryPin,
    vendorLocation: fresh.vendorLocation,
    deliveryLocation: fresh.deliveryLocation,
    captainLocation: fresh.captainLocation,
    createdAt: fresh.createdAt,
    deliveryAddress: fresh.deliveryAddress,
    paymentType: fresh.paymentType,
    customerName: old.customerName,
    customerPhone: old.customerPhone,
  );

  Future<void> _load() async {
    try {
      _apply(await context.read<ApiClient>().order(widget.orderId));
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = 'err_${error.code}');
    }
  }

  void _apply(Order order) {
    if (!mounted) return;
    setState(() => _order = order);
    _drawPlaces();
  }

  Future<void> _run(Future<Order> Function(ApiClient api) step) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final updated = await step(context.read<ApiClient>());
      _apply(_order == null ? updated : _withContact(updated, _order!));
      HapticFeedback.mediumImpact();
    } on ApiException catch (error) {
      setState(() => _error = 'err_${error.code}');
      if (error.code == 'wrong_pin') _pin.clear();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _call(String phone) =>
      launchUrl(Uri(scheme: 'tel', path: phone));

  Future<void> _directions(GeoPoint to) {
    final destination = '${to.lat},${to.lng}';
    final url = Platform.isIOS
        ? Uri.https('maps.apple.com', '/', {'daddr': destination})
        : Uri.https('www.google.com', '/maps/dir/', {
            'api': '1',
            'destination': destination,
          });
    return launchUrl(url, mode: LaunchMode.externalApplication);
  }

  // --- Map -------------------------------------------------------------------

  LatLng _latLng(GeoPoint p) => LatLng(p.lat, p.lng);

  Future<void> _drawPlaces() async {
    final map = _map, order = _order;
    if (map == null || !_styleReady || order == null || _fitted) return;
    _fitted = true;
    // Read everything from context before the first await.
    final dark = Theme.of(context).brightness == Brightness.dark;
    final panelSpace = MediaQuery.sizeOf(context).height * 0.5;
    final surface = dark ? '#151A2F' : '#FBFCFE';
    final ink = dark ? '#EDF0FA' : '#141A2E';
    final points = <LatLng>[];
    if (order.vendorLocation != null) {
      points.add(_latLng(order.vendorLocation!));
      await map.addCircle(
        CircleOptions(
          geometry: points.last,
          circleRadius: 9,
          circleColor: surface,
          circleStrokeColor: ink,
          circleStrokeWidth: 3,
        ),
      );
    }
    if (order.deliveryLocation != null) {
      points.add(_latLng(order.deliveryLocation!));
      await map.addCircle(
        CircleOptions(
          geometry: points.last,
          circleRadius: 9,
          circleColor: ink,
          circleStrokeColor: surface,
          circleStrokeWidth: 3,
        ),
      );
    }
    await _drawMe();
    final me = _meDot?.options.geometry;
    if (me != null) points.add(me);
    if (points.isEmpty) return;
    final lats = points.map((p) => p.latitude),
        lngs = points.map((p) => p.longitude);
    await map.animateCamera(
      CameraUpdate.newLatLngBounds(
        LatLngBounds(
          southwest: LatLng(
            lats.reduce((a, b) => a < b ? a : b),
            lngs.reduce((a, b) => a < b ? a : b),
          ),
          northeast: LatLng(
            lats.reduce((a, b) => a > b ? a : b),
            lngs.reduce((a, b) => a > b ? a : b),
          ),
        ),
        left: 60,
        right: 60,
        top: 100,
        bottom: panelSpace,
      ),
    );
  }

  Future<void> _drawMe() async {
    final map = _map;
    final position = _sharer.last;
    if (map == null || !_styleReady || position == null) return;
    final here = LatLng(position.latitude, position.longitude);
    if (_meDot == null) {
      _meDot = await map.addCircle(
        CircleOptions(
          geometry: here,
          circleRadius: 12,
          circleColor: '#F2C75C',
          circleStrokeColor: '#22379B',
          circleStrokeWidth: 5,
        ),
      );
    } else {
      await map.updateCircle(_meDot!, CircleOptions(geometry: here));
    }
  }

  // --- UI --------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        systemOverlayStyle: dark
            ? SystemUiOverlayStyle.light
            : SystemUiOverlayStyle.dark,
        leading: Padding(
          padding: const EdgeInsets.all(6),
          child: Pressable(
            onTap: () => Navigator.pop(context),
            child: Container(
              decoration: BoxDecoration(
                color: WaselTheme.of(context).surface,
                shape: BoxShape.circle,
                boxShadow: WaselTheme.of(context).floating,
              ),
              child: Icon(
                Directionality.of(context) == TextDirection.rtl
                    ? Ph.arrowRight
                    : Ph.arrowLeft,
                size: 20,
              ),
            ),
          ),
        ),
      ),
      body: Stack(
        children: [
          Positioned.fill(
            child: MapLibreMap(
              styleString: dark ? Config.mapStyleDark : Config.mapStyleLight,
              initialCameraPosition: const CameraPosition(
                target: LatLng(Config.fallbackLat, Config.fallbackLng),
                zoom: 12,
              ),
              compassEnabled: false,
              rotateGesturesEnabled: false,
              tiltGesturesEnabled: false,
              attributionButtonPosition: AttributionButtonPosition.topRight,
              onMapCreated: (controller) => _map = controller,
              onStyleLoadedCallback: () {
                _styleReady = true;
                _drawPlaces();
              },
            ),
          ),
          Align(alignment: Alignment.bottomCenter, child: _panel(s)),
        ],
      ),
    );
  }

  Widget _panel(S s) {
    final scheme = Theme.of(context).colorScheme;
    final t = WaselTheme.of(context);
    final order = _order;
    final muted = TextStyle(color: t.muted, fontSize: 13);

    final children = <Widget>[];
    if (order == null) {
      children.add(
        _error == null
            ? const Center(child: CircularProgressIndicator())
            : Text(s.t(_error!)),
      );
    } else {
      children.addAll([
        Text(
          '${order.vendorName} · ${s.t('orderNumber', {'id': order.id})}',
          style: muted,
        ),
        const SizedBox(height: 4),
        Text(
          _title(s, order),
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 10),
        const GoldRule(width: 48),
        const SizedBox(height: 14),
      ]);

      if (order.status == 'preparing' || order.status == 'ready') {
        children.addAll([
          _place(
            s.t('pickupFrom'),
            order.vendorName,
            onDirections: order.vendorLocation == null
                ? null
                : () => _directions(order.vendorLocation!),
          ),
          const SizedBox(height: 16),
          PillButton(
            key: const Key('picked-up'),
            icon: Ph.shoppingBag,
            busy: _busy,
            onPressed: order.status == 'ready'
                ? () => _run((api) => api.pickup(order.id))
                : null,
            label: s.t('pickedUp'),
          ),
        ]);
      } else if (order.status == 'out_for_delivery') {
        children.addAll([
          _place(
            s.t('deliverTo'),
            [
              if (order.customerName?.isNotEmpty == true) order.customerName!,
              order.deliveryAddress,
            ].join(' · '),
            onDirections: order.deliveryLocation == null
                ? null
                : () => _directions(order.deliveryLocation!),
            onCall: order.customerPhone == null
                ? null
                : () => _call(order.customerPhone!),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: order.cashToCollect > 0 ? goldWash(context) : t.sunk,
              borderRadius: BorderRadius.circular(Radii.md),
            ),
            child: Row(
              children: [
                Icon(
                  order.cashToCollect > 0 ? Ph.money : Ph.checkCircle,
                  size: 22,
                  color: order.cashToCollect > 0 ? t.goldText : t.success,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    order.cashToCollect > 0
                        ? s.t('collectCash', {
                            'amount': s.money(
                              order.cashToCollect,
                              order.currency,
                            ),
                          })
                        : s.t('paidInApp'),
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 16,
                      color: order.cashToCollect > 0 ? t.goldText : t.ink,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: TextField(
                  key: const Key('pin'),
                  controller: _pin,
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.center,
                  textDirection: TextDirection.ltr,
                  maxLength: 4,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  style: const TextStyle(
                    fontSize: 24,
                    letterSpacing: 10,
                    fontWeight: FontWeight.w700,
                  ),
                  decoration: InputDecoration(
                    labelText: s.t('pinLabel'),
                    counterText: '',
                  ),
                  onChanged: (_) => setState(() => _error = null),
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 150,
                child: PillButton(
                  key: const Key('deliver'),
                  tone: PillTone.gold,
                  icon: Ph.check,
                  busy: _busy,
                  onPressed: _pin.text.length == 4
                      ? () => _run((api) => api.deliver(order.id, _pin.text))
                      : null,
                  label: s.t('deliver'),
                ),
              ),
            ],
          ),
        ]);
      } else {
        children.add(
          OutlinedButton(
            onPressed: () => Navigator.pop(context),
            child: Text(s.t('back')),
          ),
        );
      }
      if (_error != null) {
        children.addAll([
          const SizedBox(height: 10),
          Text(
            s.t(_error!),
            style: TextStyle(color: scheme.error, fontWeight: FontWeight.w600),
          ),
        ]);
      }
    }

    return Padding(
      padding: EdgeInsets.fromLTRB(
        12,
        0,
        12,
        12 + MediaQuery.paddingOf(context).bottom / 2,
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(5),
        decoration: BoxDecoration(
          color: t.sunk,
          borderRadius: BorderRadius.circular(Radii.xl + 4),
          border: Border.all(color: t.hairline),
          boxShadow: t.floating,
        ),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: t.surface,
            borderRadius: BorderRadius.circular(Radii.xl),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: children,
          ),
        ),
      ),
    );
  }

  String _title(S s, Order order) => switch (order.status) {
    'preparing' => s.t('waitForStore'),
    'ready' => s.t('readyForPickup'),
    'out_for_delivery' => s.t('onTheWay'),
    'delivered' => s.t('delivered'),
    'cancelled' => s.t('orderCancelled'),
    _ => s.t('status_${order.status}'),
  };

  Widget _place(
    String label,
    String text, {
    VoidCallback? onDirections,
    VoidCallback? onCall,
  }) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    Widget round(IconData icon, String tip, VoidCallback onTap, bool filled) =>
        Padding(
          padding: const EdgeInsetsDirectional.only(start: 8),
          child: Tooltip(
            message: tip,
            child: Semantics(
              button: true,
              label: tip,
              child: Pressable(
                onTap: onTap,
                child: Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: filled ? scheme.primary : scheme.secondaryContainer,
                  ),
                  child: Icon(
                    icon,
                    size: 22,
                    color: filled ? scheme.onPrimary : scheme.primary,
                  ),
                ),
              ),
            ),
          ),
        );
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: TextStyle(fontSize: 13, color: t.muted)),
              const SizedBox(height: 2),
              Text(
                text,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
        if (onCall != null) round(Ph.phone, s.t('callCustomer'), onCall, false),
        if (onDirections != null)
          round(Ph.navigationArrow, s.t('navigate'), onDirections, true),
      ],
    );
  }
}
