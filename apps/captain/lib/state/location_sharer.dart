import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:wasel_core/wasel_core.dart';

/// Streams the captain's GPS to the server while they are online.
///
/// Sends over the live socket when it's open and falls back to REST. The
/// server ignores fixes closer than 2 seconds, so we send at most every 3.
class LocationSharer extends ChangeNotifier {
  LocationSharer(this.api, this.live);

  final ApiClient api;
  final LiveUpdates live;

  StreamSubscription<Position>? _positions;
  Timer? _heartbeat;
  DateTime _lastSent = DateTime.fromMillisecondsSinceEpoch(0);
  Position? last;
  bool permissionDenied = false;

  static const minInterval = Duration(seconds: 3);

  /// A captain waiting at a store doesn't move, so the GPS stream goes quiet;
  /// resending keeps them "recently seen" for dispatch.
  static const heartbeat = Duration(seconds: 60);

  bool get sharing => _positions != null;

  Future<void> start() async {
    if (sharing) return;
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    permissionDenied =
        permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever;
    if (permissionDenied) {
      notifyListeners();
      return;
    }
    _positions = Geolocator.getPositionStream(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 10,
      ),
    ).listen(_onPosition, onError: (_) {});
    _heartbeat = Timer.periodic(heartbeat, (_) {
      if (last != null) _send(last!);
    });
    notifyListeners();
  }

  void stop() {
    _positions?.cancel();
    _positions = null;
    _heartbeat?.cancel();
    _heartbeat = null;
    notifyListeners();
  }

  Future<void> _onPosition(Position position) async {
    last = position;
    notifyListeners();
    if (DateTime.now().difference(_lastSent) < minInterval) return;
    await _send(position);
  }

  Future<void> _send(Position position) async {
    _lastSent = DateTime.now();
    final heading = position.heading >= 0 ? position.heading : null;
    final speed = position.speed >= 0 ? position.speed : null;
    final sent = live.send({
      'type': 'location',
      'lat': position.latitude,
      'lng': position.longitude,
      'heading': ?heading,
      'speed': ?speed,
    });
    if (!sent) {
      try {
        await api.sendLocation(
          position.latitude,
          position.longitude,
          heading: heading,
          speed: speed,
        );
      } on ApiException {
        // Offline for a moment; the next fix will try again.
      }
    }
  }

  @override
  void dispose() {
    stop();
    super.dispose();
  }
}
