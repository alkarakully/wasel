import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../config.dart';

/// Who is signed in, their language, and where to deliver.
class Session extends ChangeNotifier {
  Session(this.api);

  final ApiClient api;

  bool loaded = false;
  String lang = 'ar';
  User? user;
  GeoPoint deliveryPoint = const GeoPoint(
    Config.fallbackLat,
    Config.fallbackLng,
  );
  bool usingDeviceLocation = false;

  bool get signedIn => api.token != null;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    lang = prefs.getString('lang') ?? 'ar';
    api.token = prefs.getString('token');
    if (api.token != null) {
      try {
        user = await api.me();
      } on ApiException catch (error) {
        // An expired token signs out; a network error keeps the session.
        if (error.code == 'unauthorized') await _clear(prefs);
      }
    }
    loaded = true;
    notifyListeners();
    // Ask for location only once someone is signed in and about to browse.
    if (signedIn) await refreshLocation();
  }

  Future<void> signIn(String token, User signedInUser) async {
    api.token = token;
    user = signedInUser;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', token);
    notifyListeners();
    await refreshLocation();
  }

  Future<void> signOut() async {
    try {
      await api.logout();
    } on ApiException {
      // Sign out locally even if the server can't be reached.
    }
    await _clear(await SharedPreferences.getInstance());
    notifyListeners();
  }

  Future<void> _clear(SharedPreferences prefs) async {
    api.token = null;
    user = null;
    await prefs.remove('token');
  }

  Future<void> setLang(String value) async {
    lang = value;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('lang', value);
  }

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
