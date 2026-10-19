import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:wasel_core/wasel_core.dart';

/// The store owner's session. While signed in, the tablet stays awake (it
/// sits on the counter all day) and registers for new-order pushes.
///
/// Team invites are answered at sign-in: until [invites] is empty the app
/// shows them instead of the board.
class StoreSession extends BaseSession {
  StoreSession(super.api, {this.push, this.keepAwake = true});

  /// New orders while the app is in the background or closed; null in tests.
  final PushService? push;
  final bool keepAwake;

  /// Invites waiting for an answer; null until checked after signing in.
  List<StoreInvite>? invites;

  /// Called after joining a store's team, so the board loads it.
  void Function()? onJoinedStore;

  @override
  Future<void> onSignedIn() async {
    await loadInvites();
    if (keepAwake) await WakelockPlus.enable();
    await push?.start();
  }

  @override
  Future<void> onSigningOut() async {
    invites = null;
    if (keepAwake) await WakelockPlus.disable();
    await push?.stop();
  }

  Future<void> loadInvites() async {
    try {
      invites = await api.storeInvites();
    } on ApiException {
      // Offline: let them in to the board; invites come back next sign-in.
      invites ??= [];
    }
    notifyListeners();
  }

  /// Accept or decline one invite. Declining the last one on an account that
  /// isn't a store account (a new number) signs out, since there's nothing to run.
  Future<void> answerInvite(StoreInvite invite, {required bool accept}) async {
    await api.answerStoreInvite(invite.id, accept: accept);
    invites = [...?invites]..removeWhere((i) => i.id == invite.id);
    if (accept) {
      user = await api.me();
      onJoinedStore?.call();
    }
    if (invites!.isEmpty && user?.role != 'vendor') {
      await signOut();
      return;
    }
    notifyListeners();
  }
}
