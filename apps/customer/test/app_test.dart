import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wasel_customer/api/api_client.dart';
import 'package:wasel_customer/api/models.dart';
import 'package:wasel_customer/l10n.dart';
import 'package:wasel_customer/screens/login_screen.dart';
import 'package:wasel_customer/screens/product_sheet.dart';
import 'package:wasel_customer/state/cart.dart';
import 'package:wasel_customer/state/session.dart';
import 'package:wasel_customer/theme.dart';

Modifier modifier(int id, String group, int delta, {bool required = false}) =>
    Modifier(
      id: id,
      groupName: group,
      nameAr: 'خيار $id',
      nameKu: '',
      nameEn: 'Option $id',
      priceDelta: delta,
      isRequired: required,
    );

final kebab = Product(
  id: 1,
  nameAr: 'كباب',
  nameKu: '',
  nameEn: 'Kebab',
  menuSection: 'Grill',
  price: 8000,
  unitType: 'item',
  isAvailable: true,
  modifiers: [
    modifier(10, 'Size', 0, required: true),
    modifier(11, 'Size', 2000, required: true),
    modifier(12, 'Extras', 500),
  ],
);

final tomatoes = Product(
  id: 2,
  nameAr: 'طماطة',
  nameKu: '',
  nameEn: 'Tomatoes',
  menuSection: 'Veg',
  price: 1500,
  unitType: 'kg',
  isAvailable: true,
  modifiers: const [],
);

final store = Vendor(
  id: 7,
  name: 'Tahrir Grill',
  type: 'restaurant',
  cuisine: 'eastern',
  isOpen: true,
);

Widget wrap(Widget child, {Session? session, ApiClient? api}) {
  final client =
      api ??
      ApiClient(client: MockClient((_) async => http.Response('{}', 404)));
  return MultiProvider(
    providers: [
      Provider.value(value: client),
      ChangeNotifierProvider.value(
        value: session ?? (Session(client)..lang = 'en'),
      ),
      ChangeNotifierProvider(create: (_) => Cart()),
    ],
    child: MaterialApp(theme: waselTheme(Brightness.light), home: child),
  );
}

/// Phone-sized screen (iPhone 16-ish) instead of the 800x600 test default.
void usePhoneScreen(WidgetTester tester) {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}

void main() {
  group('Cart', () {
    test('same product and options share a line; different options do not', () {
      final cart = Cart();
      cart.add(
        store,
        CartLine(product: kebab, quantity: 1, modifiers: [kebab.modifiers[1]]),
      );
      cart.add(
        store,
        CartLine(product: kebab, quantity: 2, modifiers: [kebab.modifiers[1]]),
      );
      cart.add(
        store,
        CartLine(product: kebab, quantity: 1, modifiers: [kebab.modifiers[0]]),
      );
      expect(cart.lines.length, 2);
      expect(cart.lines.first.quantity, 3);
      expect(cart.subtotal, 3 * 10000 + 8000);
    });

    test('per-kg items price by weight and send three decimals', () {
      final line = CartLine(
        product: tomatoes,
        quantity: 1.5,
        modifiers: const [],
      );
      expect(line.lineTotal, 2250);
      expect(line.toJson()['quantity'], '1.500');
    });

    test('removing the last unit empties the cart', () {
      final cart = Cart();
      cart.add(
        store,
        CartLine(product: tomatoes, quantity: 0.5, modifiers: const []),
      );
      cart.changeQuantity(cart.lines.first, -0.5);
      expect(cart.isEmpty, isTrue);
      expect(cart.vendorId, isNull);
    });

    test('knows when an item comes from another store', () {
      final cart = Cart()
        ..add(
          store,
          CartLine(product: tomatoes, quantity: 1, modifiers: const []),
        );
      expect(cart.belongsToOtherStore(7), isFalse);
      expect(cart.belongsToOtherStore(8), isTrue);
    });
  });

  test('money uses thousands separators and the local currency', () {
    expect(S('en').money(18000), '18,000 IQD');
    expect(S('ar').money(1250), '1,250 د.ع');
    expect(S('en').money(-2325), '-2,325 IQD');
  });

  testWidgets(
    'product sheet waits for required options and shows the line price',
    (tester) async {
      await tester.pumpWidget(
        wrap(Scaffold(body: ProductSheet(product: kebab))),
      );
      final add = find.byKey(const Key('add-to-cart'));
      expect(tester.widget<FilledButton>(add).onPressed, isNull);

      await tester.tap(find.text('Option 11'));
      await tester.tap(find.text('Option 12'));
      await tester.pump();
      expect(tester.widget<FilledButton>(add).onPressed, isNotNull);
      expect(find.text('Add to cart · 10,500 IQD'), findsOneWidget);
    },
  );

  testWidgets('login sends a code, then signs in with it', (tester) async {
    usePhoneScreen(tester);
    SharedPreferences.setMockInitialValues({});
    final requests = <String>[];
    final api = ApiClient(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        requests.add('${request.method} ${request.url.path} ${request.body}');
        if (request.url.path == '/api/auth/otp/request/') {
          return http.Response(
            jsonEncode({
              'phone': '+9647701234567',
              'channel': 'whatsapp',
              'resend_in': 60,
            }),
            200,
          );
        }
        return http.Response(
          jsonEncode({
            'token': 'abc',
            'is_new_user': true,
            'user': {
              'id': 1,
              'phone': '+9647701234567',
              'name': '',
              'role': 'customer',
              'language_pref': 'ar',
            },
          }),
          201,
        );
      }),
    );
    final session = Session(api)..lang = 'en';
    await tester.pumpWidget(
      wrap(const LoginScreen(), session: session, api: api),
    );

    await tester.enterText(find.byKey(const Key('phone')), '0770 123 4567');
    await tester.tap(find.byKey(const Key('send-code')));
    await tester.pumpAndSettle();
    expect(find.text('Enter the code'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('code')), '482913');
    await tester.pumpAndSettle();
    expect(session.signedIn, isTrue);
    expect(session.user!.phone, '+9647701234567');
    expect(requests.last, contains('"code":"482913"'));

    // Leave no countdown timer running after the test.
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('a rejected number shows the error under the field', (
    tester,
  ) async {
    usePhoneScreen(tester);
    final api = ApiClient(
      baseUrl: 'http://test',
      client: MockClient(
        (_) async => http.Response(
          jsonEncode({
            'phone': ['Enter an Iraqi mobile number'],
          }),
          400,
        ),
      ),
    );
    await tester.pumpWidget(
      wrap(const LoginScreen(), api: api, session: Session(api)..lang = 'en'),
    );
    await tester.enterText(find.byKey(const Key('phone')), '12345');
    await tester.tap(find.byKey(const Key('send-code')));
    await tester.pumpAndSettle();
    expect(find.textContaining("That number isn't valid"), findsOneWidget);
  });
}
