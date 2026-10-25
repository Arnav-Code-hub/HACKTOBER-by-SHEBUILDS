import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/features/report/data/http_report_repository.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

Map<String, Object?> suggestion([Map<String, Object?> overrides = const {}]) =>
    <String, Object?>{
      'category': 'water',
      'severity': 'high',
      'title': 'Handpump not working',
      'summary': 'The ward 4 handpump gives no water.',
      'mentioned_location': 'Ward 4',
      'detected_language': 'hi',
      ...overrides,
    };

void main() {
  late List<http.Request> requests;

  HttpReportRepository repository(http.Response Function() reply) {
    requests = <http.Request>[];
    final api = ApiClient(
      baseUrl: 'https://api.example.test/api/v1',
      token: () async => 'token',
      client: MockClient((request) async {
        requests.add(request);
        return reply();
      }),
    );
    final repo = HttpReportRepository(api);
    addTearDown(api.close);
    addTearDown(repo.close);
    return repo;
  }

  http.Response json(Object? body, [int status = 200]) => http.Response(
    jsonEncode(body),
    status,
    headers: <String, String>{'content-type': 'application/json'},
  );

  test('sends only the trimmed transcript and maps the suggestion', () async {
    final repo = repository(() => json(suggestion()));
    final analysis = await repo.analyze(
      transcript: '  Handpump broken  ',
      photoPaths: const <String>['photo.jpg'],
    );
    expect(requests.single.method, 'POST');
    expect(requests.single.url.path, '/api/v1/reports/suggest');
    expect(jsonDecode(requests.single.body), <String, Object?>{
      'transcript': 'Handpump broken',
    });
    expect(analysis.category, DemandCategory.water);
    expect(analysis.severity, Severity.high);
    expect(analysis.title, 'Handpump not working');
    expect(analysis.summary, 'The ward 4 handpump gives no water.');
    expect(analysis.mentionedLocation, 'Ward 4');
    expect(analysis.detectedLanguage, 'hi');
  });

  test('a null location becomes empty', () async {
    final repo = repository(
      () => json(suggestion(<String, Object?>{'mentioned_location': null})),
    );
    final analysis = await repo.analyze(transcript: 'Handpump broken');
    expect(analysis.mentionedLocation, '');
  });

  for (final bad in <Map<String, Object?>>[
    <String, Object?>{'category': 'parks'},
    <String, Object?>{'severity': 'urgent'},
    <String, Object?>{'detected_language': 'fr'},
    <String, Object?>{'title': ''},
    <String, Object?>{'title': 'x' * 121},
    <String, Object?>{'summary': 7},
    <String, Object?>{'mentioned_location': 4},
  ]) {
    test('an invalid field ($bad) is a failure, not a crash', () async {
      final repo = repository(() => json(suggestion(bad)));
      await expectLater(
        repo.analyze(transcript: 'Handpump broken'),
        throwsA(
          isA<ServerFailure>().having(
            (f) => f.message,
            'message',
            contains('Enter the details yourself'),
          ),
        ),
      );
    });
  }

  test('a missing location key is a failure', () async {
    final body = suggestion()..remove('mentioned_location');
    final repo = repository(() => json(body));
    await expectLater(
      repo.analyze(transcript: 'Handpump broken'),
      throwsA(isA<ServerFailure>()),
    );
  });

  test('503 asks the citizen to enter details themselves', () async {
    final repo = repository(
      () =>
          json(<String, Object?>{'detail': 'Suggestions are unavailable'}, 503),
    );
    await expectLater(
      repo.analyze(transcript: 'Handpump broken'),
      throwsA(
        isA<ServerFailure>().having(
          (f) => f.message,
          'message',
          'Suggestions are unavailable right now. Enter the details yourself.',
        ),
      ),
    );
  });

  test('429 has its own message', () async {
    final repo = repository(
      () => json(<String, Object?>{'detail': 'Too many'}, 429),
    );
    await expectLater(
      repo.analyze(transcript: 'Handpump broken'),
      throwsA(
        isA<RateLimitFailure>().having(
          (f) => f.message,
          'message',
          'Too many suggestion requests; wait a minute.',
        ),
      ),
    );
  });
}
