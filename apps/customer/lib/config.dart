/// Build-time settings. Override with --dart-define. The API address
/// (API_URL) is read by wasel_core.
class Config {
  static const mapStyleLight = String.fromEnvironment(
    'MAP_STYLE_LIGHT',
    defaultValue: 'https://tiles.openfreemap.org/styles/positron',
  );
  static const mapStyleDark = String.fromEnvironment(
    'MAP_STYLE_DARK',
    defaultValue: 'https://tiles.openfreemap.org/styles/dark',
  );

  /// Used when the phone's location isn't available: Karrada, Baghdad.
  static const fallbackLat = 33.3045;
  static const fallbackLng = 44.4214;
}
