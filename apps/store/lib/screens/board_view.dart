import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/board.dart';
import 'order_card.dart';

const _columnIcons = {
  'received': Ph.bellRinging,
  'preparing': Ph.cookingPot,
  'ready': Ph.shoppingBag,
};

/// New, preparing and ready orders, oldest first so nothing waits too long.
/// Wide screens (landscape tablets) show all three columns; narrower ones
/// pick a column with tabs.
class BoardView extends StatefulWidget {
  const BoardView({super.key});

  @override
  State<BoardView> createState() => _BoardViewState();
}

class _BoardViewState extends State<BoardView> {
  String _column = 'received';
  Timer? _tick;

  @override
  void initState() {
    super.initState();
    // Keep "x min ago" and countdowns current.
    _tick = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _tick?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final board = context.watch<StoreBoard>();
    if (!board.loaded) {
      return const Center(child: CircularProgressIndicator());
    }
    return LayoutBuilder(
      builder: (context, box) {
        if (box.maxWidth >= 900) {
          return Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final (i, status) in Order.boardStatuses.indexed) ...[
                  if (i > 0) const SizedBox(width: 14),
                  Expanded(
                    child: _Column(status: status, board: board),
                  ),
                ],
              ],
            ),
          );
        }
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
              child: _ColumnTabs(
                selected: _column,
                board: board,
                onSelected: (status) => setState(() => _column = status),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: _Column(status: _column, board: board, header: false),
              ),
            ),
          ],
        );
      },
    );
  }
}

/// A column tray holding order plates.
class _Column extends StatelessWidget {
  const _Column({
    required this.status,
    required this.board,
    this.header = true,
  });
  final String status;
  final StoreBoard board;
  final bool header;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final orders = board.column(status);
    return Container(
      decoration: BoxDecoration(
        color: t.sunk,
        borderRadius: BorderRadius.circular(Radii.xl),
        border: Border.all(color: t.hairline),
      ),
      child: Column(
        children: [
          if (header)
            Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(14, 14, 16, 6),
              child: Row(
                children: [
                  _ColumnIcon(status: status),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      s.t('col_$status'),
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  _Count(count: orders.length, gold: status == 'received'),
                ],
              ),
            ),
          Expanded(
            child: orders.isEmpty
                ? Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Ph.receipt, size: 32, color: t.muted),
                        const SizedBox(height: 8),
                        Text(
                          s.t('emptyColumn'),
                          style: TextStyle(color: t.muted),
                        ),
                      ],
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(8, 8, 8, 12),
                    itemCount: orders.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (context, i) => OrderCard(
                      key: ValueKey(orders[i].id),
                      order: orders[i],
                      showStore: board.multiStore,
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _ColumnIcon extends StatelessWidget {
  const _ColumnIcon({required this.status});
  final String status;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final fresh = status == 'received';
    final icon = Icon(
      _columnIcons[status],
      size: 18,
      color: fresh ? Gold.c400 : scheme.primary,
    );
    return SizedBox(
      width: 36,
      height: 36,
      child: fresh
          ? ClipOval(
              child: GlazePanel(child: Center(child: icon)),
            )
          : DecoratedBox(
              decoration: BoxDecoration(
                color: t.surface,
                shape: BoxShape.circle,
                boxShadow: t.raised,
              ),
              child: Center(child: icon),
            ),
    );
  }
}

class _Count extends StatelessWidget {
  const _Count({required this.count, required this.gold});
  final int count;
  final bool gold;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final on = gold && count > 0;
    return Container(
      constraints: const BoxConstraints(minWidth: 26),
      height: 26,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      alignment: Alignment.center,
      decoration: ShapeDecoration(
        color: on ? Gold.c400 : t.surface,
        shape: const StadiumBorder(),
      ),
      child: Text(
        '$count',
        style: TextStyle(
          fontWeight: FontWeight.w700,
          fontSize: 13,
          color: on ? Lapis.c950 : t.muted,
        ),
      ),
    );
  }
}

/// Portrait: one column at a time, with counts.
class _ColumnTabs extends StatelessWidget {
  const _ColumnTabs({
    required this.selected,
    required this.board,
    required this.onSelected,
  });
  final String selected;
  final StoreBoard board;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        for (final (i, status) in Order.boardStatuses.indexed) ...[
          if (i > 0) const SizedBox(width: 8),
          Expanded(
            child: Semantics(
              button: true,
              selected: selected == status,
              child: Pressable(
                onTap: () => onSelected(status),
                child: AnimatedContainer(
                  duration: Motion.fast,
                  curve: Motion.out,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: selected == status
                        ? scheme.secondaryContainer
                        : t.surface,
                    borderRadius: BorderRadius.circular(Radii.md),
                    border: Border.all(
                      color: selected == status ? scheme.primary : t.hairline,
                      width: selected == status ? 1.5 : 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _columnIcons[status],
                        size: 18,
                        color: scheme.primary,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          s.t('col_$status'),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontWeight: selected == status
                                ? FontWeight.w700
                                : FontWeight.w500,
                          ),
                        ),
                      ),
                      _Count(
                        count: board.column(status).length,
                        gold: status == 'received',
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
