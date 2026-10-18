import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../config.dart';

/// Live order: map with store, home and captain, status steps and the PIN.
class TrackingScreen extends StatefulWidget {
  const TrackingScreen({super.key, required this.orderId});
  final int orderId;

  @override
  State<TrackingScreen> createState() => _TrackingScreenState();
}

class _TrackingScreenState extends State<TrackingScreen>
    with SingleTickerProviderStateMixin {
  Order? _order;
  bool _failed = false;
  DateTime? _captainSeenAt;
  StreamSubscription? _live;
  Timer? _clock;

  MapLibreMapController? _map;
  bool _styleReady = false;
  Circle? _vendorDot;
  Circle? _homeDot;
  Circle? _captainDot;
  bool _fitted = false;

  // Glides the captain dot between GPS fixes.
  late final Ticker _ticker = createTicker(_tick);
  LatLng? _glideFrom;
  LatLng? _glideTo;
  Duration _glideStart = Duration.zero;
  static const _glideTime = Duration(milliseconds: 1800);

  @override
  void initState() {
    super.initState();
    _load();
    _live = context.read<LiveUpdates>().events.listen(_onEvent);
    // Keeps "updated N seconds ago" current.
    _clock = Timer.periodic(
      const Duration(seconds: 1),
      (_) => mounted ? setState(() {}) : null,
    );
  }

  @override
  void dispose() {
    _ticker.dispose();
    _live?.cancel();
    _clock?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final order = await context.read<ApiClient>().order(widget.orderId);
      _apply(order);
    } on ApiException {
      if (mounted) setState(() => _failed = true);
    }
  }

  void _onEvent(Map<String, dynamic> event) {
    if (event['type'] == 'order.updated' &&
        event['order']['id'] == widget.orderId) {
      _apply(Order.fromJson(event['order']));
    } else if (event['type'] == 'captain.location' &&
        event['order_id'] == widget.orderId) {
      final location = CaptainLocation.fromJson(event['location'])!;
      _captainSeenAt = location.updatedAt;
      _moveCaptain(location.point);
    } else if (event['type'] == 'connected') {
      _load(); // catch up on anything missed while offline
    }
  }

  void _apply(Order order) {
    if (!mounted) return;
    setState(() {
      _order = order;
      _failed = false;
      if (order.captainLocation != null) {
        _captainSeenAt = order.captainLocation!.updatedAt;
      }
    });
    _drawMarkers();
  }

  // --- Map -------------------------------------------------------------------

  LatLng _latLng(GeoPoint p) => LatLng(p.lat, p.lng);

  Future<void> _drawMarkers() async {
    final map = _map;
    final order = _order;
    if (map == null || !_styleReady || order == null) return;
    final dark = Theme.of(context).brightness == Brightness.dark;
    final surface = dark ? '#151A2F' : '#FBFCFE';
    final ink = dark ? '#EDF0FA' : '#141A2E';

    if (_vendorDot == null && order.vendorLocation != null) {
      _vendorDot = await map.addCircle(
        CircleOptions(
          geometry: _latLng(order.vendorLocation!),
          circleRadius: 9,
          circleColor: surface,
          circleStrokeColor: ink,
          circleStrokeWidth: 3,
        ),
      );
    }
    if (_homeDot == null && order.deliveryLocation != null) {
      _homeDot = await map.addCircle(
        CircleOptions(
          geometry: _latLng(order.deliveryLocation!),
          circleRadius: 9,
          circleColor: ink,
          circleStrokeColor: surface,
          circleStrokeWidth: 3,
        ),
      );
    }
    if (order.isTracked &&
        order.captainLocation != null &&
        _captainDot == null) {
      await _moveCaptain(order.captainLocation!.point);
    }
    if (order.isFinished && _captainDot != null) {
      await map.removeCircle(_captainDot!);
      _captainDot = null;
    }
    if (!_fitted) {
      _fitted = true;
      await _fit();
    }
  }

  Future<void> _moveCaptain(GeoPoint point) async {
    final map = _map;
    if (map == null || !_styleReady || (_order?.isFinished ?? false)) return;
    final target = _latLng(point);
    if (_captainDot == null) {
      _captainDot = await map.addCircle(
        CircleOptions(
          geometry: target,
          circleRadius: 12,
          circleColor: '#F2C75C',
          circleStrokeColor: '#22379B',
          circleStrokeWidth: 5,
        ),
      );
      await _fit();
      return;
    }
    if (MediaQuery.of(context).disableAnimations) {
      await map.updateCircle(_captainDot!, CircleOptions(geometry: target));
      return;
    }
    _glideFrom = _captainDot!.options.geometry;
    _glideTo = target;
    _glideStart = Duration.zero;
    if (_ticker.isActive) _ticker.stop();
    _ticker.start();
  }

  void _tick(Duration elapsed) {
    final from = _glideFrom, to = _glideTo, dot = _captainDot, map = _map;
    if (from == null || to == null || dot == null || map == null) return;
    if (_glideStart == Duration.zero) _glideStart = elapsed;
    final t =
        ((elapsed - _glideStart).inMilliseconds / _glideTime.inMilliseconds)
            .clamp(0.0, 1.0);
    final position = LatLng(
      from.latitude + (to.latitude - from.latitude) * t,
      from.longitude + (to.longitude - from.longitude) * t,
    );
    map.updateCircle(dot, CircleOptions(geometry: position));
    if (t >= 1) _ticker.stop();
  }

  Future<void> _fit() async {
    final map = _map;
    final points = [
      _vendorDot?.options.geometry,
      _homeDot?.options.geometry,
      _captainDot?.options.geometry,
    ].whereType<LatLng>().toList();
    if (map == null || points.isEmpty) return;
    final lats = points.map((p) => p.latitude);
    final lngs = points.map((p) => p.longitude);
    final bounds = LatLngBounds(
      southwest: LatLng(
        lats.reduce((a, b) => a < b ? a : b),
        lngs.reduce((a, b) => a < b ? a : b),
      ),
      northeast: LatLng(
        lats.reduce((a, b) => a > b ? a : b),
        lngs.reduce((a, b) => a > b ? a : b),
      ),
    );
    final sheet = MediaQuery.sizeOf(context).height * 0.42;
    await map.animateCamera(
      CameraUpdate.newLatLngBounds(
        bounds,
        left: 60,
        right: 60,
        top: 100,
        bottom: sheet + 40,
      ),
    );
  }

  // --- UI --------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final dark = Theme.of(context).brightness == Brightness.dark;
    final order = _order;

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
                _drawMarkers();
              },
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: _Panel(
              order: order,
              failed: _failed,
              captainSeenAt: _captainSeenAt,
              onRetry: _load,
              strings: s,
            ),
          ),
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
    required this.order,
    required this.failed,
    required this.captainSeenAt,
    required this.onRetry,
    required this.strings,
  });
  final Order? order;
  final bool failed;
  final DateTime? captainSeenAt;
  final VoidCallback onRetry;
  final S strings;

  static const _stepIcons = {
    'received': Ph.receipt,
    'preparing': Ph.cookingPot,
    'ready': Ph.shoppingBag,
    'out_for_delivery': Ph.moped,
    'delivered': Ph.checkCircle,
    'cancelled': Ph.receiptX,
  };

  @override
  Widget build(BuildContext context) {
    final s = strings;
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final order = this.order;

    Widget content;
    if (failed) {
      content = Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Ph.warningCircle, size: 30, color: t.muted),
          const SizedBox(height: 8),
          Text(s.t('err_network')),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: Text(s.t('retry'))),
        ],
      );
    } else if (order == null) {
      content = const Padding(
        padding: EdgeInsets.all(24),
        child: Center(child: CircularProgressIndicator()),
      );
    } else {
      final current = Order.steps.indexOf(order.status);
      final cancelled = order.status == 'cancelled';
      content = Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: cancelled ? null : GlazePanel.gradient,
                  color: cancelled ? t.sunk : null,
                ),
                child: Icon(
                  _stepIcons[order.status] ?? Ph.receipt,
                  size: 26,
                  color: cancelled ? t.muted : Gold.c400,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${order.vendorName} · ${s.t('orderNumber', {'id': order.id})}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: t.muted, fontSize: 13),
                    ),
                    const SizedBox(height: 2),
                    AnimatedSwitcher(
                      duration: Motion.medium,
                      switchInCurve: Motion.out,
                      child: Text(
                        s.t('status_${order.status}'),
                        key: ValueKey(order.status),
                        style: const TextStyle(
                          fontSize: 21,
                          fontWeight: FontWeight.w700,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              for (var i = 0; i < Order.steps.length; i++) ...[
                Expanded(
                  child: Column(
                    children: [
                      AnimatedContainer(
                        duration: Motion.medium,
                        curve: Motion.spring,
                        width: 34,
                        height: 34,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: !cancelled && i <= current
                              ? scheme.primary
                              : t.sunk,
                          border: i == current && !cancelled
                              ? Border.all(color: Gold.c400, width: 2)
                              : null,
                        ),
                        child: Icon(
                          !cancelled && i < current
                              ? Ph.check
                              : _stepIcons[Order.steps[i]],
                          size: 16,
                          color: !cancelled && i <= current
                              ? scheme.onPrimary
                              : t.muted,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        s.t('step_${Order.steps[i]}'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: i == current ? FontWeight.w700 : null,
                          color: i == current ? t.ink : t.muted,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
          if (order.deliveryPin != null && !order.isFinished) ...[
            const SizedBox(height: 18),
            GlazePanel(
              radius: Radii.lg,
              padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          s.t('pin'),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          s.t('pinHelp'),
                          style: const TextStyle(
                            fontSize: 13,
                            height: 1.4,
                            color: Lapis.c200,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    order.deliveryPin!,
                    textDirection: TextDirection.ltr,
                    style: const TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 6,
                      color: Gold.c400,
                      fontFeatures: [FontFeature.tabularFigures()],
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (order.isTracked) ...[
            const SizedBox(height: 14),
            Row(
              children: [
                Icon(Ph.moped, color: scheme.primary, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _captainText(s, order),
                    style: TextStyle(color: t.muted, fontSize: 14),
                  ),
                ),
              ],
            ),
          ],
        ],
      );
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
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 18),
          decoration: BoxDecoration(
            color: t.surface,
            borderRadius: BorderRadius.circular(Radii.xl),
          ),
          child: content,
        ),
      ),
    );
  }

  String _captainText(S s, Order order) {
    if (order.captainId == null) return s.t('captainWaiting');
    final seen = captainSeenAt;
    if (seen == null) return s.t('captainNoGps');
    final seconds = DateTime.now().difference(seen).inSeconds.clamp(0, 1 << 30);
    return seconds < 60
        ? s.t('captainSeconds', {'n': seconds})
        : s.t('captainMinutes', {'n': (seconds / 60).round()});
  }
}
