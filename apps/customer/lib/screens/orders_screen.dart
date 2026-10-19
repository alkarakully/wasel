import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import 'tracking_screen.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  late Future<List<Order>> _orders = context.read<ApiClient>().orders();

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: t.canvas,
      appBar: AppBar(
        backgroundColor: t.canvas,
        title: Text(
          s.t('myOrders'),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      body: FutureBuilder<List<Order>>(
        future: _orders,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(
              child: OutlinedButton(
                onPressed: () => setState(
                  () => _orders = context.read<ApiClient>().orders(),
                ),
                child: Text(s.t('retry')),
              ),
            );
          }
          final orders = snapshot.data;
          if (orders == null) {
            return const Center(child: CircularProgressIndicator());
          }
          if (orders.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      color: t.sunk,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Ph.receipt, size: 32, color: t.muted),
                  ),
                  const SizedBox(height: 16),
                  Text(s.t('noOrders'), style: TextStyle(color: t.muted)),
                ],
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            itemCount: orders.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (context, i) {
              final order = orders[i];
              final live = !order.isFinished;
              return Pressable(
                scale: 0.98,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => TrackingScreen(orderId: order.id),
                  ),
                ),
                child: Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: t.surface,
                    borderRadius: BorderRadius.circular(Radii.lg),
                    border: Border.all(
                      color: live ? scheme.primary : t.hairline,
                      width: live ? 1.5 : 1,
                    ),
                    boxShadow: t.raised,
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: live ? GlazePanel.gradient : null,
                          color: live ? null : t.sunk,
                        ),
                        child: Icon(
                          live ? Ph.moped : Ph.receipt,
                          size: 22,
                          color: live ? Gold.c400 : t.muted,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              order.vendorName,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            Text(
                              s.t('status_${order.status}'),
                              style: TextStyle(color: t.muted, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                      Text(
                        s.money(order.total, order.currency),
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
