import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import 'print/printer.dart';
import 'screens/home_screen.dart';
import 'state/alarm.dart';
import 'state/board.dart';
import 'state/store_session.dart';
import 'strings.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  S.addStrings(storeStrings);
  final api = ApiClient();
  final live = LiveUpdates(api);
  final push = PushService(api, app: 'store');
  final session = StoreSession(api, push: push);
  final board = StoreBoard(api, live);
  final alarm = OrderAlarm();

  // Tapping a new-order notification opens the board fresh.
  push.onOpen = (_) => board.reload();
  session.addListener(() {
    if (session.signedIn) {
      live.start();
      if (board.stores == null) board.start();
    } else {
      live.stop();
      board.stop();
    }
  });
  board.addListener(() => board.ringing ? alarm.start() : alarm.stop());
  session.load();

  runApp(
    StoreApp(
      api: api,
      live: live,
      session: session,
      board: board,
      printer: OrderPrinter(),
    ),
  );
}

class StoreApp extends StatelessWidget {
  const StoreApp({
    super.key,
    required this.api,
    required this.live,
    required this.session,
    required this.board,
    required this.printer,
  });

  final ApiClient api;
  final LiveUpdates live;
  final StoreSession session;
  final StoreBoard board;
  final OrderPrinter printer;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider.value(value: live),
        // Shared widgets (login, strings) read the session as BaseSession.
        ChangeNotifierProvider<BaseSession>.value(value: session),
        ChangeNotifierProvider.value(value: session),
        ChangeNotifierProvider.value(value: board),
        Provider.value(value: printer),
      ],
      child: Consumer<StoreSession>(
        builder: (context, session, _) => MaterialApp(
          title: 'Wasel Store',
          debugShowCheckedModeBanner: false,
          // Kurdish uses Arabic script and right-to-left layout; Flutter's
          // own widget text falls back to Arabic, our strings stay Kurdish.
          locale: Locale(session.lang == 'en' ? 'en' : 'ar'),
          supportedLocales: const [Locale('ar'), Locale('en')],
          localizationsDelegates: const [
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          theme: waselTheme(Brightness.light),
          darkTheme: waselTheme(Brightness.dark),
          home: !session.loaded
              ? BrandSplash(caption: S.read(context).t('orders'))
              : session.signedIn
              ? const HomeScreen()
              : LoginScreen(
                  acceptUser: (user) => user.role == 'vendor',
                  rejectedError: 'err_not_store',
                ),
        ),
      ),
    );
  }
}
