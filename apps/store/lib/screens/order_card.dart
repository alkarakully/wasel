import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../print/printer.dart';
import '../state/board.dart';

const prepChoices = [10, 15, 20, 30, 45];

/// One order: what to cook, how it's paid, and the next step for the store.
class OrderCard extends StatefulWidget {
  const OrderCard({super.key, required this.order, required this.showStore});
  final Order order;
  final bool showStore;

  @override
  State<OrderCard> createState() => _OrderCardState();
}

class _OrderCardState extends State<OrderCard>
    with SingleTickerProviderStateMixin {
  int _prep = 15;
  bool _busy = false;

  /// New orders breathe a lapis glow so they're seen across the kitchen.
  late final _glow = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1600),
  );

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncGlow();
  }

  @override
  void didUpdateWidget(OrderCard old) {
    super.didUpdateWidget(old);
    _syncGlow();
  }

  void _syncGlow() {
    final fresh = widget.order.status == 'received';
    if (fresh && !MediaQuery.of(context).disableAnimations) {
      if (!_glow.isAnimating) _glow.repeat(reverse: true);
    } else {
      _glow.stop();
      _glow.value = 0;
    }
  }

  @override
  void dispose() {
    _glow.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function(StoreBoard board) step) async {
    HapticFeedback.mediumImpact();
    setState(() => _busy = true);
    await step(context.read<StoreBoard>());
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _print(Order order) async {
    final s = S.read(context);
    try {
      await context.read<OrderPrinter>().printOrder(order, s);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(s.t('printFailed'))));
    }
  }

  Future<void> _accept() async {
    final board = context.read<StoreBoard>();
    HapticFeedback.mediumImpact();
    setState(() => _busy = true);
    final accepted = await board.accept(widget.order, _prep);
    if (!mounted) return;
    setState(() => _busy = false);
    if (accepted != null && board.autoPrint) await _print(accepted);
  }

  Future<void> _reject() async {
    final reason = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => RejectSheet(orderId: widget.order.id),
    );
    if (reason != null && mounted) {
      await _run((board) => board.reject(widget.order, reason));
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final order = widget.order;
    final fresh = order.status == 'received';
    final age = DateTime.now().difference(order.createdAt).inMinutes;
    final ago = age < 1
        ? s.t('justNow')
        : age < 60
        ? s.t('minutesAgo', {'n': age})
        : s.t('hoursAgo', {'n': age ~/ 60});
    final reduce = MediaQuery.of(context).disableAnimations;

    final card = AnimatedBuilder(
      animation: _glow,
      builder: (context, child) => Container(
        decoration: BoxDecoration(
          color: t.surface,
          borderRadius: BorderRadius.circular(Radii.lg),
          border: Border.all(
            color: fresh ? scheme.primary : t.hairline,
            width: fresh ? 2 : 1,
          ),
          boxShadow: [
            ...t.raised,
            if (fresh)
              BoxShadow(
                color: scheme.primary.withValues(alpha: 0.22 * _glow.value),
                blurRadius: 0,
                spreadRadius: 6 * _glow.value,
              ),
          ],
        ),
        child: child,
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Text(
                  '#${order.id}',
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                ),
                if (widget.showStore) ...[
                  const SizedBox(width: 10),
                  Flexible(
                    child: Text(
                      order.vendorName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: t.muted),
                    ),
                  ),
                ],
                const Spacer(),
                Icon(Ph.clock, size: 16, color: t.muted),
                const SizedBox(width: 4),
                Text(ago, style: TextStyle(color: t.muted, fontSize: 14)),
                const SizedBox(width: 6),
                IconButton(
                  key: Key('print-${order.id}'),
                  tooltip: s.t('printOrder', {'id': order.id}),
                  visualDensity: VisualDensity.compact,
                  onPressed: () => _print(order),
                  icon: Icon(Ph.printer, size: 20, color: scheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Divider(height: 1, color: t.hairline),
            const SizedBox(height: 10),
            for (final item in order.items)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      constraints: const BoxConstraints(minWidth: 44),
                      margin: const EdgeInsetsDirectional.only(end: 10),
                      child: Text(
                        item.soldByKg
                            ? '${_qty(item.quantity)} ${s.t('kg')}'
                            : '${_qty(item.quantity)}×',
                        textDirection: TextDirection.ltr,
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                          color: scheme.primary,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item.name(s.lang),
                            style: const TextStyle(fontSize: 17),
                          ),
                          if (item.modifiers.isNotEmpty)
                            Text(
                              item.modifiers
                                  .map(
                                    (m) => localizedName(
                                      s.lang,
                                      m['ar']!,
                                      m['ku']!,
                                      m['en']!,
                                    ),
                                  )
                                  .join('، '),
                              style: TextStyle(color: t.muted, fontSize: 14),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 10),
            Divider(height: 1, color: t.hairline),
            const SizedBox(height: 10),
            Row(
              children: [
                _PayChip(cash: order.paymentType == 'cod'),
                const Spacer(),
                Text(
                  s.money(order.total),
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            ..._nextStep(s, t, scheme),
          ],
        ),
      ),
    );

    // Arrives with a short rise; later rebuilds don't replay it.
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: reduce ? Duration.zero : Motion.medium,
      curve: Motion.out,
      builder: (context, v, child) => Opacity(
        opacity: v,
        child: Transform.translate(
          offset: Offset(0, 12 * (1 - v)),
          child: child,
        ),
      ),
      child: card,
    );
  }

  List<Widget> _nextStep(S s, WaselTheme t, ColorScheme scheme) {
    final order = widget.order;
    switch (order.status) {
      case 'received':
        return [
          const SizedBox(height: 14),
          Text(
            s.t('prepTime'),
            style: TextStyle(color: t.muted, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final minutes in prepChoices)
                ChoiceChip(
                  key: Key('prep-$minutes'),
                  label: Text('$minutes ${s.t('min')}'),
                  selected: _prep == minutes,
                  showCheckmark: false,
                  onSelected: (_) {
                    HapticFeedback.selectionClick();
                    setState(() => _prep = minutes);
                  },
                ),
            ],
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, box) {
              final accept = PillButton(
                key: Key('accept-${order.id}'),
                label: s.t('accept'),
                icon: Ph.check,
                busy: _busy,
                onPressed: _accept,
              );
              final reject = SizedBox(
                height: 58,
                child: OutlinedButton.icon(
                  key: Key('reject-${order.id}'),
                  onPressed: _busy ? null : _reject,
                  icon: const Icon(Ph.x, size: 18),
                  label: Text(s.t('reject')),
                ),
              );
              // Narrow columns: stack, so neither label has to wrap.
              if (box.maxWidth < 380) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [accept, const SizedBox(height: 8), reject],
                );
              }
              return Row(
                children: [
                  Expanded(flex: 2, child: accept),
                  const SizedBox(width: 10),
                  Expanded(child: reject),
                ],
              );
            },
          ),
        ];
      case 'preparing':
        final ready = order.estimatedReadyAt;
        final left = ready?.difference(DateTime.now()).inMinutes;
        final late = left != null && left < 0;
        return [
          if (left != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(
                  late ? Ph.warningCircle : Ph.hourglass,
                  size: 18,
                  color: late ? scheme.error : t.muted,
                ),
                const SizedBox(width: 6),
                Text(
                  late
                      ? s.t('late', {'n': -left})
                      : s.t('readyIn', {'n': left}),
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: late ? scheme.error : t.muted,
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 14),
          PillButton(
            key: Key('ready-${order.id}'),
            label: s.t('markReady'),
            icon: Ph.check,
            busy: _busy,
            onPressed: () => _run((b) => b.markReady(order)),
          ),
        ];
      default:
        return [
          const SizedBox(height: 14),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: t.sunk,
              borderRadius: BorderRadius.circular(Radii.sm),
            ),
            child: Row(
              children: [
                Icon(Ph.moped, size: 20, color: scheme.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    s.t(
                      order.captainId != null
                          ? 'captainComing'
                          : 'waitingCaptain',
                    ),
                    style: TextStyle(
                      color: t.muted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ];
    }
  }

  static String _qty(double q) =>
      q == q.roundToDouble() ? q.round().toString() : q.toStringAsFixed(1);
}

class _PayChip extends StatelessWidget {
  const _PayChip({required this.cash});
  final bool cash;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: ShapeDecoration(
        color: cash ? goldWash(context) : t.sunk,
        shape: const StadiumBorder(),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            cash ? Ph.money : Ph.creditCard,
            size: 16,
            color: cash ? t.goldText : t.muted,
          ),
          const SizedBox(width: 6),
          Text(
            s.t(cash ? 'cash' : 'paid'),
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: cash ? t.goldText : t.muted,
            ),
          ),
        ],
      ),
    );
  }
}

