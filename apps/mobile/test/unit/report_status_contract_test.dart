import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/features/demands/data/http_demands_repository.dart';
import 'package:janmaang/features/report/data/report_dto.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

import 'live_report_repository_test.dart' show reportJson;

void main() {
  group('agreed status values (docs/api/day1-frontend-contract.md)', () {
    const expected = <String, DemandStatus>{
      'reported': DemandStatus.reported,
      'verified': DemandStatus.verified,
      'rejected': DemandStatus.rejected,
      'prioritised': DemandStatus.prioritised,
      'funded': DemandStatus.funded,
      'in_progress': DemandStatus.inProgress,
      'awaiting_verification': DemandStatus.inProgress,
      'citizen_verified': DemandStatus.citizenVerified,
    };

    for (final entry in expected.entries) {
      test('${entry.key} maps to ${entry.value.name}', () {
        final demand = demandFromJson(reportJson()..['status'] = entry.key);
        expect(demand.status, entry.value);
        expect(
          demand.awaitingVerification,
          entry.key == 'awaiting_verification',
        );
      });
    }

    test('dropped backend values are protocol failures', () {
      for (final status in <String>['clustered', 'ranked', 'resolved']) {
        expect(
          () => demandFromJson(reportJson()..['status'] = status),
          throwsA(isA<ServerFailure>()),
          reason: status,
        );
      }
    });

    test('copyWith updates the verification flag and clears a reason', () {
      final awaiting = demandFromJson(
        reportJson()..['status'] = 'awaiting_verification',
      );
      final confirmed = awaiting.copyWith(
        status: DemandStatus.citizenVerified,
        awaitingVerification: false,
      );
      expect(confirmed.awaitingVerification, isFalse);
      expect(awaiting.copyWith().awaitingVerification, isTrue);

      final rejected = demandFromJson(
        reportJson()
          ..['status'] = 'rejected'
          ..['rejection_reason'] = 'Duplicate',
      );
      expect(rejected.copyWith().rejectionReason, 'Duplicate');
      expect(
        rejected.copyWith(clearRejectionReason: true).rejectionReason,
        isNull,
      );
    });

    test('a rejected report carries the Panchayat reason', () {
      final demand = demandFromJson(
        reportJson()
          ..['status'] = 'rejected'
          ..['rejection_reason'] = 'Outside this district',
      );
      expect(demand.rejectionReason, 'Outside this district');
    });
  });

  /// One malformed record per field and type the mapping reads.
  final malformed = <String, Map<String, Object?> Function()>{
    'category number': () => reportJson()..['category'] = 7,
    'title number': () => reportJson()..['title'] = 42,
    'code number': () => reportJson()..['code'] = 1001,
    'description list': () => reportJson()..['description'] = <Object?>[],
    'ward map': () => reportJson()..['ward'] = <String, Object?>{},
    'latitude string': () => reportJson()..['latitude'] = '16.7',
    'rank fraction': () => reportJson()..['rank'] = 1.5,
    'supporters string': () => reportJson()..['supporter_count'] = 'many',
    'created_at number': () => reportJson()..['created_at'] = 20261001,
    'updated_at garbage': () => reportJson()..['updated_at'] = 'yesterday',
    'status_changed_at number': () =>
        reportJson()..['status_changed_at'] = true,
    'rejection_reason number': () => reportJson()..['rejection_reason'] = 3,
    'media item string': () => reportJson()..['media'] = <Object?>['x.jpg'],
    'thumbnail http': () => reportJson()
      ..['media'] = <Object?>[
        <String, Object?>{
          'id': 'm',
          'url': 'https://res.cloudinary.com/d/a.jpg',
          'thumbnail_url': 'http://insecure.example/a.jpg',
        },
      ],
    'score label number': () => reportJson()
      ..['score_breakdown'] = <Object?>[
        <String, Object?>{
          'label': 5,
          'score': 50,
          'weight': 0.2,
          'is_demo': true,
        },
      ],
    'score is_demo string': () => reportJson()
      ..['score_breakdown'] = <Object?>[
        <String, Object?>{
          'label': 'Equity',
          'score': 50,
          'weight': 0.2,
          'is_demo': 'yes',
        },
      ],
  };

  group('a malformed field is a ServerFailure, never a TypeError', () {
    for (final entry in malformed.entries) {
      test(entry.key, () {
        expect(
          () => demandFromJson(entry.value()),
          throwsA(isA<ServerFailure>()),
        );
      });
    }
  });

  test(
    'my reports keeps readable records and counts unreadable ones',
    () async {
      final bad = <Object?>[
        reportJson()
          ..['id'] = 'report-2'
          ..['status'] = 'invented',
        'not even an object',
        for (final build in malformed.values) build()..['id'] = 'bad',
      ];
      final api = ApiClient(
        baseUrl: 'https://api.example.test',
        token: () async => 'token',
        client: MockClient(
          (request) async => http.Response(
            jsonEncode(<String, Object?>{
              'items': <Object?>[
                reportJson(),
                ...bad,
                reportJson()..['id'] = 'report-3',
              ],
            }),
            200,
          ),
        ),
      );
      final repository = HttpDemandsRepository(api);

      final reports = await repository.watchMyDemands('local-user').first;

      expect(reports.map((d) => d.id), <String>['report-1', 'report-3']);
      expect(repository.unreadableInLastLoad, bad.length);
      api.close();
    },
  );

  group('timeline dates are never invented', () {
    test('the current status is dated by status_changed_at', () {
      final demand = demandFromJson(
        reportJson()
          ..['created_at'] = '2026-10-01T08:00:00Z'
          ..['status'] = 'citizen_verified'
          ..['status_changed_at'] = '2026-10-24T09:30:00Z',
      );
      expect(demand.timeline.single.status, DemandStatus.citizenVerified);
      expect(demand.timeline.single.at, DateTime.utc(2026, 10, 24, 9, 30));
    });

    test('without status_changed_at the event is undated', () {
      final demand = demandFromJson(
        reportJson()
          ..['created_at'] = '2026-10-01T08:00:00Z'
          ..['updated_at'] = '2026-10-24T09:30:00Z'
          ..['status'] = 'citizen_verified',
      );
      // Neither the creation date nor updated_at stands in for it.
      expect(demand.timeline.single.at, isNull);
    });
  });
}
