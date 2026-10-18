import 'dart:async';
import 'dart:io' show Platform;

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'api/api_client.dart';

/// Firebase settings from build flags, so no config files live in the repo:
///   --dart-define=FIREBASE_API_KEY=... --dart-define=FIREBASE_PROJECT_ID=...
///   --dart-define=FIREBASE_SENDER_ID=... --dart-define=FIREBASE_APP_ID=...
/// Each app (customer, captain) and platform has its own FIREBASE_APP_ID.
class PushConfig {
  static const apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const senderId = String.fromEnvironment('FIREBASE_SENDER_ID');
  static const appId = String.fromEnvironment('FIREBASE_APP_ID');

  /// Null when push isn't set up for this build; the app then runs without it.
  static FirebaseOptions? get options => apiKey.isEmpty || appId.isEmpty
      ? null
      : const FirebaseOptions(
          apiKey: apiKey,
          appId: appId,
          messagingSenderId: senderId,
          projectId: projectId,
        );
}

/// Registers this phone for push notifications and reports taps on them.
///
/// The live socket covers the app while it's open; pushes cover it when it's
/// in the background or closed. [onOpen] gets a tapped notification's data,
/// e.g. {"kind": "offer", "offer_id": "3", "order_id": "12"}.
class PushService {
  PushService(this.api, {required this.app});

  final ApiClient api;

  /// "customer" or "captain": which app's notifications this phone wants.
  final String app;

  void Function(Map<String, dynamic> data)? onOpen;

  String? _fid;
  final _subscriptions = <StreamSubscription>[];
  bool _started = false;

  bool get enabled => PushConfig.options != null;

  Future<void> start() async {
    if (_started || !enabled) return;
    _started = true;
    try {
      if (Firebase.apps.isEmpty) {
        await Firebase.initializeApp(options: PushConfig.options);
      }
      final messaging = FirebaseMessaging.instance;
      final permission = await messaging.requestPermission();
      if (permission.authorizationStatus == AuthorizationStatus.denied) return;
      // In the foreground the live socket already shows everything.
      await messaging.setForegroundNotificationPresentationOptions(
        alert: false,
        sound: false,
        badge: false,
      );

      _subscriptions.addAll([
        FirebaseMessaging.onMessageOpenedApp.listen(
          (message) => onOpen?.call(message.data),
        ),
        // FCM sends to the app instance's Firebase Installation ID (FID).
        messaging.onRegistered.listen(_register),
        messaging.onUnregistered.listen(_forget),
      ]);
      final opened = await messaging.getInitialMessage();
      if (opened != null) onOpen?.call(opened.data);
      // Emits the FID on onRegistered, even when already registered.
      await messaging.register();
    } catch (error) {
      // Push is a bonus; never block the app over it.
      debugPrint('Push setup failed: $error');
    }
  }

  Future<void> _register(String fid) async {
    _fid = fid;
    try {
      await api.registerDevice(
        fid,
        platform: Platform.isIOS ? 'ios' : 'android',
        app: app,
      );
    } on ApiException catch (error) {
      debugPrint('Push device not registered: ${error.code}');
    }
  }

  Future<void> _forget(String fid) async {
    if (_fid == fid) _fid = null;
    try {
      await api.unregisterDevice(fid);
    } on ApiException {
      // The server drops dead devices on its own.
    }
  }

  /// Call before signing out, while the API token still works.
  Future<void> stop() async {
    for (final subscription in _subscriptions) {
      await subscription.cancel();
    }
    _subscriptions.clear();
    _started = false;
    final fid = _fid;
    _fid = null;
    if (fid != null) await _forget(fid);
  }
}