const _reasons = ['reason_out_of_stock', 'reason_busy', 'reason_closing'];

/// Pick a common reason or type one; the customer sees it. Returns the reason.
class RejectSheet extends StatefulWidget {
  const RejectSheet({super.key, required this.orderId});
  final int orderId;

  @override
  State<RejectSheet> createState() => _RejectSheetState();
}

class _RejectSheetState extends State<RejectSheet> {
  String _choice = _reasons.first;
  final _other = TextEditingController();

  @override
  void dispose() {
    _other.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final reason = _choice == 'other' ? _other.text.trim() : s.t(_choice);

    Widget option(String key) {
      final selected = _choice == key;
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Semantics(
          button: true,
          selected: selected,
          child: Pressable(
            onTap: () => setState(() => _choice = key),
            child: AnimatedContainer(
              duration: Motion.fast,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                color: selected ? scheme.secondaryContainer : t.sunk,
                borderRadius: BorderRadius.circular(Radii.md),
                border: Border.all(
                  color: selected ? scheme.primary : t.hairline,
                  width: selected ? 1.5 : 1,
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      s.t(key),
                      style: TextStyle(
                        fontWeight: selected
                            ? FontWeight.w700
                            : FontWeight.w500,
                        color: selected ? scheme.primary : t.ink,
                      ),
                    ),
                  ),
                  if (selected) Icon(Ph.checkCircle, color: scheme.primary),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          22,
          0,
          22,
          16 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: SingleChildScrollView(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  s.t('rejectTitle', {'id': widget.orderId}),
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(s.t('rejectReason'), style: TextStyle(color: t.muted)),
                const SizedBox(height: 16),
                for (final key in _reasons) option(key),
                option('other'),
                if (_choice == 'other')
                  TextField(
                    key: const Key('other-reason'),
                    controller: _other,
                    autofocus: true,
                    maxLength: 255,
                    decoration: InputDecoration(hintText: s.t('otherReason')),
                    onChanged: (_) => setState(() {}),
                  ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: SizedBox(
                        height: 56,
                        child: OutlinedButton(
                          onPressed: () => Navigator.pop(context),
                          child: Text(s.t('cancel')),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      flex: 2,
                      child: SizedBox(
                        height: 56,
                        child: FilledButton(
                          key: const Key('confirm-reject'),
                          style: FilledButton.styleFrom(
                            backgroundColor: scheme.error,
                            foregroundColor: scheme.onError,
                          ),
                          onPressed: reason.isEmpty
                              ? null
                              : () => Navigator.pop(context, reason),
                          child: Text(s.t('confirmReject')),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
