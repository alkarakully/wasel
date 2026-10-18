import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:wasel_core/wasel_core.dart';

/// The store owner's session. While signed in, the tablet stays awake (it
/// sits on the counter all day) and registers for new-order pushes.
class StoreSession extends BaseSession {
  StoreSession(super.api, {this.push, this.keepAwake = true});

  /// New orders while the app is in the background or closed; null in tests.
  final PushService? push;
  final bool keepAwake;

  @override
  Future<void> onSignedIn() async {
    if (keepAwake) await WakelockPlus.enable();
    await push?.start();
  }

  @override
  Future<void> onSigningOut() async {
    if (keepAwake) await WakelockPlus.disable();
    await push?.stop();
  }
}
