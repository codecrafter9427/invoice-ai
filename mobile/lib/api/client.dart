import 'dart:convert';

import 'package:http/http.dart' as http;

/// Default API for Android emulator → host machine.
/// iOS simulator / desktop: use http://localhost:8004
/// Physical device: set [ApiClient.baseUrl] to your LAN IP.
class ApiClient {
  ApiClient({this.baseUrl = 'http://10.0.2.2:8004'});

  String baseUrl;
  String? accessToken;

  Uri _uri(String path, [Map<String, String>? query]) {
    final root = baseUrl.replaceAll(RegExp(r'/$'), '');
    return Uri.parse('$root$path').replace(queryParameters: query);
  }

  Map<String, String> _headers({bool json = true}) {
    final h = <String, String>{};
    if (json) h['Content-Type'] = 'application/json';
    if (accessToken != null) h['Authorization'] = 'Bearer $accessToken';
    return h;
  }

  Future<Map<String, dynamic>> demoLogin(String email, String password) async {
    final res = await http.post(
      _uri('/api/v1/auth/demo-login'),
      headers: _headers(),
      body: jsonEncode({'email': email, 'password': password}),
    );
    final body = _decode(res);
    if (res.statusCode != 200) {
      throw ApiException(_errorMessage(body, res.statusCode));
    }
    accessToken = body['access_token'] as String?;
    return body;
  }

  Future<List<Map<String, dynamic>>> listInvoices({
    String? status,
    String? search,
    int pageSize = 50,
  }) async {
    final q = <String, String>{'page_size': '$pageSize'};
    if (status != null && status.isNotEmpty) q['status'] = status;
    if (search != null && search.isNotEmpty) q['search'] = search;
    final res = await http.get(_uri('/api/v1/invoices', q), headers: _headers());
    final body = _decode(res);
    if (res.statusCode != 200) {
      throw ApiException(_errorMessage(body, res.statusCode));
    }
    final items = body['items'] as List<dynamic>? ?? [];
    return items.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> listSuppliers() async {
    final res = await http.get(
      _uri('/api/v1/suppliers', {'page_size': '50'}),
      headers: _headers(),
    );
    final body = _decode(res);
    if (res.statusCode != 200) {
      throw ApiException(_errorMessage(body, res.statusCode));
    }
    final items = body['items'] as List<dynamic>? ?? [];
    return items.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> createInvoice(Map<String, dynamic> payload) async {
    final res = await http.post(
      _uri('/api/v1/invoices'),
      headers: _headers(),
      body: jsonEncode(payload),
    );
    final body = _decode(res);
    if (res.statusCode != 201 && res.statusCode != 200) {
      throw ApiException(_errorMessage(body, res.statusCode));
    }
    return body;
  }

  Future<Map<String, dynamic>> extractInvoice(String text) async {
    final res = await http.post(
      _uri('/api/v1/ai/invoice-extract'),
      headers: _headers(),
      body: jsonEncode({
        'input': {'text': text, 'ocr_text': text},
        'context_ids': <String>[],
        'options': <String, dynamic>{},
      }),
    );
    final body = _decode(res);
    if (res.statusCode != 200) {
      throw ApiException(_errorMessage(body, res.statusCode));
    }
    return body;
  }

  Map<String, dynamic> _decode(http.Response res) {
    if (res.body.isEmpty) return <String, dynamic>{};
    final decoded = jsonDecode(res.body);
    if (decoded is Map<String, dynamic>) return decoded;
    return <String, dynamic>{'data': decoded};
  }

  String _errorMessage(Map<String, dynamic> body, int status) {
    final err = body['error'] ?? body['detail']?['error'];
    if (err is Map && err['message'] is String) return err['message'] as String;
    return 'Request failed ($status)';
  }
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;

  @override
  String toString() => message;
}
