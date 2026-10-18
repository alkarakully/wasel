import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../session.dart';
import '../theme.dart';

/// العربية / کوردی / English, shown in each language's own name.
///
/// A pill track with a sliding thumb. [onDark] gives the frosted variant that
/// sits on the lapis glaze.
class LanguageSwitch extends StatelessWidget {
  const LanguageSwitch({super.key, this.onDark = false});

  final bool onDark;

  static const languages = {'ar': 'العربية', 'ku': 'کوردی', 'en': 'English'};

  @override
  Widget build(BuildContext context) {
    final session = context.watch<BaseSession>();
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final track = onDark ? Colors.white.withValues(alpha: 0.10) : t.sunk;
    final border = onDark ? Colors.white.withValues(alpha: 0.16) : t.hairline;
    final thumb = onDark ? Gold.c400 : t.surface;
    final selectedText = onDark ? Lapis.c950 : scheme.primary;
    final idleText = onDark ? Lapis.c100 : t.muted;

    return FittedBox(
      fit: BoxFit.scaleDown,
      child: Container(
        padding: const EdgeInsets.all(3),
        decoration: ShapeDecoration(
          color: track,
          shape: StadiumBorder(side: BorderSide(color: border)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final e in languages.entries)
              Semantics(
                button: true,
                selected: session.lang == e.key,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => session.setLang(e.key),
                  child: AnimatedContainer(
                    duration: Motion.fast,
                    curve: Motion.out,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 7,
                    ),
                    decoration: ShapeDecoration(
                      color: session.lang == e.key ? thumb : Colors.transparent,
                      shape: const StadiumBorder(),
                      shadows: session.lang == e.key && !onDark
                          ? t.raised
                          : null,
                    ),
                    child: Text(
                      e.value,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: session.lang == e.key
                            ? FontWeight.w700
                            : FontWeight.w500,
                        color: session.lang == e.key ? selectedText : idleText,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
