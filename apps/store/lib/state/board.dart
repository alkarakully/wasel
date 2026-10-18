import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:wasel_core/wasel_core.dart';

/// The owner's stores and their open orders, kept current over the live
/// socket. Reloads after every reconnect, so nothing missed offline is lost.
class StoreBoard extends ChangeNotifier {
  StoreBoard(this.api, this.live);

  final ApiClient api;
  final LiveUpdates live;
  StreamSubscription? _events;

  List<VendorDetail>? stores;
  int? storeId;
  List<Order> orders = [];
  bool loaded = false;
  bool connected = true;

  /// Error code to show once (cleared when tapped).
  String? notice;

  /// Saved store open state and stock, newer than [stores].
  final Map<int, bool> _open = {};
  final Map<int, bool> _available = {};

  /// New orders someone tapped "Stop ringing" for; a newer order rings again.
  final Set<int> _silenced = {};

  VendorDetail? get store {
    final list = stores;
    if (list == null || list.isEmpty) return null;
    return list.firstWhere((s) => s.id == storeId, orElse: () => list.first);
  }

  bool get multiStore => (stores?.length ?? 0) > 1;
  bool isOpen(VendorDetail s) => _open[s.id] ?? s.isOpen;
  bool isAvailable(Product p) => _available[p.id] ?? p.isAvailable;

  List<Order> column(String status) =>
      orders.where((o) => o.status == status).toList()
        ..sort((a, b) => a.createdAt.compareTo(b.createdAt));

  List<Order> get newOrders => column('received');
  bool get ringing => newOrders.any((o) => !_silenced.contains(o.id));

  void start() {
    _events ??= live.events.listen(_onEvent);
    loadStores();
    reload();
  }

  void stop() {
    _events?.cancel();
    _events = null;
    stores = null;
    orders = [];
    loaded = false;
    _silenced.clear();
  }

  void _onEvent(Map<String, dynamic> event) {
    switch (event['type']) {
      case 'connected':
        connected = true;
        reload(); // catch up on anything missed while offline
      case 'disconnected':
        connected = false;
        notifyListeners();
      case 'order.updated':
        upsert(Order.fromJson(event['order']));
    }
  }

  Future<void> loadStores() async {
    try {
      stores = await api.myStores();
      storeId ??= stores!.isEmpty ? null : stores!.first.id;
      _open.clear();
      _available.clear();
      notifyListeners();
    } on ApiException catch (error) {
      _fail(error);
    }
  }

  Future<void> reload() async {
    try {
      orders = await api.storeBoard();
      loaded = true;
      notifyListeners();
    } on ApiException catch (error) {
      _fail(error);
    }
  }

  /// Put a fresh copy of an order on the board, or take it off when it's done.
  void upsert(Order order) {
    orders = [
      for (final o in orders)
        if (o.id != order.id) o,
      if (Order.boardStatuses.contains(order.status)) order,
    ];
    notifyListeners();
  }

  void selectStore(int id) {
    storeId = id;
    notifyListeners();
  }

  void silence() {
    _silenced.addAll(newOrders.map((o) => o.id));
    notifyListeners();
  }

  void dismissNotice() {
    notice = null;
    notifyListeners();
  }

  Future<void> accept(Order order, int prepMinutes) =>
      _step(() => api.acceptOrder(order.id, prepMinutes));

  Future<void> reject(Order order, String reason) =>
      _step(() => api.rejectOrder(order.id, reason));

  Future<void> markReady(Order order) => _step(() => api.markReady(order.id));

  Future<void> _step(Future<Order> Function() call) async {
    try {
      upsert(await call());
    } on ApiException catch (error) {
      _fail(error);
      if (error.code == 'invalid_transition') reload();
    }
  }

  Future<void> setOpen(VendorDetail s, bool open) async {
    _open[s.id] = open;
    notifyListeners();
    try {
      _open[s.id] = await api.setStoreOpen(s.id, open);
    } on ApiException catch (error) {
      _open[s.id] = !open;
      _fail(error);
    }
    notifyListeners();
  }

  /// Flips right away so the switch feels instant; undoes it if the server says no.
  Future<void> setAvailable(Product p, bool available) async {
    _available[p.id] = available;
    notifyListeners();
    try {
      _available[p.id] = await api.setProductAvailable(p.id, available);
    } on ApiException catch (error) {
      _available[p.id] = !available;
      _fail(error);
    }
    notifyListeners();
  }

  void _fail(ApiException error) {
    notice = 'err_${error.code}';
    notifyListeners();
  }

  @override
  void dispose() {
    _events?.cancel();
    super.dispose();
  }
}
