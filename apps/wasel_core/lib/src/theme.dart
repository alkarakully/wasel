import 'package:flutter/cupertino.dart' show CupertinoPageTransitionsBuilder;
import 'package:flutter/material.dart';

/// Wasel design system v2. The same tokens live in
/// backend/accounts/static/wasel/tokens.css and apps/vendor/src/styles.css.
///
/// Brand: Babylon lapis (Ishtar Gate blue) with gold kept for the wordmark,
/// rules and highlights. Neutrals are cool "ink" tones tinted toward lapis.
class Lapis {
  static const c50 = Color(0xFFF0F3FD);
  static const c100 = Color(0xFFE1E7FA);
  static const c200 = Color(0xFFC3CEF4);
  static const c300 = Color(0xFF98A9EA);
  static const c400 = Color(0xFF6A80DA);
  static const c500 = Color(0xFF4560C7);
  static const c600 = Color(0xFF2F48B0);
  static const c700 = Color(0xFF22379B); // brand
  static const c800 = Color(0xFF1A2A7C);
  static const c900 = Color(0xFF131F5C);
  static const c950 = Color(0xFF0B123A);
}

class Gold {
  static const c200 = Color(0xFFFBEBC2);
  static const c300 = Color(0xFFF7DC92);
  static const c400 = Color(0xFFF2C75C); // brand
  static const c500 = Color(0xFFE0AE3A);
  static const c700 = Color(0xFF8C6514); // gold text on light surfaces
}

/// Kept for older call sites.
class Brand {
  static const lapis = Lapis.c700;
  static const lapisDark = Lapis.c800;
  static const gold = Gold.c400;
  static const onLapis = Color(0xFFF4F6FF);
}

/// Spring-like curves: quick to start, soft to settle.
class Motion {
  static const spring = Cubic(0.32, 0.72, 0, 1);
  static const out = Cubic(0.16, 1, 0.3, 1);
  static const fast = Duration(milliseconds: 220);
  static const medium = Duration(milliseconds: 420);
  static const slow = Duration(milliseconds: 700);
}

class Radii {
  static const sm = 10.0;
  static const md = 16.0;
  static const lg = 24.0;
  static const xl = 32.0;
}

const fontFamily = 'packages/wasel_core/IBMPlexSansArabic';

/// Surface tokens that Material's ColorScheme doesn't cover.
@immutable
class WaselTheme extends ThemeExtension<WaselTheme> {
  const WaselTheme({
    required this.canvas,
    required this.surface,
    required this.sunk,
    required this.ink,
    required this.muted,
    required this.hairline,
    required this.goldText,
    required this.success,
    required this.raised,
    required this.floating,
  });

  final Color canvas;
  final Color surface;
  final Color sunk;
  final Color ink;
  final Color muted;
  final Color hairline;
  final Color goldText;
  final Color success;

  /// Soft lapis-tinted shadows: cards at rest, and sheets/islands above.
  final List<BoxShadow> raised;
  final List<BoxShadow> floating;

  static const light = WaselTheme(
    canvas: Color(0xFFF5F6FB),
    surface: Color(0xFFFDFDFF),
    sunk: Color(0xFFEEF0F7),
    ink: Color(0xFF10152B),
    muted: Color(0xFF4B5272),
    hairline: Color(0x14131F5C),
    goldText: Gold.c700,
    success: Color(0xFF17845A),
    raised: [
      BoxShadow(color: Color(0x0F131F5C), blurRadius: 2, offset: Offset(0, 1)),
      BoxShadow(
        color: Color(0x14131F5C),
        blurRadius: 24,
        spreadRadius: -12,
        offset: Offset(0, 10),
      ),
    ],
    floating: [
      BoxShadow(
        color: Color(0x33131F5C),
        blurRadius: 48,
        spreadRadius: -20,
        offset: Offset(0, 24),
      ),
    ],
  );

  static const dark = WaselTheme(
    canvas: Color(0xFF0A0E1F),
    surface: Color(0xFF12172C),
    sunk: Color(0xFF0E1326),
    ink: Color(0xFFEEF1FB),
    muted: Color(0xFFA6ADC8),
    hairline: Color(0x14EEF1FB),
    goldText: Gold.c400,
    success: Color(0xFF4CC38A),
    raised: [
      BoxShadow(
        color: Color(0x66000000),
        blurRadius: 24,
        spreadRadius: -12,
        offset: Offset(0, 10),
      ),
    ],
    floating: [
      BoxShadow(
        color: Color(0x99000000),
        blurRadius: 48,
        spreadRadius: -20,
        offset: Offset(0, 24),
      ),
    ],
  );

  /// The tokens for the current theme; plain Material themes get the
  /// defaults for their brightness.
  static WaselTheme of(BuildContext context) {
    final theme = Theme.of(context);
    return theme.extension<WaselTheme>() ??
        (theme.brightness == Brightness.dark ? dark : light);
  }

  @override
  WaselTheme copyWith() => this;

  @override
  WaselTheme lerp(WaselTheme? other, double t) =>
      t < 0.5 ? this : (other ?? this);
}

