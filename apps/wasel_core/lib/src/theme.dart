import 'package:flutter/material.dart';

/// Wasel brand: Babylon lapis with gold kept for the wordmark only.
/// Same tokens as backend/accounts/static/wasel/tokens.css.
class Brand {
  static const lapis = Color(0xFF22379B);
  static const lapisDark = Color(0xFF1A2A7A);
  static const gold = Color(0xFFF2C75C);
  static const onLapis = Color(0xFFF4F6FF);
}

ThemeData waselTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme = ColorScheme(
    brightness: brightness,
    primary: dark ? const Color(0xFF93A6FF) : Brand.lapis,
    onPrimary: dark ? const Color(0xFF0D1330) : Brand.onLapis,
    primaryContainer: dark ? const Color(0xFF1C2450) : const Color(0xFFE6EAFB),
    onPrimaryContainer: dark
        ? const Color(0xFFEDF0FA)
        : const Color(0xFF141A2E),
    secondary: dark ? const Color(0xFF93A6FF) : Brand.lapis,
    // Selected chips and tonal buttons: soft lapis with dark text.
    secondaryContainer: dark
        ? const Color(0xFF1C2450)
        : const Color(0xFFE6EAFB),
    onSecondaryContainer: dark
        ? const Color(0xFFEDF0FA)
        : const Color(0xFF141A2E),
    onSecondary: dark ? const Color(0xFF0D1330) : Brand.onLapis,
    error: dark ? const Color(0xFFFF8A80) : const Color(0xFFB42318),
    onError: dark ? const Color(0xFF0D1020) : Colors.white,
    surface: dark ? const Color(0xFF151A2F) : const Color(0xFFFBFCFE),
    onSurface: dark ? const Color(0xFFEDF0FA) : const Color(0xFF141A2E),
    onSurfaceVariant: dark ? const Color(0xFFA3AAC4) : const Color(0xFF4A5170),
    outline: dark ? const Color(0xFF2D3453) : const Color(0xFFD3D8E6),
    surfaceContainerHighest: dark
        ? const Color(0xFF1C2238)
        : const Color(0xFFEEF1F8),
  );
  const radius = BorderRadius.all(Radius.circular(12));
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: dark
        ? const Color(0xFF0D1020)
        : const Color(0xFFF2F4F9),
    appBarTheme: AppBarTheme(
      backgroundColor: dark ? const Color(0xFF0D1020) : const Color(0xFFF2F4F9),
      foregroundColor: scheme.onSurface,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: scheme.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: BorderSide(color: scheme.outline),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        shape: const RoundedRectangleBorder(borderRadius: radius),
        textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        shape: const RoundedRectangleBorder(borderRadius: radius),
        side: BorderSide(color: scheme.outline),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surface,
      border: OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(color: scheme.outline),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(color: scheme.outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
    ),
    chipTheme: ChipThemeData(
      shape: const RoundedRectangleBorder(borderRadius: radius),
      side: BorderSide(color: scheme.outline),
      selectedColor: scheme.primaryContainer,
    ),
  );
}
