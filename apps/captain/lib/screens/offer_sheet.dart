import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

/// "New order for you": accept or skip before the countdown runs out.
///
/// Pops with the claimed [Order] on accept, or null when skipped, expired or
/// withdrawn ([closed] emits this offer's id when the server ends it).
class OfferSheet extends StatefulWidget {
  const OfferSheet({super.key, required this.offer, required this.closed});

  final DispatchOffer offer;
  final Stream<int> closed;

  @override
  State<OfferSheet> createState() => _OfferSheetState();
}

class _OfferSheetState extends State<OfferSheet> {
  late final Duration _total = widget.offer.timeLeft;
  Timer? _tick;
  StreamSubscription<int>? _closed;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tick = Timer.periodic(const Duration(milliseconds: 250), (_) {
      if (widget.offer.timeLeft == Duration.zero) {
        _finish(null);
      } else {
        setState(() {});
      }
    });
    _closed = widget.closed
        .where((id) => id == widget.offer.id)
        .listen((_) => _finish(null));
  }

  @override
  void dispose() {
    _tick?.cancel();
    _closed?.cancel();
    super.dispose();
  }

  void _finish(Order? order) {
    _tick?.cancel();
    if (mounted && Navigator.of(context).canPop()) {
      Navigator.of(context).pop(order);
    }
  }

  Future<void> _answer(bool accept) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final api = context.read<ApiClient>();
    try {
      if (accept) {
        _finish(await api.acceptOffer(widget.offer.id));
      } else {
        await api.declineOffer(widget.offer.id);
        _finish(null);
      }
    } on ApiException catch (error) {
      if (error.code == 'offer_gone') {
        _finish(null);
        return;
      }
      setState(() {
        _busy = false;
        _error = 'err_${error.code}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final scheme = Theme.of(context).colorScheme;
    final t = WaselTheme.of(context);
    final order = widget.offer.order;
    final left = widget.offer.timeLeft;
    final fraction = _total.inMilliseconds == 0
        ? 0.0
        : left.inMilliseconds / _total.inMilliseconds;
    final cash = order.cashToCollect > 0;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            GlazePanel(
              radius: Radii.lg,
              padding: const EdgeInsets.fromLTRB(20, 18, 18, 20),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          s.t('offerTitle'),
                          style: const TextStyle(
                            color: Gold.c300,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          order.vendorName,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            height: 1.3,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            const Icon(
                              Ph.navigationArrow,
                              size: 16,
                              color: Lapis.c200,
                            ),
                            const SizedBox(width: 6),
                            Flexible(
                              child: Text(
                                s.t('offerDistance', {
                                  'km': widget.offer.distanceKm.toStringAsFixed(
                                    1,
                                  ),
                                }),
                                style: const TextStyle(color: Lapis.c200),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Countdown ring: gold drains as the offer runs out.
                  SizedBox(
                    width: 72,
                    height: 72,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        CircularProgressIndicator(
                          value: fraction,
                          strokeWidth: 5,
                          strokeCap: StrokeCap.round,
                          // Gold while there's time, warming to coral as it runs out.
                          color: Color.lerp(
                            const Color(0xFFFF8A80),
                            Gold.c400,
                            (fraction * 3).clamp(0.0, 1.0),
                          ),
                          backgroundColor: Colors.white.withValues(alpha: 0.12),
                        ),
                        Center(
                          child: Text(
                            s.t('offerSeconds', {
                              's': (left.inMilliseconds / 1000).ceil(),
                            }),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              fontFeatures: [FontFeature.tabularFigures()],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Ph.mapPin, size: 20, color: t.muted),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      '${s.t('deliverTo')}: ${order.deliveryAddress}',
                      style: const TextStyle(height: 1.45),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: cash ? goldWash(context) : t.sunk,
                borderRadius: BorderRadius.circular(Radii.md),
              ),
              child: Row(
                children: [
                  Icon(
                    cash ? Ph.money : Ph.checkCircle,
                    size: 22,
                    color: cash ? t.goldText : t.success,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      cash
                          ? s.t('collectCash', {
                              'amount': s.money(order.cashToCollect),
                            })
                          : s.t('paidInApp'),
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        color: cash ? t.goldText : t.ink,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(s.t(_error!), style: TextStyle(color: scheme.error)),
            ],
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 58,
                    child: OutlinedButton(
                      key: const Key('decline-offer'),
                      onPressed: _busy ? null : () => _answer(false),
                      child: Text(s.t('offerSkip')),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: PillButton(
                    key: const Key('accept-offer'),
                    tone: PillTone.gold,
                    busy: _busy,
                    onPressed: () => _answer(true),
                    label: s.t('takeOrder'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
