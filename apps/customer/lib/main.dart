import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'state/cart.dart';
import 'state/live_updates.dart';
import 'state/session.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiClient();
  final session = Session(api);
  final live = LiveUpdates(api);
  // Keep one live socket open whenever someone is signed in.
  session.addListener(() => session.signedIn ? live.start() : live.stop());
  session.load();

  runApp(
    MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider.value(value: live),
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
          ? const _Splash()
          : session.signedIn
          ? const HomeScreen()
          : const LoginScreen(),
    );
  }
}

class _Splash extends StatelessWidget {
  const _Splash();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Brand.lapis,
      body: Center(
        child: Text(
          'واصل',
          style: TextStyle(
            color: Brand.gold,
            fontSize: 64,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}
