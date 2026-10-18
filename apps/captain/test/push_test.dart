import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wasel_captain/state/captain_session.dart';
import 'package:wasel_core/wasel_core.dart';

import 'captain_test.dart' show FakeSharer;

/// Records start/stop instead of talking to Firebase.
class FakePush extends PushService {
  FakePush(super.api) : super(app: 'captain');
  final calls = <String>[];

  @override
  Future<void> start() async => calls.add('start');

  @override
  Future<void> stop() async => calls.add('stop');
}

void main() {
  test('push starts after sign-in and stops before sign-out', () async {
    SharedPreferences.setMockInitialValues({});
    final requests = <String>[];
    final api = ApiClient(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        requests.add('${request.method} ${request.url.path}');
        return http.Response('', 204);
      }),
    );
    final push = FakePush(api);
    final session = CaptainSession(
      api,
      FakeSharer(api, LiveUpdates(api)),
      push: push,
    );

    await session.signIn(
      'abc',
      User(
        id: 9,
        phone: '+9647500000999',
        name: '',
        role: 'captain',
        languagePref: 'ar',
      ),
    );
    expect(push.calls, ['start']);

    await session.signOut();
    expect(push.calls, ['start', 'stop']);
    // Push stops while the token still works, then the session logs out.
    expect(requests.last, 'POST /api/auth/logout/');
  });

  test('push is off when the build has no Firebase settings', () {
    expect(PushConfig.options, isNull);
    expect(
      PushService(ApiClient(baseUrl: 'http://test'), app: 'captain').enabled,
      isFalse,
    );
  });
}
