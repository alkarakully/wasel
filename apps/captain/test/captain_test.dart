import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:wasel_captain/screens/home_screen.dart';
import 'package:wasel_captain/state/captain_session.dart';
import 'package:wasel_captain/state/location_sharer.dart';
import 'package:wasel_captain/strings.dart';
import 'package:wasel_core/wasel_core.dart';

/// Records start/stop instead of touching the phone's GPS.
class FakeSharer extends LocationSharer {
  FakeSharer(super.api, super.live);
  bool started = false;

  @override
  Future<void> start() async => started = true;

  @override
  void stop() => started = false;
}

Map<String, dynamic> orderJson(
  int id, {
  String status = 'preparing',
  int? captain,
  String payment = 'cod',
}) => {
  'id': id,
  'vendor': 1,
  'vendor_name': 'Tigris Grill',
  'captain': captain,
  'status': status,
  'payment_type': payment,
  'delivery_address': 'Karrada, street 62',
  'total_amount': '13000',
  'delivery_pin': null,
  'vendor_location': {'lat': 33.306, 'lng': 44.419},
  'delivery_location': {'lat': 33.3045, 'lng': 44.4214},
  'captain_location': null,
  'customer_contact': null,
  'created_at': '2026-10-17T12:00:00Z',
};

class Harness {
  Harness({
    List<Map<String, dynamic>> mine = const [],
    List<Map<String, dynamic>> available = const [],
    int claimStatus = 200,
  }) {
    api = ApiClient(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        requests.add('${request.method} ${request.url.path}');
        return switch (request.url.path) {
          '/api/orders/' => http.Response(jsonEncode({'results': mine}), 200),
          '/api/dispatch/offers/current/' => http.Response('', 204),
          '/api/captain/status/' => http.Response('{"online": true}', 200),
          '/api/orders/available/' => http.Response(
            jsonEncode({'results': available}),
            200,
          ),
          _ when claimStatus != 200 => http.Response(
            jsonEncode({'error': 'already_claimed', 'detail': ''}),
            claimStatus,
          ),
          _ => http.Response(jsonEncode(orderJson(1, captain: 9)), 200),
        };
      }),
    );
    live = LiveUpdates(api);
    sharer = FakeSharer(api, live);
    session = CaptainSession(api, sharer)
      ..lang = 'en'
      ..user = User(
        id: 9,
        phone: '+9647500000999',
        name: 'Haider',
        role: 'captain',
        languagePref: 'en',
      );
  }

  final requests = <String>[];
  late final ApiClient api;
  late final LiveUpdates live;
  late final FakeSharer sharer;
  late final CaptainSession session;

  Widget app() => MultiProvider(
    providers: [
      Provider.value(value: api),
      Provider.value(value: live),
      ChangeNotifierProvider<LocationSharer>.value(value: sharer),
      ChangeNotifierProvider<BaseSession>.value(value: session),
      ChangeNotifierProvider.value(value: session),
    ],
    child: MaterialApp(
      theme: waselTheme(Brightness.light),
      home: const HomeScreen(),
    ),
  );
}

void main() {
  setUpAll(() => S.addStrings(captainStrings));

  test('cash to collect only for cash orders', () {
    expect(Order.fromJson(orderJson(1)).cashToCollect, 13000);
    expect(Order.fromJson(orderJson(1, payment: 'wallet')).cashToCollect, 0);
  });

  testWidgets(
    'going online shares GPS and shows orders waiting for a captain',
    (tester) async {
      final h = Harness(available: [orderJson(1), orderJson(2)]);
      await tester.pumpWidget(h.app());
      await tester.pumpAndSettle();

      expect(find.text('Take order'), findsNothing);
      expect(
        find.text('Go online to see orders and start sharing your location.'),
        findsOneWidget,
      );

      await tester.tap(find.byKey(const Key('online')));
      await tester.pumpAndSettle();
      expect(h.sharer.started, isTrue);
      expect(find.text('Take order'), findsNWidgets(2));
      expect(find.text('Collect cash: 13,000 IQD'), findsNWidgets(2));

      await tester.tap(find.byKey(const Key('online')));
      await tester.pumpAndSettle();
      expect(h.sharer.started, isFalse);
    },
  );

  testWidgets(
    'a current delivery replaces the list and keeps the captain online',
    (tester) async {
      final h = Harness(
        mine: [orderJson(5, status: 'out_for_delivery', captain: 9)],
        available: [orderJson(1)],
      );
      await h.session.setOnline(true);
      await tester.pumpWidget(h.app());
      await tester.pumpAndSettle();

      expect(find.text('Your current delivery'), findsOneWidget);
      expect(find.text('Take order'), findsNothing);
      final toggle = tester.widget<Switch>(find.byKey(const Key('online')));
      expect(toggle.onChanged, isNull);
    },
  );

  testWidgets('losing the race for an order explains why', (tester) async {
    final h = Harness(available: [orderJson(1)], claimStatus: 409);
    await h.session.setOnline(true);
    await tester.pumpWidget(h.app());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Take order'));
    await tester.pumpAndSettle();
    expect(h.requests, contains('POST /api/orders/1/claim/'));
    expect(find.text('Another captain took this order.'), findsOneWidget);
  });
}
