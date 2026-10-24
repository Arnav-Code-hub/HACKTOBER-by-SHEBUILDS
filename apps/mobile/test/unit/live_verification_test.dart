import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/features/report/data/report_dto.dart';
import 'package:janmaang/features/verification/data/http_verification_repository.dart';
import 'package:janmaang/features/verification/domain/verification.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

import 'live_report_repository_test.dart' show reportJson;

final now = DateTime.utc(2026, 10, 25, 10);

Map<String, Object?> verificationJson() => <String, Object?>{
  'work_order_id': 'w1',
  'report_code': 'YDG-WTR-0001',
  'title': 'Handpump not working',
  'category': 'water',
  'status': 'awaiting_verification',
  'round': 2,
  'can_verify': true,
  'blocked_reason': null,
  'before': <String, Object?>{
    'url': 'https://res.cloudinary.com/d/before.jpg',
    'uploaded_at': '2026-10-11T10:00:00Z',
  },
  'after': <String, Object?>{
    'url': 'https://res.cloudinary.com/d/after.jpg',
    'uploaded_at': '2026-10-24T10:00:00Z',
  },
  'card_url': 'https://res.cloudinary.com/d/card.jpg',
};

ApiClient apiReturning(
  http.Response Function(http.Request request) handler,
) => ApiClient(
  baseUrl: 'https://api.example.test',
  token: () async => 'token',
  client: MockClient((request) async => handler(request)),
);

void main() {
  group('verification view mapping', () {
    test('maps evidence, round and eligibility', () {
      final request = verificationRequestFromJson(
        'r1',
        verificationJson(),
        now: now,
      );
      expect(request.workOrderId, 'w1');
      expect(request.round, 2);
      expect(request.canVerify, isTrue);
      expect(request.question, 'Is the water source working now?');
      expect(request.afterPhotoUrl, endsWith('after.jpg'));
      expect(request.evidenceCardUrl, endsWith('card.jpg'));
      expect(request.reportedAgo, '2w ago');
      expect(request.completedAgo, '1d ago');
    });

    test('allows missing completion evidence and card', () {
      final request = verificationRequestFromJson('r1', <String, Object?>{
        ...verificationJson(),
        'after': null,
        'card_url': null,
      }, now: now);
      expect(request.afterPhotoUrl, isNull);
      expect(request.evidenceCardUrl, isNull);
    });

    test('explains why a citizen cannot verify', () {
      final request = verificationRequestFromJson('r1', <String, Object?>{
        ...verificationJson(),
        'can_verify': false,
        'blocked_reason': 'Only the person who reported this can verify it.',
      });
      expect(request.canVerify, isFalse);
      expect(request.blockedReason, contains('Only the person'));
    });

    test('refuses non-HTTPS evidence rather than showing it', () {
      expect(
        () => verificationRequestFromJson('r1', <String, Object?>{
          ...verificationJson(),
          'after': <String, Object?>{
            'url': 'http://example.test/after.jpg',
            'uploaded_at': '2026-10-24T10:00:00Z',
          },
        }),
        throwsA(isA<ServerFailure>()),
      );
    });
  });

  group('HttpVerificationRepository', () {
    test('posts the verdict and comment once per round', () async {
      http.Request? sent;
      final api = apiReturning((request) {
        sent = request;
        return http.Response('{"id":"w1","status":"in_progress"}', 200);
      });
      await HttpVerificationRepository(api).submit(
        const VerificationSubmission(
          demandId: 'r1',
          kind: VerificationKind.citizen,
          isFixed: false,
          note: '  Still dry in the evening.  ',
          workOrderId: 'w1',
          round: 2,
        ),
        'local-user',
      );
      expect(sent!.url.path, '/api/v1/work-orders/w1/verify');
      expect(jsonDecode(sent!.body), <String, Object?>{
        'verdict': false,
        'comment': 'Still dry in the evening.',
      });
      expect(sent!.headers['Idempotency-Key'], 'verify-w1-2');
      api.close();
    });

    test('will not post a verdict without its work order', () async {
      final api = apiReturning((_) => fail('must not call the API'));
      await expectLater(
        HttpVerificationRepository(api).submit(
          const VerificationSubmission(
            demandId: 'r1',
            kind: VerificationKind.citizen,
            isFixed: true,
          ),
          'local-user',
        ),
        throwsA(isA<ValidationFailure>()),
      );
      api.close();
    });

    test('explains a report that is not open for verification', () async {
      final api = apiReturning((_) => http.Response('{}', 404));
      await expectLater(
        HttpVerificationRepository(api).getRequest('r1'),
        throwsA(
          isA<NotFoundFailure>().having(
            (f) => f.message,
            'message',
            contains('repair work has been submitted'),
          ),
        ),
      );
      api.close();
    });
  });

  group('report detail mapping', () {
    test('keeps thumbnails aligned with full-size photos', () {
      final demand = demandFromJson(
        reportJson()
          ..['media'] = <Object?>[
            <String, Object?>{
              'id': 'm1',
              'url': 'https://res.cloudinary.com/d/full.jpg',
              'thumbnail_url': 'https://res.cloudinary.com/d/thumb.jpg',
            },
            <String, Object?>{
              'id': 'm2',
              'url': 'https://res.cloudinary.com/d/only.jpg',
            },
          ],
      );
      expect(demand.photoThumbnailUrls, <String>[
        'https://res.cloudinary.com/d/thumb.jpg',
        'https://res.cloudinary.com/d/only.jpg',
      ]);
    });

    test('labels demonstration ranking inputs', () {
      final demand = demandFromJson(
        reportJson()
          ..['status'] = 'prioritised'
          ..['score_breakdown'] = <Object?>[
            <String, Object?>{
              'factor': 'support',
              'label': 'Community support',
              'score': 72.4,
              'weight': 0.3,
              'is_demo': false,
            },
            <String, Object?>{
              'factor': 'equity',
              'label': 'Equity',
              'score': 50,
              'weight': 0.2,
              'is_demo': true,
            },
          ],
      );
      final [support, equity] = demand.scoreBreakdown;
      expect(support.score, 72);
      expect(support.isDemo, isFalse);
      expect(equity.isDemo, isTrue);
      expect(equity.explanation, contains('Demo value'));
    });

    test('rejects a score outside 0–100', () {
      expect(
        () => demandFromJson(
          reportJson()
            ..['score_breakdown'] = <Object?>[
              <String, Object?>{
                'factor': 'x',
                'label': 'X',
                'score': 140,
                'weight': 0.3,
                'is_demo': false,
              },
            ],
        ),
        throwsA(isA<ServerFailure>()),
      );
    });
  });
}
