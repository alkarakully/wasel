import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/board.dart';
import '../state/store_session.dart';
import 'board_view.dart';
import 'menu_view.dart';

/// The counter tablet: a top bar (store, open switch, sections), alerts, then
/// the live order board or the menu's stock switches.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _menu = false;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final board = context.watch<StoreBoard>();
    final noStores = board.stores != null && board.stores!.isEmpty;

    return Scaffold(
      backgroundColor: t.canvas,
      body: SafeArea(
        child: Column(
          children: [
            _TopBar(
              menu: _menu,
              onSection: (menu) => setState(() => _menu = menu),
            ),
            _Alerts(board: board),
            Expanded(
              child: noStores
                  ? Center(
                      child: Text(
                        s.t('noStores'),
                        style: TextStyle(color: t.muted),
                      ),
                    )
                  : AnimatedSwitcher(
                      duration: Motion.medium,
                      switchInCurve: Motion.out,
                      switchOutCurve: Motion.out,
                      child: _menu
                          ? const MenuView(key: ValueKey('menu'))
                          : const BoardView(key: ValueKey('board')),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.menu, required this.onSection});
  final bool menu;
  final ValueChanged<bool> onSection;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final board = context.watch<StoreBoard>();
    final store = board.store;
    final newCount = board.newOrders.length;

    final brand = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: const SizedBox(
            width: 44,
            height: 44,
            child: GlazePanel(
              child: Center(
                child: Text(
                  'و',
                  style: TextStyle(
                    color: Gold.c400,
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    height: 1,
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        if (store != null)
          board.multiStore
              ? DropdownButtonHideUnderline(
                  child: DropdownButton<int>(
                    key: const Key('store-picker'),
                    value: store.id,
                    borderRadius: BorderRadius.circular(Radii.md),
                    style: TextStyle(
                      fontFamily: fontFamily,
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      color: t.ink,
                    ),
                    items: [
                      for (final option in board.stores!)
                        DropdownMenuItem(
                          value: option.id,
                          child: Text(option.name),
                        ),
                    ],
                    onChanged: (id) =>
                        id == null ? null : board.selectStore(id),
                  ),
                )
              : Text(
                  store.name,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
        if (store != null) ...[
          const SizedBox(width: 12),
          _OpenPill(
            open: board.isOpen(store),
            onTap: () => board.setOpen(store, !board.isOpen(store)),
          ),
        ],
      ],
    );

    final sections = _Sections(
      menu: menu,
      newCount: newCount,
      onSection: onSection,
    );

    final tools = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const LanguageSwitch(),
        const SizedBox(width: 8),
        Tooltip(
          message: s.t('account'),
          child: Pressable(
            key: const Key('account'),
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const AccountScreen()),
            ),
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: t.surface,
                shape: BoxShape.circle,
                border: Border.all(color: t.hairline),
                boxShadow: t.raised,
              ),
              child: Icon(Ph.key, size: 20, color: t.ink),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Tooltip(
          message: s.t('logout'),
          child: Pressable(
            onTap: () => context.read<StoreSession>().signOut(),
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: t.surface,
                shape: BoxShape.circle,
                border: Border.all(color: t.hairline),
                boxShadow: t.raised,
              ),
              child: Icon(Ph.signOut, size: 20, color: t.ink),
            ),
          ),
        ),
      ],
    );

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Container(
        padding: const EdgeInsetsDirectional.fromSTEB(10, 8, 10, 8),
        decoration: BoxDecoration(
          color: t.surface,
          borderRadius: BorderRadius.circular(Radii.xl),
          border: Border.all(color: t.hairline),
          boxShadow: t.floating,
        ),
        child: LayoutBuilder(
          builder: (context, box) {
            // Landscape tablets fit one row; portrait gets two.
            if (box.maxWidth >= 980) {
              return Row(
                children: [
                  Expanded(
                    child: Align(
                      alignment: AlignmentDirectional.centerStart,
                      child: brand,
                    ),
                  ),
                  sections,
                  Expanded(
                    child: Align(
                      alignment: AlignmentDirectional.centerEnd,
                      child: tools,
                    ),
                  ),
                ],
              );
            }
            return Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: AlignmentDirectional.centerStart,
                        child: brand,
                      ),
                    ),
                    tools,
                  ],
                ),
                const SizedBox(height: 8),
                sections,
              ],
            );
          },
        ),
      ),
    );
  }
}

/// Orders / Menu, with the count of new orders in gold.
class _Sections extends StatelessWidget {
  const _Sections({
    required this.menu,
    required this.newCount,
    required this.onSection,
  });
  final bool menu;
  final int newCount;
  final ValueChanged<bool> onSection;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;

