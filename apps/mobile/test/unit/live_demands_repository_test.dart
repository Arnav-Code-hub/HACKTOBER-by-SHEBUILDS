import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/features/demands/data/http_demands_repository.dart';

void main() {
  const clusterId = '59e8a73f-5c9b-4d73-9c8a-0c32e967e4ba';

  test(
    'joining posts authenticated support and validates its acknowledgement',
    () async {
      late http.Request captured;
      final api = ApiClient(
        baseUrl: 'https://api.example.test',
        token: () async => 'firebase-id-token',
        client: MockClient((request) async {
          captured = request;
          return http.Response(
            jsonEncode(<String, Object?>{
              'id': clusterId,
              'supporter_count': 4,
            }),
            200,
          );
        }),
      );
      addTearDown(api.close);
      final repository = HttpDemandsRepository(api);

      expect(await repository.joinCluster(clusterId), 4);

      expect(captured.method, 'POST');
      expect(captured.url.path, '/api/v1/clusters/$clusterId/support');
      expect(captured.headers['authorization'], 'Bearer firebase-id-token');
      expect(jsonDecode(captured.body), isEmpty);
    },
  );

  test('joining surfaces a server permission rejection', () async {
    final api = ApiClient(
      baseUrl: 'https://api.example.test',
      token: () async => 'firebase-id-token',
      client: MockClient((_) async => http.Response('{}', 403)),
    );
    addTearDown(api.close);

    await expectLater(
      HttpDemandsRepository(api).joinCluster(clusterId),
      throwsA(isA<PermissionFailure>()),
    );
  });

  test('malformed support acknowledgement is rejected', () async {
    final api = ApiClient(
      baseUrl: 'https://api.example.test',
      token: () async => 'firebase-id-token',
      client: MockClient(
        (_) async =>
            http.Response('{"id":"$clusterId","supporter_count":"four"}', 200),
      ),
    );
    addTearDown(api.close);

    await expectLater(
      HttpDemandsRepository(api).joinCluster(clusterId),
      throwsA(isA<ServerFailure>()),
    );
  });
}
