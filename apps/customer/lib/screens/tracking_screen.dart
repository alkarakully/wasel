import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter/services.dart';
import 'package:maplibre_gl/maplibre_gl.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../config.dart';
import '../l10n.dart';
import '../state/live_updates.dart';
import '../theme.dart';

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
          circleColor: '#22379B',
          circleStrokeColor: '#F4F6FF',
          circleStrokeWidth: 4,
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
          child: IconButton.filledTonal(
            onPressed: () => Navigator.pop(context),
            icon: const BackButtonIcon(),
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

  @override
  Widget build(BuildContext context) {
    final s = strings;
    final scheme = Theme.of(context).colorScheme;
    final order = this.order;

    Widget content;
    if (failed) {
      content = Column(
        mainAxisSize: MainAxisSize.min,
        children: [
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
      content = Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${order.vendorName} · ${s.t('orderNumber', {'id': order.id})}',
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
          const SizedBox(height: 4),
          Text(
            s.t('status_${order.status}'),
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              for (var i = 0; i < Order.steps.length; i++)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsetsDirectional.only(end: 6),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          height: 6,
                          decoration: BoxDecoration(
                            color: order.status != 'cancelled' && i <= current
                                ? scheme.primary
                                : scheme.outline,
                            borderRadius: BorderRadius.circular(3),
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
                            color: i == current
                                ? scheme.onSurface
                                : scheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
          if (order.deliveryPin != null && !order.isFinished) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: scheme.primaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          s.t('pin'),
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        Text(
                          s.t('pinHelp'),
                          style: TextStyle(
                            fontSize: 13,
                            color: scheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Text(
                    order.deliveryPin!,
                    textDirection: TextDirection.ltr,
                    style: TextStyle(
                      fontSize: 30,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 4,
                      color: scheme.primary,
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
                Icon(Icons.two_wheeler, color: scheme.primary, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _captainText(s, order),
                    style: TextStyle(color: scheme.onSurfaceVariant),
                  ),
                ),
              ],
            ),
          ],
        ],
      );
    }

    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        20 + MediaQuery.paddingOf(context).bottom,
      ),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(
            color: Brand.lapisDark.withValues(alpha: 0.18),
            blurRadius: 30,
          ),
        ],
      ),
      child: content,
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
