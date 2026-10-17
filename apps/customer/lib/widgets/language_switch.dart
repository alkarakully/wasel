import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/session.dart';

/// العربية / کوردی / English, shown in each language's own name.
class LanguageSwitch extends StatelessWidget {
  const LanguageSwitch({super.key});

  static const languages = {'ar': 'العربية', 'ku': 'کوردی', 'en': 'English'};

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    return SegmentedButton<String>(
      showSelectedIcon: false,
      style: const ButtonStyle(visualDensity: VisualDensity.compact),
      segments: [
        for (final e in languages.entries)
          ButtonSegment(value: e.key, label: Text(e.value)),
      ],
      selected: {session.lang},
      onSelectionChanged: (value) => session.setLang(value.first),
    );
  }
}
