import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/features/notifications/data/notification_repository.dart';

void main() {
  late List<http.Request> requests;

  NotificationRepository repository(http.Response Function() reply) {
    requests = <http.Request>[];
    final api = ApiClient(
      baseUrl: 'https://api.example.test/api/v1',
      token: () async => 'token',
      client: MockClient((request) async {
        requests.add(request);
        return reply();
      }),
    );
    addTearDown(api.close);
    return NotificationRepository(api);
  }

  http.Response json(Object? body) => http.Response(
    jsonEncode(body),
    200,
    headers: <String, String>{'content-type': 'application/json'},
  );

  test('loads the inbox with its unread count', () async {
    final repo = repository(
      () => json(<String, Object?>{
        'items': <Object?>[
          <String, Object?>{
            'id': 'n1',
            'title': 'Repair work is ready for review',
            'body': 'Please review the repair.',
            'created_at': '2026-10-29T10:00:00Z',
            'read_at': null,
          },
          <String, Object?>{
            'id': 'n2',
            'title': 'Your report was reviewed',
            'body': 'Report JM-1 is now verified.',
            'created_at': '2026-10-28T10:00:00Z',
            'read_at': '2026-10-28T11:00:00Z',
          },
        ],
        'unread_count': 1,
      }),
    );
    final page = await repo.load();

    expect(requests.single.url.path, '/api/v1/notifications');
    expect(page.unreadCount, 1);
    expect(page.items.map((item) => item.id), <String>['n1', 'n2']);
    expect(page.items.first.isRead, isFalse);
    expect(page.items.last.isRead, isTrue);
  });

  test('an incomplete item is a failure, not a blank row', () async {
    final repo = repository(
      () => json(<String, Object?>{
        'items': <Object?>[
          <String, Object?>{'id': 'n1', 'title': 'No body or date'},
        ],
        'unread_count': 1,
      }),
    );
    await expectLater(repo.load(), throwsFormatException);
  });

  test('marks one notification read', () async {
    final repo = repository(
      () => json(<String, Object?>{
        'id': 'n1',
        'read_at': '2026-10-29T10:05:00Z',
      }),
    );
    await repo.markRead('n1');
    expect(requests.single.method, 'POST');
    expect(requests.single.url.path, '/api/v1/notifications/n1/read');
  });
}
