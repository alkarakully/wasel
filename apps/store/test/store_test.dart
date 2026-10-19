import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:pdf/pdf.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:wasel_core/wasel_core.dart';
import 'package:wasel_store/print/printer.dart';
import 'package:wasel_store/print/slips.dart';
import 'package:wasel_store/screens/home_screen.dart';
import 'package:wasel_store/screens/invites_screen.dart';
import 'package:wasel_store/state/alarm.dart';
import 'package:wasel_store/state/board.dart';
import 'package:wasel_store/state/store_session.dart';
import 'package:wasel_store/strings.dart';

/// Live socket the test drives by hand.
class FakeLive extends LiveUpdates {
  FakeLive(super.api);
  final controller = StreamController<Map<String, dynamic>>.broadcast();

  @override
  Stream<Map<String, dynamic>> get events => controller.stream;
}

Map<String, dynamic> orderJson(
  int id, {
  String status = 'received',
  String payment = 'cod',
  int? captain,
}) => {
  'id': id,
  'vendor': 1,
  'vendor_name': 'Tigris Grill',
  'captain': captain,
  'status': status,
  'payment_type': payment,
  'delivery_address': 'Karrada',
  'total_amount': '13000',
  'delivery_pin': null,
  'vendor_location': null,
  'delivery_location': null,
  'captain_location': null,
  'created_at': DateTime.now()
      .subtract(const Duration(minutes: 4))
      .toIso8601String(),
  'estimated_ready_at': status == 'preparing'
      ? DateTime.now().add(const Duration(minutes: 12)).toIso8601String()
      : null,
  'items': [
    {
      'name': {'ar': 'كباب', 'ku': '', 'en': 'Kebab'},
      'quantity': '2.000',
      'unit_type': 'item',
      'modifiers': [
        {
          'name': {'ar': 'كبير', 'ku': '', 'en': 'Large'},
        },
      ],
    },
  ],
};

final storeJson = {
  'id': 1,
  'name': 'Tigris Grill',
  'type': 'restaurant',
  'cuisine': 'eastern',
  'is_open': true,
  'products': [
    {
      'id': 11,
      'name_ar': 'كباب',
      'name_ku': '',
      'name_en': 'Kebab',
      'menu_section': 'Grill',
      'price': '9000',
      'unit_type': 'item',
      'is_available': true,
      'modifiers': [],
    },
  ],
};

http.Response json(Object data) => http.Response.bytes(
  utf8.encode(jsonEncode(data)),
  200,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

class Harness {
  Harness({List<Map<String, dynamic>>? board}) : board = board ?? [] {
    api = ApiClient(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        requests.add('${request.method} ${request.url.path} ${request.body}');
        final path = request.url.path;
        if (path == '/api/vendors/mine/') {
          return json([storeJson]);
        }
        if (path == '/api/orders/') {
          return json({'results': this.board});
        }
        final step = RegExp(r'/api/orders/(\d+)/(accept|reject|ready)/');
        final match = step.firstMatch(path);
        if (match != null) {
          final status = {
            'accept': 'preparing',
            'reject': 'cancelled',
            'ready': 'ready',
          }[match.group(2)]!;
          return json(orderJson(int.parse(match.group(1)!), status: status));
        }
        if (path == '/api/products/11/availability/') {
          final on = jsonDecode(request.body)['is_available'];
          return json({'id': 11, 'is_available': on});
        }
        return http.Response('', 204);
      }),
    );
    api.token = 'abc';
    live = FakeLive(api);
    session = StoreSession(api, keepAwake: false)
      ..lang = 'en'
      ..loaded = true;
    storeBoard = StoreBoard(api, live);
    storeBoard.addListener(
      () => storeBoard.ringing ? alarm.start() : alarm.stop(),
    );
  }

  final List<Map<String, dynamic>> board;
  final requests = <String>[];
  late final ApiClient api;
  late final FakeLive live;
  late final StoreSession session;
  late final StoreBoard storeBoard;
  final alarm = SilentAlarm();
  final printer = FakePrinter();

  Widget app() => MultiProvider(
    providers: [
      Provider<ApiClient>.value(value: api),
      Provider<LiveUpdates>.value(value: live),
      ChangeNotifierProvider<BaseSession>.value(value: session),
      ChangeNotifierProvider.value(value: session),
      ChangeNotifierProvider.value(value: storeBoard),
      Provider<OrderPrinter>.value(value: printer),
    ],
    child: MediaQuery(
      data: const MediaQueryData(disableAnimations: true),
      child: MaterialApp(
        theme: waselTheme(Brightness.light),
        home: const HomeScreen(),
      ),
    ),
  );
}

