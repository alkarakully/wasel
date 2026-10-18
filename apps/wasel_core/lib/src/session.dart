import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api/api_client.dart';
import 'api/models.dart';

/// Who is signed in and which language they use. Apps extend this and
/// override [onSignedIn] for app-specific setup (location, GPS sharing).
class BaseSession extends ChangeNotifier {
  BaseSession(this.api);

  final ApiClient api;

  bool loaded = false;
  String lang = 'ar';
  User? user;

  bool get signedIn => api.token != null;

  /// Runs after a stored session is restored or a new sign-in completes.
  @protected
  Future<void> onSignedIn() async {}

  /// Runs before signing out, while the API token still works.
  @protected
  Future<void> onSigningOut() async {}

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
    if (signedIn) await onSignedIn();
  }

  Future<void> signIn(String token, User signedInUser) async {
    api.token = token;
    user = signedInUser;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', token);
    notifyListeners();
    await onSignedIn();
  }

  Future<void> signOut() async {
    await onSigningOut();
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
    if (!signedIn) return;
    try {
      await api.updateLanguage(value);
    } on ApiException {
      // Kept locally; the server catches up next time.
    }
  }
}
