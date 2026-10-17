import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import 'screens/home_screen.dart';
import 'state/captain_session.dart';
import 'state/location_sharer.dart';
import 'strings.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  S.addStrings(captainStrings);
  final api = ApiClient();
  final live = LiveUpdates(api);
  final sharer = LocationSharer(api, live);
  final session = CaptainSession(api, sharer);
  session.addListener(() => session.signedIn ? live.start() : live.stop());
  session.load();

  runApp(
    MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider.value(value: live),
        ChangeNotifierProvider.value(value: sharer),
        // Shared widgets (login, strings) read the session as BaseSession.
        ChangeNotifierProvider<BaseSession>.value(value: session),
        ChangeNotifierProvider.value(value: session),
      ],
      child: const CaptainApp(),
    ),
  );
}

class CaptainApp extends StatelessWidget {
  const CaptainApp({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<CaptainSession>();
    return MaterialApp(
      title: 'Wasel Captain',
      debugShowCheckedModeBanner: false,
      // Kurdish uses Arabic script and right-to-left layout; Flutter's own
      // widget text falls back to Arabic, our strings stay Kurdish.
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
          ? const Scaffold(backgroundColor: Brand.lapis)
          : session.signedIn
          ? const HomeScreen()
          : LoginScreen(
              acceptUser: (user) => user.role == 'captain',
              rejectedError: 'err_not_captain',
            ),
    );
  }
}
