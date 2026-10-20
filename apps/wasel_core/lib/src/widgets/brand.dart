import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../theme.dart';
import 'icons.dart';
import 'logo_paths.dart';

/// The Ishtar Gate's glazed bricks: staggered mortar lines, very faint.
class BrickTexturePainter extends CustomPainter {
  const BrickTexturePainter({
    this.color = const Color(0xFFF4F6FF),
    this.opacity = 0.07,
  });

  final Color color;
  final double opacity;
  static const brickWidth = 44.0;
  static const brickHeight = 20.0;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color.withValues(alpha: opacity)
      ..strokeWidth = 1;
    var row = 0;
    for (var y = 0.0; y < size.height; y += brickHeight, row++) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
      final offset = row.isEven ? 0.0 : brickWidth / 2;
      for (var x = offset; x < size.width; x += brickWidth) {
        canvas.drawLine(Offset(x, y), Offset(x, y + brickHeight), paint);
      }
    }
  }

  @override
  bool shouldRepaint(BrickTexturePainter old) =>
      old.color != color || old.opacity != opacity;
}

/// Deep glazed-lapis gradient with the brick texture: the brand's hero surface.
class GlazePanel extends StatelessWidget {
  const GlazePanel({
    super.key,
    required this.child,
    this.radius = 0,
    this.padding = EdgeInsets.zero,
  });

  final Widget child;
  final double radius;
  final EdgeInsetsGeometry padding;

  static const gradient = LinearGradient(
    begin: AlignmentDirectional.topEnd,
    end: AlignmentDirectional.bottomStart,
    colors: [Lapis.c600, Lapis.c700, Lapis.c900, Lapis.c950],
    stops: [0, 0.35, 0.8, 1],
  );

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: DecoratedBox(
        decoration: const BoxDecoration(gradient: gradient),
        child: Stack(
          children: [
            // A soft highlight, like light catching the glaze.
            const Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: AlignmentDirectional(0.8, -1.1),
                    radius: 1.1,
                    colors: [Color(0x406A80DA), Color(0x006A80DA)],
                  ),
                ),
              ),
            ),
            const Positioned.fill(
              child: CustomPaint(painter: BrickTexturePainter()),
            ),
            Padding(padding: padding, child: child),
          ],
        ),
      ),
    );
  }
}

