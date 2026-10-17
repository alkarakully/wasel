import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'models.dart';

class ApiException implements Exception {
  ApiException(this.code, [this.status, this.retryAfter]);

  /// The backend's error code (e.g. "vendor_closed"), "invalid_phone" for a
  /// rejected phone field, or "network" when the server couldn't be reached.
  final String code;
  final int? status;
  final int? retryAfter;

  @override
  String toString() => 'ApiException($code, $status)';
}

class ApiClient {
  ApiClient({http.Client? client, this.baseUrl = Config.apiUrl})
    : _http = client ?? http.Client();

  final http.Client _http;
  final String baseUrl;
  String? token;

  Uri socketUri() {
    final base = Uri.parse(baseUrl);
    return base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: '/ws/orders/',
      queryParameters: {'token': token ?? ''},
    );
  }

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
  }) async {
    final uri = Uri.parse('$baseUrl$path').replace(queryParameters: query);
    final request = http.Request(method, uri)
      ..headers['Accept'] = 'application/json'
      ..headers['Content-Type'] = 'application/json';
    if (token != null) request.headers['Authorization'] = 'Token $token';
    if (body != null) request.body = jsonEncode(body);

    http.Response response;
    try {
      response = await http.Response.fromStream(
        await _http.send(request).timeout(const Duration(seconds: 15)),
      );
    } on SocketException {
      throw ApiException('network');
    } on http.ClientException {
      throw ApiException('network');
    } on Exception {
      throw ApiException('network');
    }

    final data = response.body.isEmpty
        ? null
        : jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode >= 400) throw _error(response.statusCode, data);
    return data;
  }

  ApiException _error(int status, dynamic data) {
    if (data is Map) {
      if (data['error'] is String) {
        return ApiException(data['error'], status, data['retry_after']);
      }
      if (data.containsKey('phone')) {
        return ApiException('invalid_phone', status);
      }
      if (data.containsKey('code')) return ApiException('invalid_code', status);
    }
    return ApiException(status == 401 ? 'unauthorized' : 'generic', status);
  }

  // --- Auth ------------------------------------------------------------------

  /// Returns the normalized phone, the channel used and seconds until resend.
  Future<({String phone, String channel, int resendIn})> requestCode(
    String phone,
    String channel,
  ) async {
    final data = await _send(
      'POST',
      '/api/auth/otp/request/',
      body: {'phone': phone, 'channel': channel},
    );
    return (
      phone: data['phone'] as String,
      channel: data['channel'] as String,
      resendIn: data['resend_in'] as int,
    );
  }

  Future<({String token, User user})> verifyCode(
    String phone,
    String code,
  ) async {
    final data = await _send(
      'POST',
      '/api/auth/otp/verify/',
      body: {'phone': phone, 'code': code},
    );
    return (token: data['token'] as String, user: User.fromJson(data['user']));
  }

  Future<User> me() async => User.fromJson(await _send('GET', '/api/auth/me/'));

  Future<void> logout() => _send('POST', '/api/auth/logout/');

  // --- Stores ----------------------------------------------------------------

  Future<List<Vendor>> vendors({required GeoPoint at, String? cuisine}) async {
    final data = await _send(
      'GET',
      '/api/vendors/',
      query: {'lat': '${at.lat}', 'lng': '${at.lng}', 'cuisine': ?cuisine},
    );
    return [for (final v in data['results']) Vendor.fromJson(v)];
  }

  Future<VendorDetail> vendor(int id) async =>
      VendorDetail.fromJson(await _send('GET', '/api/vendors/$id/'));

  Future<List<Offer>> bannerOffers() async {
    final data = await _send('GET', '/api/offers/', query: {'banner': '1'});
    return [for (final o in data['results']) Offer.fromJson(o)];
  }

  // --- Orders ----------------------------------------------------------------

  Future<Quote> quote(Map<String, dynamic> cart) async =>
      Quote.fromJson(await _send('POST', '/api/orders/quote/', body: cart));

  Future<Order> placeOrder(Map<String, dynamic> order) async =>
      Order.fromJson(await _send('POST', '/api/orders/', body: order));

  Future<List<Order>> orders() async {
    final data = await _send('GET', '/api/orders/');
    return [for (final o in data['results']) Order.fromJson(o)];
  }

  Future<Order> order(int id) async =>
      Order.fromJson(await _send('GET', '/api/orders/$id/'));
}
