import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wasel_core/wasel_core.dart';

/// Phone-sized screen instead of the 800x600 test default.
void usePhoneScreen(WidgetTester tester) {
  tester.view.physicalSize = const Size(1170, 2532);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
}

const user = {
  'id': 1,
  'phone': '+9647701234567',
  'name': '',
  'role': 'customer',
  'language_pref': 'ar',
};

ApiClient fakeApi(List<String> log, {String role = 'customer'}) => ApiClient(
  baseUrl: 'http://test',
  client: MockClient((request) async {
    log.add('${request.method} ${request.url.path} ${request.body}');
    switch (request.url.path) {
      case '/api/auth/otp/request/':
        return http.Response(
          jsonEncode({
            'phone': '+9647701234567',
            'channel': 'whatsapp',
            'resend_in': 60,
          }),
          200,
        );
      case '/api/auth/otp/verify/':
        return http.Response(
          jsonEncode({
            'token': 'abc',
            'is_new_user': false,
            'user': {...user, 'role': role},
          }),
          200,
        );
      default:
        return http.Response('', 204);
    }
  }),
);

Widget wrap(Widget child, BaseSession session) => MultiProvider(
  providers: [
    Provider.value(value: session.api),
    ChangeNotifierProvider<BaseSession>.value(value: session),
  ],
  child: MaterialApp(theme: waselTheme(Brightness.light), home: child),
);

Future<void> logIn(WidgetTester tester) async {
  await tester.enterText(find.byKey(const Key('phone')), '0770 123 4567');
  await tester.tap(find.byKey(const Key('send-code')));
  await tester.pumpAndSettle();
  await tester.enterText(find.byKey(const Key('code')), '482913');
  await tester.pumpAndSettle();
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('money uses thousands separators and the local currency', () {
    expect(S('en').money(18000), '18,000 IQD');
    expect(S('ar').money(1250), '1,250 د.ع');
    expect(S('en').money(-2325), '-2,325 IQD');
  });

  test('app strings override shared ones and fall back to English', () {
    S.addStrings({
      'en': {'only_en': 'English only'},
      'ar': {'retry': 'جرّب'},
    });
    expect(S('ar').t('retry'), 'جرّب');
    expect(S('ku').t('only_en'), 'English only');
    expect(S('en').t('orderNumber', {'id': 7}), 'Order #7');
  });

  testWidgets('login sends a code, then signs in with it', (tester) async {
    usePhoneScreen(tester);
    final log = <String>[];
    final session = BaseSession(fakeApi(log))..lang = 'en';
    await tester.pumpWidget(wrap(const LoginScreen(), session));

    await logIn(tester);
    expect(session.signedIn, isTrue);
    expect(session.user!.phone, '+9647701234567');
    expect(log.last, contains('"code":"482913"'));
    await tester.pumpWidget(const SizedBox()); // stop the resend countdown
  });

  testWidgets('a pasted message or Arabic digits still give the code', (
    tester,
  ) async {
    usePhoneScreen(tester);
    final log = <String>[];
    final session = BaseSession(fakeApi(log))..lang = 'en';
    await tester.pumpWidget(wrap(const LoginScreen(), session));

    await tester.enterText(find.byKey(const Key('phone')), '0770 123 4567');
    await tester.tap(find.byKey(const Key('send-code')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('code')),
      'Wasel login code for +9647701234567: ٤٨٢٩١٣',
    );
    await tester.pumpAndSettle();

    expect(session.signedIn, isTrue);
    expect(log.last, contains('"code":"482913"'));
    await tester.pumpWidget(const SizedBox()); // stop the resend countdown
  });

  testWidgets('an app can refuse accounts it is not for', (tester) async {
    usePhoneScreen(tester);
    final log = <String>[];
    final session = BaseSession(fakeApi(log))..lang = 'en';
    await tester.pumpWidget(
      wrap(
        LoginScreen(
          acceptUser: (u) => u.role == 'captain',
          rejectedError: 'err_not_allowed',
        ),
        session,
      ),
    );

    await logIn(tester);
    expect(session.signedIn, isFalse);
    expect(find.text("This account can't use this app."), findsOneWidget);
    expect(log.last, startsWith('POST /api/auth/logout/'));
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
      wrap(const LoginScreen(), BaseSession(api)..lang = 'en'),
    );
    await tester.enterText(find.byKey(const Key('phone')), '12345');
    await tester.tap(find.byKey(const Key('send-code')));
    await tester.pumpAndSettle();
    expect(find.textContaining("That number isn't valid"), findsOneWidget);
  });
}
