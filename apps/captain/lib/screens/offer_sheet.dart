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
    final order = widget.offer.order;
    final left = widget.offer.timeLeft;
    final fraction = _total.inMilliseconds == 0
        ? 0.0
        : left.inMilliseconds / _total.inMilliseconds;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    s.t('offerTitle'),
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                Text(
                  s.t('offerSeconds', {
                    's': (left.inMilliseconds / 1000).ceil(),
                  }),
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: scheme.primary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(value: fraction, minHeight: 8),
            ),
            const SizedBox(height: 18),
            Text(
              order.vendorName,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            Text(
              s.t('offerDistance', {
                'km': widget.offer.distanceKm.toStringAsFixed(1),
              }),
              style: TextStyle(color: scheme.onSurfaceVariant),
            ),
            const SizedBox(height: 10),
            Text('${s.t('deliverTo')}: ${order.deliveryAddress}'),
            const SizedBox(height: 4),
            Text(
              order.cashToCollect > 0
                  ? s.t('collectCash', {'amount': s.money(order.cashToCollect)})
                  : s.t('paidInApp'),
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(s.t(_error!), style: TextStyle(color: scheme.error)),
            ],
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    key: const Key('decline-offer'),
                    onPressed: _busy ? null : () => _answer(false),
                    child: Text(s.t('offerSkip')),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: FilledButton(
                    key: const Key('accept-offer'),
                    onPressed: _busy ? null : () => _answer(true),
                    child: Text(s.t('takeOrder')),
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