    Widget tab(
      String label,
      bool selected,
      VoidCallback onTap, {
      Widget? badge,
    }) => Semantics(
      button: true,
      selected: selected,
      child: Pressable(
        onTap: onTap,
        child: AnimatedContainer(
          duration: Motion.fast,
          curve: Motion.out,
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 10),
          decoration: ShapeDecoration(
            color: selected ? t.surface : Colors.transparent,
            shape: const StadiumBorder(),
            shadows: selected ? t.raised : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  color: selected ? scheme.primary : t.muted,
                ),
              ),
              ?badge,
            ],
          ),
        ),
      ),
    );

    return Container(
      padding: const EdgeInsets.all(3),
      decoration: ShapeDecoration(
        color: t.sunk,
        shape: StadiumBorder(side: BorderSide(color: t.hairline)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: tab(
              s.t('orders'),
              !menu,
              () => onSection(false),
              badge: newCount == 0
                  ? null
                  : Padding(
                      padding: const EdgeInsetsDirectional.only(start: 8),
                      child: _CountBadge(count: newCount),
                    ),
            ),
          ),
          Flexible(child: tab(s.t('menu'), menu, () => onSection(true))),
        ],
      ),
    );
  }
}

/// A gold count that pops when it changes.
class _CountBadge extends StatelessWidget {
  const _CountBadge({required this.count});
  final int count;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      key: ValueKey(count),
      tween: Tween(begin: 1.35, end: 1),
      duration: MediaQuery.of(context).disableAnimations
          ? Duration.zero
          : Motion.medium,
      curve: Motion.spring,
      builder: (context, scale, child) =>
          Transform.scale(scale: scale, child: child),
      child: Container(
        constraints: const BoxConstraints(minWidth: 24),
        height: 24,
        padding: const EdgeInsets.symmetric(horizontal: 7),
        alignment: Alignment.center,
        decoration: const ShapeDecoration(
          color: Gold.c400,
          shape: StadiumBorder(),
        ),
        child: Text(
          '$count',
          style: const TextStyle(
            color: Lapis.c950,
            fontWeight: FontWeight.w700,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}

/// Store open/closed: green dot when taking orders.
class _OpenPill extends StatelessWidget {
  const _OpenPill({required this.open, required this.onTap});
  final bool open;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final color = open ? t.success : t.muted;
    return Semantics(
      button: true,
      toggled: open,
      child: Pressable(
        key: const Key('store-open'),
        onTap: onTap,
        child: AnimatedContainer(
          duration: Motion.fast,
          curve: Motion.out,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: ShapeDecoration(
            color: open ? t.success.withValues(alpha: 0.12) : t.sunk,
            shape: StadiumBorder(
              side: BorderSide(color: color.withValues(alpha: 0.35)),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
              ),
              const SizedBox(width: 8),
              Text(
                s.t(open ? 'storeOpen' : 'storeClosed'),
                style: TextStyle(color: color, fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Ringing, offline and error banners under the top bar.
class _Alerts extends StatelessWidget {
  const _Alerts({required this.board});
  final StoreBoard board;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;

    Widget banner({
      required Key key,
      required Widget child,
      VoidCallback? onTap,
      Color? color,
      bool glaze = false,
    }) {
      final body = Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        child: DefaultTextStyle.merge(
          style: TextStyle(
            fontWeight: FontWeight.w700,
            fontSize: glaze ? 17 : 15,
            color: glaze ? Colors.white : null,
          ),
          child: child,
        ),
      );
      return Padding(
        key: key,
        padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
        child: Pressable(
          scale: 0.99,
          onTap: onTap,
          child: glaze
              ? GlazePanel(radius: Radii.lg, child: body)
              : Container(
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(Radii.md),
                  ),
                  child: body,
                ),
        ),
      );
    }

    return AnimatedSize(
      duration: Motion.medium,
      curve: Motion.spring,
      alignment: Alignment.topCenter,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (board.ringing)
            banner(
              key: const Key('mute'),
              glaze: true,
              onTap: board.silence,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const _RingingBell(),
                  const SizedBox(width: 12),
                  Flexible(child: Text(s.t('newOrderBanner'))),
                ],
              ),
            ),
          if (!board.connected)
            banner(
              key: const Key('offline'),
              color: goldWash(context),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Ph.warningCircle, color: t.goldText),
                  const SizedBox(width: 8),
                  Text(s.t('offline'), style: TextStyle(color: t.goldText)),
                ],
              ),
            ),
          if (board.notice != null)
            banner(
              key: const Key('notice'),
              color: scheme.errorContainer,
              onTap: board.dismissNotice,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Ph.warningCircle, color: scheme.error),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      s.t(board.notice!),
                      style: TextStyle(color: scheme.onErrorContainer),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// A bell that swings while the order rings (still when motion is reduced).
class _RingingBell extends StatefulWidget {
  const _RingingBell();

  @override
  State<_RingingBell> createState() => _RingingBellState();
}

class _RingingBellState extends State<_RingingBell>
    with SingleTickerProviderStateMixin {
  late final _swing = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.of(context).disableAnimations) {
      _swing.stop();
    } else if (!_swing.isAnimating) {
      _swing.repeat();
    }
  }

  @override
  void dispose() {
    _swing.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _swing,
      builder: (context, child) {
        // Three quick swings, then a rest.
        final v = _swing.value;
        final angle = v < 0.5 ? 0.28 * (1 - v * 2) * _wave(v * 6) : 0.0;
        return Transform.rotate(
          angle: angle,
          alignment: Alignment.topCenter,
          child: child,
        );
      },
      child: const Icon(Ph.bellRinging, color: Gold.c400, size: 26),
    );
  }

  static double _wave(double x) =>
      (x % 2 < 1 ? 1 : -1) * (1 - (x % 1 - 0.5).abs() * 2);
}