/// A landscape iPad.
void useTablet(WidgetTester tester) {
  tester.view.physicalSize = const Size(2732, 2048);
  tester.view.devicePixelRatio = 2;
  addTearDown(tester.view.reset);
}

Future<Harness> open(
  WidgetTester tester, {
  List<Map<String, dynamic>>? board,
}) async {
  useTablet(tester);
  final h = Harness(board: board);
  h.storeBoard.start();
  await tester.pumpWidget(h.app());
  await tester.pumpAndSettle();
  return h;
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    S.addStrings(storeStrings);
  });

  testWidgets('shows the three columns with what to cook', (tester) async {
    final h = await open(
      tester,
      board: [
        orderJson(1),
        orderJson(2, status: 'preparing'),
        orderJson(3, status: 'ready', captain: 9),
      ],
    );
    expect(find.text('New orders'), findsOneWidget);
    expect(find.text('Preparing'), findsOneWidget);
    expect(find.text('Ready for pickup'), findsOneWidget);
    expect(find.text('Kebab'), findsNWidgets(3));
    expect(find.text('Large'), findsNWidgets(3));
    expect(find.text('2×'), findsNWidgets(3));
    expect(find.text('Ready in 11 min'), findsOneWidget);
    expect(find.text('Captain on the way to pick up'), findsOneWidget);
    expect(h.alarm.ringing, isTrue);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('accepting sends the prep time and stops the ring', (
    tester,
  ) async {
    final h = await open(tester, board: [orderJson(1)]);
    expect(h.alarm.ringing, isTrue);

    await tester.tap(find.byKey(const Key('prep-20')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('accept-1')));
    await tester.pumpAndSettle();

    expect(h.requests.last, contains('POST /api/orders/1/accept/'));
    expect(h.requests.last, contains('"prep_minutes":20'));
    expect(h.alarm.ringing, isFalse);
    expect(find.byKey(const Key('ready-1')), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('rejecting asks for a reason the customer will see', (
    tester,
  ) async {
    final h = await open(tester, board: [orderJson(1)]);
    await tester.tap(find.byKey(const Key('reject-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text("We're too busy right now"));
    await tester.pump();
    await tester.tap(find.byKey(const Key('confirm-reject')));
    await tester.pumpAndSettle();

    expect(h.requests.last, contains('POST /api/orders/1/reject/'));
    expect(h.requests.last, contains("We're too busy right now"));
    expect(find.text('Kebab'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('a new order over the socket rings until silenced', (
    tester,
  ) async {
    final h = await open(tester);
    expect(h.alarm.ringing, isFalse);

    h.live.controller.add({'type': 'order.updated', 'order': orderJson(5)});
    await tester.pumpAndSettle();
    expect(find.text('#5'), findsOneWidget);
    expect(h.alarm.ringing, isTrue);

    await tester.tap(find.byKey(const Key('mute')));
    await tester.pumpAndSettle();
    expect(h.alarm.ringing, isFalse);

    // A newer order rings again.
    h.live.controller.add({'type': 'order.updated', 'order': orderJson(6)});
    await tester.pumpAndSettle();
    expect(h.alarm.ringing, isTrue);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('losing the connection shows a banner', (tester) async {
    final h = await open(tester);
    h.live.controller.add({'type': 'disconnected'});
    await tester.pumpAndSettle();
    expect(find.text('Connection lost. Reconnecting...'), findsOneWidget);

    h.live.controller.add({'type': 'connected'});
    await tester.pumpAndSettle();
    expect(find.text('Connection lost. Reconnecting...'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('menu switches mark items out of stock', (tester) async {
    final h = await open(tester);
    await tester.tap(find.text('Menu'));
    await tester.pumpAndSettle();
    expect(find.text('In stock'), findsOneWidget);

    await tester.tap(find.byKey(const Key('stock-11')));
    await tester.pumpAndSettle();
    expect(
      h.requests.last,
      contains('POST /api/products/11/availability/ {"is_available":false}'),
    );
    expect(find.text('Out of stock'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('prints from the card, and on accept when asked to', (
    tester,
  ) async {
    final h = await open(tester, board: [orderJson(1)]);
    await tester.tap(find.byKey(const Key('print-1')));
    await tester.pumpAndSettle();
    expect(h.printer.printed, [1]);

    await tester.tap(find.byKey(const Key('auto-print')));
    await tester.pumpAndSettle();
    expect(h.storeBoard.autoPrint, isTrue);
    await tester.tap(find.byKey(const Key('accept-1')));
    await tester.pumpAndSettle();
    expect(h.printer.printed, [1, 1]);
    await tester.pumpWidget(const SizedBox());
  });

  test('slips say what to cook and pack, never the PIN or phone', () {
    final order = Order.fromJson({
      ...orderJson(4, status: 'preparing'),
      'delivery_pin': '4821',
      'customer_contact': {'name': 'Zainab', 'phone': '+9647701234567'},
    });
    final slips = OrderSlips.of(order, S('en'), storeName: 'Tigris Grill');
    expect(slips.orderNumber, '#4');
    expect(slips.lines.single.quantity, '2×');
    expect(slips.lines.single.name, 'Kebab');
    expect(slips.lines.single.options, 'Large');
    expect(slips.customer, 'Customer: Zainab');
    expect(slips.payment, 'Cash: captain collects 13,000 IQD');
    expect(slips.readyBy, startsWith('Ready by'));
    final everything = [
      slips.orderNumber,
      slips.placed,
      slips.readyBy,
      slips.customer,
      slips.payment,
      for (final l in slips.lines) '${l.quantity}${l.name}${l.options}',
    ].join(' ');
    expect(everything, isNot(contains('4821')));
    expect(everything, isNot(contains('7701234567')));
  });

  testWidgets('builds an 80 mm PDF with the Arabic font', (tester) async {
    final order = Order.fromJson(orderJson(4));
    final bytes = await tester.runAsync(
      () => OrderPrinter.buildPdf(
        OrderSlips.of(order, S('ar'), storeName: 'مطعم دجلة'),
        PdfPageFormat.roll80,
      ),
    );
    expect(String.fromCharCodes(bytes!.take(4)), '%PDF');
    expect(bytes.length, greaterThan(10000)); // fonts embedded
  });

  group('team invites', () {
    final invite = {
      'id': 4,
      'store': {'id': 1, 'name': 'Tigris Grill', 'type': 'restaurant'},
      'role': 'cashier',
      'invited_by': 'Ali',
      'created_at': '',
    };

    /// A client for someone invited to Tigris Grill; [role] is their account now.
    ApiClient inviteApi(List<String> requests, {String role = 'customer'}) {
      var joined = false;
      return ApiClient(
        baseUrl: 'http://test',
        client: MockClient((request) async {
          requests.add('${request.method} ${request.url.path}');
          final path = request.url.path;
          if (path == '/api/store-invites/') {
            return json(joined ? [] : [invite]);
          }
          if (path == '/api/store-invites/4/accept/') {
            joined = true;
            return json({'id': 4, 'status': 'accepted'});
          }
          if (path == '/api/store-invites/4/decline/') {
            joined = true;
            return json({'id': 4, 'status': 'declined'});
          }
          if (path == '/api/auth/me/') {
            return json({
              'id': 7,
              'phone': '+9647801112233',
              'name': 'Sara',
              'role': joined && request.method == 'GET' ? 'vendor' : role,
            });
          }
          if (path == '/api/auth/otp/request/') {
            return json({
              'phone': '+9647801112233',
              'channel': 'whatsapp',
              'resend_in': 60,
            });
          }
          if (path == '/api/auth/otp/verify/') {
            return json({
              'token': 'new',
              'user': {
                'id': 7,
                'phone': '+9647801112233',
                'name': '',
                'role': role,
              },
            });
          }
          return http.Response('', 204);
        }),
      );
    }

    Widget screen(StoreSession session, Widget home) => MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: session.api),
        ChangeNotifierProvider<BaseSession>.value(value: session),
        ChangeNotifierProvider.value(value: session),
      ],
      child: MediaQuery(
        data: const MediaQueryData(disableAnimations: true),
        child: MaterialApp(theme: waselTheme(Brightness.light), home: home),
      ),
    );

    testWidgets('accepting joins the team and loads the store', (tester) async {
      useTablet(tester);
      final requests = <String>[];
      final session = StoreSession(inviteApi(requests), keepAwake: false)
        ..lang = 'en'
        ..loaded = true;
      var joined = 0;
      session.onJoinedStore = () => joined++;
      await session.signIn(
        'abc',
        User.fromJson({
          'id': 7,
          'phone': '+9647801112233',
          'name': '',
          'role': 'customer',
        }),
      );
      expect(session.invites, hasLength(1));

      await tester.pumpWidget(screen(session, const InvitesScreen()));
      expect(find.text('Tigris Grill'), findsOneWidget);
      expect(find.text('Ali invited you to join as Cashier'), findsOneWidget);

      await tester.tap(find.byKey(const Key('accept-invite-4')));
      await tester.pumpAndSettle();
      expect(requests, contains('POST /api/store-invites/4/accept/'));
      expect(session.invites, isEmpty);
      expect(session.user!.role, 'vendor');
      expect(session.signedIn, isTrue);
      expect(joined, 1);
      await tester.pumpWidget(const SizedBox());
    });

    testWidgets('a new number that declines is signed out', (tester) async {
      useTablet(tester);
      final requests = <String>[];
      final session = StoreSession(inviteApi(requests), keepAwake: false)
        ..lang = 'en'
        ..loaded = true;
      await session.signIn(
        'abc',
        User.fromJson({
          'id': 7,
          'phone': '+9647801112233',
          'name': '',
          'role': 'customer',
        }),
      );
      await tester.pumpWidget(screen(session, const InvitesScreen()));

      await tester.tap(find.byKey(const Key('decline-4')));
      await tester.pumpAndSettle();
      expect(requests, contains('POST /api/store-invites/4/decline/'));
      expect(session.signedIn, isFalse);
      await tester.pumpWidget(const SizedBox());
    });

    testWidgets('sign-in lets in invited numbers and refuses other customers', (
      tester,
    ) async {
      useTablet(tester);
      for (final invited in [true, false]) {
        final requests = <String>[];
        final api = inviteApi(requests);
        final session = StoreSession(api, keepAwake: false)
          ..lang = 'en'
          ..loaded = true;
        await tester.pumpWidget(
          screen(
            session,
            LoginScreen(
              admitUser: (api, user) async =>
                  user.role == 'vendor' ||
                  (invited && (await api.storeInvites()).isNotEmpty),
              rejectedError: 'err_not_store',
            ),
          ),
        );
        await tester.enterText(find.byType(TextField).first, '07801112233');
        await tester.testTextInput.receiveAction(TextInputAction.done);
        await tester.pumpAndSettle();
        final send = find.byWidgetPredicate((w) => w is PillButton);
        await tester.tap(send.first);
        await tester.pumpAndSettle();
        await tester.enterText(find.byType(TextField).first, '482913');
        await tester.pumpAndSettle();

        expect(session.signedIn, invited, reason: 'invited: $invited');
        if (!invited) {
          expect(find.textContaining("isn't a store account"), findsOneWidget);
          expect(requests.last, 'POST /api/auth/logout/');
        }
        await tester.pumpWidget(const SizedBox());
      }
    });
  });
}
