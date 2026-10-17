import 'package:wasel_core/wasel_core.dart';

import 'location_sharer.dart';

/// The captain's session and whether they are taking orders.
///
/// Going online starts GPS sharing; going offline stops it. Captains start
/// offline every time the app opens, so nobody shares location by accident.
class CaptainSession extends BaseSession {
  CaptainSession(super.api, this.sharer);

  final LocationSharer sharer;
  bool online = false;

  Future<void> setOnline(bool value) async {
    online = value;
    notifyListeners();
    if (value) {
      await sharer.start();
    } else {
      sharer.stop();
    }
  }

  @override
  Future<void> signOut() async {
    await setOnline(false);
    await super.signOut();
  }
}
