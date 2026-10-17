import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import 'api/api_client.dart';

/// One socket per signed-in user, reconnecting with backoff.
/// Screens listen to [events] and pick the messages they care about.
class LiveUpdates {
  LiveUpdates(this.api);

  final ApiClient api;
  final _events = StreamController<Map<String, dynamic>>.broadcast();
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  Timer? _ping;
  Timer? _reconnect;
  int _retry = 0;
  bool _wanted = false;

  Stream<Map<String, dynamic>> get events => _events.stream;

  bool _connected = false;
  bool get isConnected => _channel != null && _connected;

  /// Sends a message over the socket if it's open; returns false otherwise.
  bool send(Map<String, dynamic> message) {
    if (!isConnected) return false;
    _channel!.sink.add(jsonEncode(message));
    return true;
  }

  void start() {
    if (_wanted) return;
    _wanted = true;
    _connect();
  }

  void stop() {
    _wanted = false;
    _reconnect?.cancel();
    _ping?.cancel();
    _subscription?.cancel();
    _channel?.sink.close();
    _channel = null;
    _connected = false;
  }

  void _connect() {
    if (!_wanted || api.token == null) return;
    final channel = WebSocketChannel.connect(api.socketUri());
    _channel = channel;
    _subscription = channel.stream.listen(
      (raw) {
        final message = jsonDecode(raw as String) as Map<String, dynamic>;
        if (message['type'] == 'connected') {
          _retry = 0;
          _connected = true;
        }
        _events.add(message);
      },
      onDone: () => _scheduleReconnect(channel.closeCode),
      onError: (_) => _scheduleReconnect(null),
      cancelOnError: true,
    );
    _ping?.cancel();
    _ping = Timer.periodic(const Duration(seconds: 25), (_) {
      _channel?.sink.add(jsonEncode({'type': 'ping'}));
    });
  }

  void _scheduleReconnect(int? closeCode) {
    _connected = false;
    _ping?.cancel();
    if (!_wanted || closeCode == 4401) return; // signed out: don't retry
    final seconds = [1, 2, 4, 8, 16, 30][_retry.clamp(0, 5)];
    _retry++;
    _reconnect?.cancel();
    _reconnect = Timer(Duration(seconds: seconds), _connect);
  }
}