ThemeData waselTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final tokens = dark ? WaselTheme.dark : WaselTheme.light;
  final primary = dark ? Lapis.c300 : Lapis.c700;
  final onPrimary = dark ? Lapis.c950 : const Color(0xFFF4F6FF);
  final tint = dark ? const Color(0xFF1B2348) : Lapis.c50;

  final scheme = ColorScheme(
    brightness: brightness,
    primary: primary,
    onPrimary: onPrimary,
    primaryContainer: tint,
    onPrimaryContainer: tokens.ink,
    secondary: dark ? Gold.c400 : Gold.c700,
    onSecondary: dark ? Lapis.c950 : Colors.white,
    secondaryContainer: tint,
    onSecondaryContainer: tokens.ink,
    tertiary: Gold.c400,
    onTertiary: Lapis.c950,
    error: dark ? const Color(0xFFFF8A7A) : const Color(0xFFC2331F),
    onError: dark ? Lapis.c950 : Colors.white,
    surface: tokens.surface,
    onSurface: tokens.ink,
    onSurfaceVariant: tokens.muted,
    surfaceContainerLowest: tokens.surface,
    surfaceContainerLow: tokens.canvas,
    surfaceContainer: tokens.sunk,
    surfaceContainerHigh: tokens.sunk,
    surfaceContainerHighest: tokens.sunk,
    outline: dark ? const Color(0xFF2B3252) : const Color(0xFFD6DAE8),
    outlineVariant: tokens.hairline,
    shadow: Lapis.c950,
  );

  final base = ThemeData(
    useMaterial3: true,
    brightness: brightness,
    fontFamily: fontFamily,
  );
  final text = base.textTheme
      .apply(bodyColor: tokens.ink, displayColor: tokens.ink)
      .copyWith(
        displaySmall: base.textTheme.displaySmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5,
        ),
        headlineMedium: base.textTheme.headlineMedium?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.3,
        ),
        headlineSmall: base.textTheme.headlineSmall?.copyWith(
          fontWeight: FontWeight.w700,
        ),
        titleLarge: base.textTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
        ),
        titleMedium: base.textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.w600,
        ),
        bodyLarge: base.textTheme.bodyLarge?.copyWith(height: 1.5),
        bodyMedium: base.textTheme.bodyMedium?.copyWith(
          height: 1.5,
          color: tokens.ink,
        ),
        labelLarge: base.textTheme.labelLarge?.copyWith(
          fontWeight: FontWeight.w600,
          letterSpacing: 0.1,
        ),
      );

  const pill = StadiumBorder();
  const card = RoundedRectangleBorder(
    borderRadius: BorderRadius.all(Radius.circular(Radii.md)),
  );
  final field = OutlineInputBorder(
    borderRadius: const BorderRadius.all(Radius.circular(Radii.md)),
    borderSide: BorderSide(color: tokens.hairline),
  );

  return base.copyWith(
    colorScheme: scheme,
    textTheme: text,
    extensions: [tokens],
    scaffoldBackgroundColor: tokens.canvas,
    splashFactory: InkSparkle.splashFactory,
    appBarTheme: AppBarTheme(
      backgroundColor: tokens.canvas,
      foregroundColor: tokens.ink,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: text.titleLarge,
    ),
    cardTheme: CardThemeData(
      color: tokens.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: card.copyWith(side: BorderSide(color: tokens.hairline)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(56),
        shape: pill,
        textStyle: text.titleMedium?.copyWith(fontWeight: FontWeight.w700),
        elevation: 0,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(56),
        shape: pill,
        side: BorderSide(color: scheme.outline),
        foregroundColor: tokens.ink,
        textStyle: text.titleMedium,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: primary,
        textStyle: text.labelLarge,
        shape: pill,
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(foregroundColor: tokens.ink),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: tokens.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      border: field,
      enabledBorder: field,
      focusedBorder: field.copyWith(
        borderSide: BorderSide(color: primary, width: 2),
      ),
      errorBorder: field.copyWith(borderSide: BorderSide(color: scheme.error)),
      focusedErrorBorder: field.copyWith(
        borderSide: BorderSide(color: scheme.error, width: 2),
      ),
      hintStyle: TextStyle(color: tokens.muted.withValues(alpha: 0.75)),
    ),
    chipTheme: ChipThemeData(
      shape: pill,
      side: BorderSide(color: tokens.hairline),
      backgroundColor: tokens.surface,
      selectedColor: primary,
      labelStyle: text.labelLarge?.copyWith(color: tokens.ink),
      secondaryLabelStyle: text.labelLarge?.copyWith(color: onPrimary),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      showCheckmark: false,
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: SegmentedButton.styleFrom(
        backgroundColor: tokens.surface,
        selectedBackgroundColor: tint,
        selectedForegroundColor: tokens.ink,
        side: BorderSide(color: tokens.hairline),
        shape: pill,
      ),
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: tokens.surface,
      surfaceTintColor: Colors.transparent,
      showDragHandle: true,
      dragHandleColor: scheme.outline,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(Radii.xl)),
      ),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: tokens.surface,
      surfaceTintColor: Colors.transparent,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(Radii.lg)),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: dark ? Lapis.c100 : Lapis.c950,
      contentTextStyle: text.bodyMedium?.copyWith(
        color: dark ? Lapis.c950 : Lapis.c50,
      ),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(Radii.md)),
      ),
    ),
    switchTheme: SwitchThemeData(
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
      thumbColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected) ? Gold.c400 : tokens.surface,
      ),
      trackColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected) ? primary : scheme.outline,
      ),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(
      color: primary,
      linearTrackColor: tokens.sunk,
    ),
    dividerTheme: DividerThemeData(color: tokens.hairline, space: 1),
    listTileTheme: ListTileThemeData(
      iconColor: tokens.muted,
      textColor: tokens.ink,
    ),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
        TargetPlatform.android: FadeForwardsPageTransitionsBuilder(),
      },
    ),
  );
}
