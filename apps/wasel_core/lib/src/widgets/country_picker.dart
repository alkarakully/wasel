import 'package:flutter/material.dart';

import '../countries.dart';
import '../strings.dart';
import '../theme.dart';
import 'icons.dart';

/// Opens the country list for a phone number: Iraq first, then the Gulf,
/// then every country A–Z, searchable by name or code. Returns the picked
/// ISO code, or null when dismissed.
Future<String?> showCountryPicker(BuildContext context, String selected) {
  return showModalBottomSheet<String>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    showDragHandle: true,
    builder: (context) => _CountrySheet(selected: selected),
  );
}

class _CountrySheet extends StatefulWidget {
  const _CountrySheet({required this.selected});
  final String selected;

  @override
  State<_CountrySheet> createState() => _CountrySheetState();
}

class _CountrySheetState extends State<_CountrySheet> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final term = _query.trim().toLowerCase().replaceFirst('+', '');
    final matches = term.isEmpty
        ? null
        : countries
              .where(
                (c) =>
                    c.en.toLowerCase().contains(term) ||
                    c.ar.contains(term) ||
                    c.dial.startsWith(term),
              )
              .toList();

    Widget tile(Country c) {
      final picked = c.code == widget.selected;
      return ListTile(
        key: Key('country-${c.code}'),
        leading: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [CountryBadge(c.code)],
        ),
        title: Text(c.name(s.lang)),
        trailing: Directionality(
          textDirection: TextDirection.ltr,
          child: Text(
            '+${c.dial}',
            style: TextStyle(
              color: t.muted,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ),
        selected: picked,
        selectedTileColor: Theme.of(context).colorScheme.primary
            .withValues(alpha: 0.08),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        onTap: () => Navigator.of(context).pop(c.code),
      );
    }

    final rest = countries.where((c) => !shortList.contains(c.code));
    return SizedBox(
      height: MediaQuery.sizeOf(context).height * 0.75,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: TextField(
              key: const Key('country-search'),
              autofocus: false,
              decoration: InputDecoration(
                prefixIcon: const Icon(Ph.magnifyingGlass, size: 20),
                hintText: s.t('searchCountries'),
              ),
              onChanged: (value) => setState(() => _query = value),
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              children: matches != null
                  ? [for (final c in matches) tile(c)]
                  : [
                      for (final code in shortList) tile(countryFor(code)),
                      Padding(
                        padding: const EdgeInsetsDirectional.fromSTEB(
                          16,
                          14,
                          16,
                          6,
                        ),
                        child: Text(
                          s.t('allCountries'),
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: t.muted,
                          ),
                        ),
                      ),
                      for (final c in rest) tile(c),
                    ],
            ),
          ),
        ],
      ),
    );
  }
}

/// A country's two-letter code in a small pill, used where a flag would go
/// (the app font has no flag emoji).
class CountryBadge extends StatelessWidget {
  const CountryBadge(this.code, {super.key});
  final String code;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: 34,
      padding: const EdgeInsets.symmetric(vertical: 3),
      decoration: BoxDecoration(
        color: scheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        code,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
          color: scheme.primary,
        ),
      ),
    );
  }
}
