import 'package:geolocator/geolocator.dart';
import 'package:wasel_core/wasel_core.dart';

import '../config.dart';

/// The customer's session, plus where to deliver.
class Session extends BaseSession {
  Session(super.api);

  GeoPoint deliveryPoint = const GeoPoint(
    Config.fallbackLat,
    Config.fallbackLng,
  );
  bool usingDeviceLocation = false;

  // Ask for location only once someone is signed in and about to browse.
  @override
  Future<void> onSignedIn() => refreshLocation();

  /// Uses the phone's location when allowed; otherwise keeps the fallback spot.
  Future<void> refreshLocation() async {
    try {
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return;
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          timeLimit: Duration(seconds: 10),
        ),
      );
      deliveryPoint = GeoPoint(position.latitude, position.longitude);
      usingDeviceLocation = true;
      notifyListeners();
    } catch (_) {
      // Location services off or timed out: stay on the fallback spot.
    }
  }
}
