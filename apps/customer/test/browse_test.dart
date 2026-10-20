import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wasel_core/wasel_core.dart';
import 'package:wasel_customer/screens/home_screen.dart';
import 'package:wasel_customer/screens/search_screen.dart';
import 'package:wasel_customer/state/cart.dart';
import 'package:wasel_customer/state/session.dart';
import 'package:wasel_customer/strings.dart';

Map<String, dynamic> storeJson(
  int id,
  String name, {
  String type = 'restaurant',
  String cuisine = '',
  Map<String, dynamic>? offer,
  List<Map<String, dynamic>> matches = const [],
}) => {
  'id': id,
  'name': name,
  'type': type,
  'cuisine': cuisine,
  'is_open': true,
  'distance_km': 0.4,
  'delivery_fee': '1500',
  'country': 'IQ',
  'currency': 'IQD',
  'offer': offer,
  'matches': matches,
};

const tenOff = {
  'id': 3,
  'title': '10% off',
  'type': 'percent',
  'value': '10',
  'min_order': '0',
  'currency': 'IQD',
};

/// Answers like the backend and records every store-list query.
ApiClient fakeApi(List<Map<String, String>> queries) => ApiClient(
  client: MockClient((request) async {
    if (request.url.path == '/api/offers/') {
      return http.Response(jsonEncode({'results': []}), 200);
    }
    final p = request.url.queryParameters;
    queries.add(p);
    final stores = <Map<String, dynamic>>[
      if (p['q'] == 'kebab')
        storeJson(
          1,
          'Tigris Grill',
          cuisine: 'eastern',
          matches: [
            {'id': 9, 'name_ar': 'كباب', 'name_en': 'Iraqi kebab'},
          ],
        )
      else if (p['type'] == 'pharmacy') ...[
        if (p['offers'] != '1')
          storeJson(2, 'Al-Shifa Pharmacy', type: 'pharmacy'),
      ] else if (p['q'] == null) ...[
        storeJson(1, 'Tigris Grill', cuisine: 'eastern', offer: tenOff),
        if (p['offers'] != '1')
          storeJson(4, 'Karrada Flowers', type: 'flowers'),
      ],
    ];
    return http.Response(
      jsonEncode({'results': stores}),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  }),
);

void main() {
  setUpAll(() => S.addStrings(customerStrings));
  setUp(() => SharedPreferences.setMockInitialValues({}));

  Widget app(ApiClient api, Widget home) {
    final session = Session(api)..lang = 'en';
    return MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<BaseSession>.value(value: session),
        ChangeNotifierProvider.value(value: session),
        ChangeNotifierProvider(create: (_) => Cart()),
      ],
      child: MediaQuery(
        data: const MediaQueryData(
          size: Size(430, 1400),
          disableAnimations: true,
        ),
        child: MaterialApp(theme: waselTheme(Brightness.light), home: home),
      ),
    );
  }

  testWidgets('home shows kinds of store, offers nearby and filters by kind', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(430, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final queries = <Map<String, String>>[];
    await tester.pumpWidget(app(fakeApi(queries), const HomeScreen()));
    await tester.pumpAndSettle();

    expect(find.text('Pharmacy'), findsOneWidget);
    expect(find.text('Offers near you'), findsOneWidget);
    // The offer badge shows on the store card and in the offers row.
    expect(find.text('10% off'), findsNWidgets(2));
    expect(find.text('Flowers & gifts'), findsWidgets);
    expect(find.byKey(const Key('cuisine-rail')), findsOneWidget);

    await tester.tap(find.text('Pharmacy'));
    await tester.pumpAndSettle();
    expect(queries.last['type'], 'pharmacy');
    expect(find.text('Al-Shifa Pharmacy'), findsOneWidget);
    expect(find.text('Tigris Grill'), findsNothing);
    // Cuisines only narrow restaurants.
    expect(find.byKey(const Key('cuisine-rail')), findsNothing);
  });

  testWidgets('search finds stores by dish and shows the dishes that matched', (
    tester,
  ) async {
    final queries = <Map<String, String>>[];
    await tester.pumpWidget(app(fakeApi(queries), const SearchScreen()));
    expect(
      find.text('Search by store or dish name, or pick a kind of store.'),
      findsOneWidget,
    );

    await tester.enterText(find.byKey(const Key('search-field')), 'kebab');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    expect(queries.last['q'], 'kebab');
    expect(find.text('Tigris Grill'), findsOneWidget);
    expect(find.text('Iraqi kebab'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('search-field')), 'sushi');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    expect(find.text('Nothing near you matches “sushi”.'), findsOneWidget);
  });
}
