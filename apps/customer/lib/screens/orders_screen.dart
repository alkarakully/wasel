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
    return Scaffold(
      appBar: AppBar(title: Text(s.t('myOrders'))),
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
          if (orders.isEmpty) return Center(child: Text(s.t('noOrders')));
          return ListView.separated(
            itemCount: orders.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final order = orders[i];
              return ListTile(
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 6,
                ),
                title: Text(
                  order.vendorName,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                subtitle: Text(s.t('status_${order.status}')),
                trailing: Text(s.money(order.total)),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => TrackingScreen(orderId: order.id),
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