/// A thin gold line with a small diamond, used under the wordmark and titles.
/// It draws itself in from the reading start the first time it appears.
class GoldRule extends StatelessWidget {
  const GoldRule({super.key, this.width = 72});
  final double width;

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.of(context).disableAnimations;
    // Align keeps the rule its own width inside stretched columns.
    return Align(
      alignment: AlignmentDirectional.centerStart,
      widthFactor: 1,
      heightFactor: 1,
      child: SizedBox(
        width: width,
        height: 10,
        child: TweenAnimationBuilder<double>(
          tween: Tween(begin: reduce ? 1 : 0, end: 1),
          duration: Motion.slow,
          curve: Motion.out,
          builder: (context, v, _) => Stack(
            alignment: AlignmentDirectional.centerStart,
            children: [
              FractionallySizedBox(
                widthFactor: v,
                alignment: AlignmentDirectional.centerStart,
                child: Container(
                  height: 1.5,
                  color: Gold.c400.withValues(alpha: 0.85),
                ),
              ),
              PositionedDirectional(
                start: width / 2 - 4,
                child: Transform.rotate(
                  angle: 0.785398 * (1 + 2 * (1 - v)),
                  child: Transform.scale(
                    scale: Curves.easeOutBack.transform(
                      ((v - 0.35) / 0.65).clamp(0.0, 1.0),
                    ),
                    child: Container(width: 7, height: 7, color: Gold.c400),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A soft gold background for money notes (cash to collect), readable in
/// both light and dark mode.
Color goldWash(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark
    ? Gold.c400.withValues(alpha: 0.12)
    : Gold.c200.withValues(alpha: 0.55);

/// واصل in gold.
class Wordmark extends StatelessWidget {
  const Wordmark({
    super.key,
    this.size = 56,
    this.latinColor = const Color(0xFFF4F6FF),
    this.arabicColor = logoGold,
    this.stacked = false,
  });

  /// About the height of the Arabic name; the divider reaches a little past it.
  final double size;

  /// WASEL's colour: light on the lapis glaze (default), [logoBlue] on light screens.
  final Color latinColor;

  /// واصل and the divider stay gold unless a screen needs otherwise.
  final Color arabicColor;

  /// واصل over the divider and WASEL, for splash screens.
  final bool stacked;

  static const logoBlue = Color(0xFF033990);
  static const logoGold = Color(0xFFE4A739);

  static String _hex(Color c) =>
      '#${(c.toARGB32() & 0xFFFFFF).toRadixString(16).padLeft(6, '0')}';

  String _svg() {
    final la = _hex(latinColor), ar = _hex(arabicColor);
    final laA = latinColor.a.toStringAsFixed(3);
    if (stacked) {
      return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="$logoStackedViewBox">'
          '<path transform="$logoStackedArabicTransform" d="$logoArabicPath" fill="$ar" fill-rule="evenodd"/>'
          '<path d="$logoStackedRulePath" fill="$ar"/>'
          '<path transform="$logoStackedLatinTransform" d="$logoLatinPath" fill="$la" fill-opacity="$laA" fill-rule="evenodd"/>'
          '</svg>';
    }
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="$logoViewBox">'
        '<path d="$logoLatinPath" fill="$la" fill-opacity="$laA" fill-rule="evenodd"/>'
        '<path d="$logoDividerPath" fill="$ar"/>'
        '<path d="$logoArabicPath" fill="$ar" fill-rule="evenodd"/>'
        '</svg>';
  }

  @override
  Widget build(BuildContext context) {
    // Same overall height as the text wordmark it replaced, so layouts keep their rhythm.
    final height = stacked ? size * 2.2 : size * 1.15;
    return Semantics(
      label: 'WASEL واصل',
      image: true,
      // Shrinks to fit a narrow panel instead of overflowing it.
      child: FittedBox(
        fit: BoxFit.scaleDown,
        alignment: AlignmentDirectional.centerStart,
        child: SvgPicture.string(
          _svg(),
          height: height,
          excludeFromSemantics: true,
        ),
      ),
    );
  }
}

/// The "double bezel": a tinted outer tray holding the content plate, so key
/// cards read as physical objects rather than flat boxes.
class BezelCard extends StatelessWidget {
  const BezelCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.radius = Radii.lg,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double radius;
  static const _gap = 5.0;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    return Container(
      padding: const EdgeInsets.all(_gap),
      decoration: BoxDecoration(
        color: t.sunk,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: t.hairline),
      ),
      child: Container(
        padding: padding,
        decoration: BoxDecoration(
          color: t.surface,
          borderRadius: BorderRadius.circular(radius - _gap),
          boxShadow: t.raised,
          // A top highlight like the edge of a glass plate.
          border: Border(
            top: BorderSide(
              color: Colors.white.withValues(
                alpha: Theme.of(context).brightness == Brightness.dark
                    ? 0.06
                    : 0.6,
              ),
              width: 0.5,
            ),
          ),
        ),
        child: child,
      ),
    );
  }
}

/// Scales down a touch while pressed, like a physical button.
class Pressable extends StatefulWidget {
  const Pressable({
    super.key,
    required this.child,
    this.onTap,
    this.scale = 0.97,
  });
  final Widget child;
  final VoidCallback? onTap;
  final double scale;

  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable> {
  bool _down = false;

  void _set(bool down) {
    if (widget.onTap != null && down != _down) setState(() => _down = down);
  }

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.of(context).disableAnimations;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: widget.onTap == null
          ? null
          : () {
              // A light tick, like pressing a physical key.
              HapticFeedback.selectionClick();
              widget.onTap!();
            },
      onTapDown: (_) => _set(true),
      onTapUp: (_) => _set(false),
      onTapCancel: () => _set(false),
      child: AnimatedScale(
        scale: _down && !reduce ? widget.scale : 1,
        duration: Motion.fast,
        curve: Motion.spring,
        child: widget.child,
      ),
    );
  }
}

/// Primary call to action: a pill with the arrow in its own circle.
class PillButton extends StatelessWidget {
  const PillButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.busy = false,
    this.icon,
    this.tone = PillTone.lapis,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool busy;
  final IconData? icon;
  final PillTone tone;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final rtl = Directionality.of(context) == TextDirection.rtl;
    final enabled = onPressed != null && !busy;
    final background = tone == PillTone.gold ? Gold.c400 : scheme.primary;
    final foreground = tone == PillTone.gold ? Lapis.c950 : scheme.onPrimary;

    return Semantics(
      button: true,
      enabled: enabled,
      label: label,
      child: Pressable(
        onTap: enabled ? onPressed : null,
        child: AnimatedOpacity(
          opacity: enabled ? 1 : 0.45,
          duration: Motion.fast,
          child: Container(
            height: 58,
            padding: const EdgeInsetsDirectional.only(start: 24, end: 7),
            decoration: ShapeDecoration(
              shape: const StadiumBorder(),
              color: background,
              shadows: enabled
                  ? [
                      BoxShadow(
                        color: background.withValues(alpha: 0.35),
                        blurRadius: 20,
                        spreadRadius: -8,
                        offset: const Offset(0, 10),
                      ),
                    ]
                  : null,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontFamily: fontFamily,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: foreground,
                    ),
                  ),
                ),
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: foreground.withValues(alpha: 0.14),
                  ),
                  child: busy
                      ? Padding(
                          padding: const EdgeInsets.all(13),
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: foreground,
                          ),
                        )
                      : Icon(
                          icon ?? (rtl ? Ph.arrowLeft : Ph.arrowRight),
                          color: foreground,
                          size: 22,
                        ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

enum PillTone { lapis, gold }

/// An illustrated tile per cuisine, used where a store has no photo yet.
class CuisineArt extends StatelessWidget {
  const CuisineArt({
    super.key,
    required this.cuisine,
    this.type = 'restaurant',
    this.size = 64,
    this.radius = Radii.md,
  });

  final String cuisine;
  final String type;
  final double size;
  final double radius;

  static const _art = <String, (IconData, List<Color>)>{
    'eastern': (Ph.cookingPot, [Color(0xFF2F48B0), Color(0xFF131F5C)]),
    'western': (Ph.pizza, [Color(0xFF4560C7), Color(0xFF1A2A7C)]),
    'fast_food': (Ph.hamburger, [Color(0xFF22379B), Color(0xFF0B123A)]),
    'sweets': (Ph.cake, [Color(0xFF6A80DA), Color(0xFF22379B)]),
    'drinks': (Ph.coffee, [Color(0xFF1A2A7C), Color(0xFF0B123A)]),
    'popular': (Ph.fire, [Color(0xFF2F48B0), Color(0xFF0B123A)]),
    'supermarket': (Ph.basket, [Color(0xFF4560C7), Color(0xFF131F5C)]),
    'cafe': (Ph.coffee, [Color(0xFF6A80DA), Color(0xFF1A2A7C)]),
    'pharmacy': (Ph.pill, [Color(0xFF2F48B0), Color(0xFF0B123A)]),
    'convenience': (Ph.shoppingCart, [Color(0xFF4560C7), Color(0xFF1A2A7C)]),
    'flowers': (Ph.flower, [Color(0xFF6A80DA), Color(0xFF131F5C)]),
  };

  static IconData iconFor(String cuisine) =>
      (_art[cuisine] ?? _art['eastern']!).$1;

  /// A store type's icon ("restaurant", "pharmacy", ...).
  static IconData iconForType(String type) =>
      type == 'restaurant' ? Ph.forkKnife : (_art[type]?.$1 ?? Ph.storefront);

  @override
  Widget build(BuildContext context) {
    // Restaurants show their cuisine; every other kind of store shows its kind.
    final key = type == 'restaurant' ? cuisine : type;
    final (icon, colors) =
        _art[key] ?? (Ph.forkKnife, const [Lapis.c600, Lapis.c900]);
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: colors,
          ),
        ),
        child: Stack(
          children: [
            const Positioned.fill(
              child: CustomPaint(painter: BrickTexturePainter(opacity: 0.09)),
            ),
            Center(
              child: Icon(icon, size: size * 0.46, color: Gold.c300),
            ),
          ],
        ),
      ),
    );
  }
}

/// Shown while the session loads: the wordmark on glaze.
class BrandSplash extends StatelessWidget {
  const BrandSplash({super.key, this.caption});
  final String? caption;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Lapis.c900,
      body: SizedBox.expand(
        child: GlazePanel(
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // The wordmark settles in like glaze catching light.
                TweenAnimationBuilder<double>(
                  tween: Tween(
                    begin: MediaQuery.of(context).disableAnimations ? 1 : 0,
                    end: 1,
                  ),
                  duration: Motion.slow,
                  curve: Motion.out,
                  builder: (context, v, child) => Opacity(
                    opacity: v,
                    child: Transform.scale(
                      scale: 0.92 + 0.08 * v,
                      child: child,
                    ),
                  ),
                  child: const Wordmark(size: 72, stacked: true),
                ),
                if (caption != null) ...[
                  const SizedBox(height: 14),
                  Text(
                    caption!,
                    style: const TextStyle(
                      fontFamily: fontFamily,
                      color: Lapis.c200,
                      fontSize: 15,
                      letterSpacing: 1.5,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
