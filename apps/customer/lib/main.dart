import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import 'screens/home_screen.dart';
import 'screens/tracking_screen.dart';
import 'state/cart.dart';
import 'state/session.dart';
import 'strings.dart';

final navigatorKey = GlobalKey<NavigatorState>();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  S.addStrings(customerStrings);
  final api = ApiClient();
  final push = PushService(api, app: 'customer');
  final session = Session(api, push: push);
  // Tapping an order notification opens that order's tracking screen.
  push.onOpen = (data) {
    final orderId = int.tryParse('${data['order_id']}');
    if (orderId == null) return;
    navigatorKey.currentState?.push(
      MaterialPageRoute(builder: (_) => TrackingScreen(orderId: orderId)),
    );
  };
  final live = LiveUpdates(api);
  // Keep one live socket open whenever someone is signed in.
  session.addListener(() => session.signedIn ? live.start() : live.stop());
  session.load();

  runApp(
    MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider.value(value: live),
        // Shared widgets (login, strings) read the session as BaseSession.
        ChangeNotifierProvider<BaseSession>.value(value: session),
        ChangeNotifierProvider.value(value: session),
        ChangeNotifierProvider(create: (_) => Cart()),
      ],
      child: const WaselApp(),
    ),
  );
}

class WaselApp extends StatelessWidget {
  const WaselApp({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    return MaterialApp(
      navigatorKey: navigatorKey,
      title: 'Wasel',
      debugShowCheckedModeBanner: false,
      // Kurdish (Sorani) uses Arabic script and right-to-left layout; Flutter's
      // built-in widget text falls back to Arabic, our own strings stay Kurdish.
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
          ? const BrandSplash()
          : session.signedIn
          ? const HomeScreen()
          : const LoginScreen(),
    );
  }
}
