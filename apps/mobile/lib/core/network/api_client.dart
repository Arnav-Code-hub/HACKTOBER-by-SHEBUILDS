import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:http/http.dart' as http;

import '../errors/failure.dart';

/// Authenticated business API transport. Cloudinary upload requests use a
/// separate transport and never receive this Authorization header.
class ApiClient {
  ApiClient({required String baseUrl, required this.token, http.Client? client})
    : _base = _validatedBase(baseUrl),
      _client = client ?? http.Client();

  final Uri _base;
  final Future<String?> Function() token;
  final http.Client _client;

  static Uri _validatedBase(String value) {
    final uri = Uri.tryParse(value);
    final local = uri?.host == 'localhost' || uri?.host == '127.0.0.1';
    if (uri == null ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        (uri.scheme != 'https' && !(uri.scheme == 'http' && local))) {
      throw const ValidationFailure(
        'API_BASE_URL must be HTTPS (HTTP is allowed for localhost).',
      );
    }
    if (uri.path != '' &&
        uri.path != '/' &&
        uri.path != '/api/v1' &&
        uri.path != '/api/v1/') {
      throw const ValidationFailure(
        'API_BASE_URL must be the API origin, without another path.',
      );
    }
    return uri.replace(path: '/api/v1');
  }

  Future<void>? _warmUp;

  /// Waits for a sleeping free-tier host to wake before the first real call.
  ///
  /// Unauthenticated `GET /health` (outside `/api/v1`), so no token is sent.
  /// Concurrent callers share one request; a failure is not cached, so the
  /// next caller tries again. A waking host answers 502/503 or drops the
  /// connection for up to about a minute, so attempts are spaced out rather
  /// than spent back to back.
  Future<void> warmUp({
    Duration timeout = const Duration(seconds: 30),
    int attempts = 40,
    Duration pause = const Duration(seconds: 3),
    Duration budget = const Duration(minutes: 2),
  }) => _warmUp ??= _pingHealth(timeout, attempts, pause, budget).catchError((
    Object error,
  ) {
    _warmUp = null;
    throw error;
  });

  Future<void> _pingHealth(
    Duration timeout,
    int attempts,
    Duration pause,
    Duration budget,
  ) async {
    final uri = _base.replace(path: '/health');
    final elapsed = Stopwatch()..start();
    for (var attempt = 1; attempt <= attempts; attempt++) {
      if (attempt > 1) await Future<void>.delayed(pause);
      final remaining = budget - elapsed.elapsed;
      if (remaining <= Duration.zero) break;
      try {
        final response = await _client
            .get(
              uri,
              headers: const <String, String>{'Accept': 'application/json'},
            )
            .timeout(remaining < timeout ? remaining : timeout);
        if (response.statusCode >= 200 && response.statusCode < 300) return;
      } on TimeoutException {
        // Retry below: the host may still be starting.
      } on http.ClientException {
        // Same.
      }
    }
    throw const NetworkFailure(
      'The server is starting up or unreachable. Retry in a minute.',
    );
  }

  Future<Object?> get(
    String path, {
    Map<String, String>? query,
    Duration? timeout,
  }) => _request('GET', path, query: query, timeout: timeout);

  Future<Object?> post(
    String path,
    Map<String, Object?> body, {
    String? idempotencyKey,
  }) => _request('POST', path, body: body, idempotencyKey: idempotencyKey);

  Future<Object?> _request(
    String method,
    String path, {
    Map<String, String>? query,
    Map<String, Object?>? body,
    String? idempotencyKey,
    Duration? timeout,
  }) async {
    final limit = timeout ?? const Duration(seconds: 25);
    try {
      final idToken = await token();
      if (idToken == null || idToken.isEmpty) {
        throw const AuthFailure('Please sign in again.');
      }
      final uri = _base.replace(
        path: '${_base.path.replaceFirst(RegExp(r'/$'), '')}/$path',
        queryParameters: query,
      );
      final request = http.Request(method, uri)
        ..headers.addAll(<String, String>{
          'Authorization': 'Bearer $idToken',
          'Accept': 'application/json',
          if (body != null) 'Content-Type': 'application/json',
        });
      if (idempotencyKey != null) {
        request.headers['Idempotency-Key'] = idempotencyKey;
      }
      if (body != null) request.body = jsonEncode(body);
      final response = await http.Response.fromStream(
        await _client.send(request).timeout(limit),
      ).timeout(limit);
      if (response.statusCode == 401) {
        throw const AuthFailure(
          'Your session expired. Sign out and sign in again.',
        );
      }
      if (response.statusCode == 403) {
        throw const PermissionFailure(
          'Your account cannot perform this action.',
        );
      }
      if (response.statusCode == 404) throw const NotFoundFailure();
      if (response.statusCode == 409) {
        throw const ConflictFailure(
          'This request conflicts with an existing action. Check Track before trying again.',
        );
      }
      if (response.statusCode == 422 || response.statusCode == 400) {
        throw const ValidationFailure(
          'The server rejected the submitted details. Check the fields.',
        );
      }
      if (response.statusCode == 429) {
        throw const RateLimitFailure(
          'Too many requests. Please wait a minute.',
        );
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw const ServerFailure(
          'The service is unavailable. Your unsent draft remains in this tab.',
        );
      }
      return response.body.isEmpty ? null : jsonDecode(response.body);
    } on Failure {
      rethrow;
    } on TimeoutException {
      throw const NetworkFailure(
        'The request timed out. Check Track, then retry the same report.',
      );
    } on http.ClientException {
      throw const NetworkFailure(
        'Cannot reach the API. Keep this tab open and retry.',
      );
    } on FormatException {
      throw const ServerFailure('The server returned an invalid response.');
    } catch (_) {
      throw const ServerFailure(
        'The request could not be completed. Keep this tab open and retry.',
      );
    }
  }

  void close() => _client.close();
}

Map<String, dynamic> jsonObject(Object? value) {
  if (value is Map<String, dynamic>) return value;
  throw const ServerFailure('The server returned an invalid object.');
}

String newRequestKey() =>
    base64UrlEncode(List<int>.generate(24, (_) => Random.secure().nextInt(256)))
        .replaceAll('=', '');
