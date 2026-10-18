import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/services.dart';

/// The new-order ring: the same four-note chime as the web portal, repeating
/// until someone accepts, rejects or taps "Stop ringing". It plays even when
/// the tablet's silent switch is on; a missed order costs the store money.
class OrderAlarm {
  AudioPlayer? _player;
  bool _ringing = false;

  bool get ringing => _ringing;

  Future<void> start() async {
    if (_ringing) return;
    _ringing = true;
    HapticFeedback.heavyImpact();
    try {
      final player = _player ??= AudioPlayer();
      await player.setAudioContext(
        AudioContextConfig(respectSilence: false, stayAwake: true).build(),
      );
      await player.setReleaseMode(ReleaseMode.loop);
      await player.play(AssetSource('sounds/new_order.wav'), volume: 1);
    } catch (_) {
      // No sound device (simulator, tests): the screen still flashes.
    }
  }

  Future<void> stop() async {
    if (!_ringing) return;
    _ringing = false;
    try {
      await _player?.stop();
    } catch (_) {}
  }
}

/// For tests: remembers whether it would be ringing.
class SilentAlarm extends OrderAlarm {
  bool _on = false;

  @override
  bool get ringing => _on;

  @override
  Future<void> start() async => _on = true;

  @override
  Future<void> stop() async => _on = false;
}
