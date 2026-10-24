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

  test('my reports keeps readable records and counts unreadable ones', () async {
    final api = ApiClient(
      baseUrl: 'https://api.example.test',
      token: () async => 'token',
      client: MockClient(
        (request) async => http.Response(
          jsonEncode(<String, Object?>{
            'items': <Object?>[
              reportJson(),
              reportJson()
                ..['id'] = 'report-2'
                ..['status'] = 'invented',
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
    expect(repository.unreadableInLastLoad, 1);
    api.close();
  });
}
