import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:wasel_captain/screens/offer_sheet.dart';
import 'package:wasel_captain/strings.dart';
import 'package:wasel_core/wasel_core.dart';

import 'captain_test.dart' show orderJson;

DispatchOffer offer({Duration left = const Duration(seconds: 30)}) =>
    DispatchOffer.fromJson({
      'id': 5,
      'order': orderJson(1),
      'distance_km': 0.48,
      'expires_at': DateTime.now().add(left).toIso8601String(),
    });

/// Opens the sheet from a button and records what it popped with.
class Opener extends StatelessWidget {
  const Opener({
    super.key,
    required this.offer,
    required this.closed,
    required this.result,
  });
  final DispatchOffer offer;
  final Stream<int> closed;
  final Completer<Order?> result;

  @override
  Widget build(BuildContext context) => Scaffold(
    body: TextButton(
      onPressed: () async => result.complete(
        await showModalBottomSheet<Order>(
          context: context,
          builder: (_) => OfferSheet(offer: offer, closed: closed),
        ),
      ),
      child: const Text('open'),
    ),
  );
}

void main() {
  setUpAll(() => S.addStrings(captainStrings));

  Future<(Completer<Order?>, List<String>)> open(
    WidgetTester tester,
    DispatchOffer offer, {
    Stream<int> closed = const Stream.empty(),
  }) async {
    final requests = <String>[];
    final api = ApiClient(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        requests.add('${request.method} ${request.url.path}');
        return request.url.path.endsWith('/accept/')
            ? http.Response(jsonEncode(orderJson(1, captain: 9)), 200)
            : http.Response('', 204);
      }),
    );
    final session = BaseSession(api)..lang = 'en';
    final result = Completer<Order?>();
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          Provider.value(value: api),
          ChangeNotifierProvider<BaseSession>.value(value: session),
        ],
        child: MaterialApp(
          home: Opener(offer: offer, closed: closed, result: result),
        ),
      ),
    );
    await tester.tap(find.text('open'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    return (result, requests);
  }

  testWidgets('shows the offer and takes the order', (tester) async {
    final (result, requests) = await open(tester, offer());
    expect(find.text('New order for you'), findsOneWidget);
    expect(find.text('Store is 0.5 km away'), findsOneWidget);
    expect(find.text('Collect cash: 13,000 IQD'), findsOneWidget);

    await tester.tap(find.byKey(const Key('accept-offer')));
    await tester.pumpAndSettle();
    expect(requests, ['POST /api/dispatch/offers/5/accept/']);
    expect((await result.future)!.captainId, 9);
  });

  testWidgets('skipping declines and closes', (tester) async {
    final (result, requests) = await open(tester, offer());
    await tester.tap(find.byKey(const Key('decline-offer')));
    await tester.pumpAndSettle();
    expect(requests, ['POST /api/dispatch/offers/5/decline/']);
    expect(await result.future, isNull);
  });

  testWidgets('closes when the server withdraws the offer', (tester) async {
    final closed = StreamController<int>.broadcast();
    final (result, _) = await open(tester, offer(), closed: closed.stream);
    closed.add(99); // another offer: stays open
    await tester.pump();
    expect(find.text('New order for you'), findsOneWidget);
    closed.add(5);
    await tester.pumpAndSettle();
    expect(await result.future, isNull);
    await closed.close();
  });

  testWidgets('closes by itself when time runs out', (tester) async {
    final (result, _) = await open(tester, offer(left: const Duration(milliseconds: 600)));
    // The countdown reads the real clock, so let real time pass.
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 900)));
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pumpAndSettle();
    expect(await result.future, isNull);
  });
}
