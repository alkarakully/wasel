import 'package:wasel_core/wasel_core.dart';

import 'location_sharer.dart';

/// The captain's session and whether they are taking orders.
///
/// Going online tells dispatch to offer orders and starts GPS sharing; going
/// offline stops both. Captains start offline every time the app opens, so
/// nobody shares location by accident.
class CaptainSession extends BaseSession {
  CaptainSession(super.api, this.sharer, {this.push});

  final LocationSharer sharer;

  /// Offers while the app is in the background or closed; null in tests.
  final PushService? push;
  bool online = false;

  Future<void> setOnline(bool value) async {
    online = value;
    notifyListeners();
    try {
      // Dispatch only offers orders to captains the server knows are online.
      await api.setOnline(value);
    } on ApiException {
      // GPS still flows; the next toggle tells the server again.
    }
    if (value) {
      await sharer.start();
    } else {
      sharer.stop();
    }
  }

  @override
  Future<void> onSignedIn() async => push?.start();

  @override
  Future<void> onSigningOut() async => push?.stop();

  @override
  Future<void> signOut() async {
    await setOnline(false);
    await super.signOut();
  }
}
