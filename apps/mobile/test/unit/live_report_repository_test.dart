import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image_picker/image_picker.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/core/services/media_service.dart';
import 'package:janmaang/features/report/data/http_report_repository.dart';
import 'package:janmaang/features/report/data/report_dto.dart';
import 'package:janmaang/features/report/domain/report_draft.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

Map<String, Object?> reportJson() => <String, Object?>{
  'id': 'report-1',
  'code': 'R-1',
  'title': 'Broken handpump',
  'reporter_id': 'local-user',
  'category': 'water',
  'severity': 'medium',
  'status': 'reported',
  'created_at': '2026-10-21T08:00:00Z',
  'description': 'Please repair',
  'ward': 'Ward 4',
  'district': 'Test district',
  'transcript': 'Handpump broken',
  'latitude': 16.7,
  'longitude': 77.1,
  'channel': 'text',
  'media': <Object?>[
    <String, Object?>{
      'id': 'asset-database-id',
      'url': 'https://res.cloudinary.com/test/image/upload/photo.jpg',
    },
  ],
};

ReportDraft validDraft({List<XFile> photos = const <XFile>[]}) => ReportDraft(
  transcript: 'Handpump broken',
  manualTitle: 'Broken handpump',
  manualCategory: DemandCategory.water,
  latitude: 16.7,
  longitude: 77.1,
  channel: ReportChannel.text,
  photos: photos,
);

void main() {
  final png = Uint8List.fromList(<int>[
    137,
    80,
    78,
    71,
    13,
    10,
    26,
    10,
    0,
    0,
    0,
    0,
  ]);

  test('manual report can submit when optional AI fails', () async {
    final api = ApiClient(
      baseUrl: 'https://api.example.test',
      token: () async => 'token',
      client: MockClient((_) async => http.Response('{}', 500)),
    );
    final repo = HttpReportRepository(api);
    addTearDown(api.close);
    addTearDown(repo.close);
    await expectLater(
      repo.analyze(transcript: 'Handpump broken'),
      throwsA(isA<ServerFailure>()),
    );
    expect(validDraft().analysis, isNull);
    expect(validDraft().canSubmit, isTrue);
    expect(validDraft().effectiveAnalysis!.severity, Severity.medium);
  });

  test(
    'incomplete manual details and out-of-range coordinates cannot submit',
    () {
      expect(
        const ReportDraft(
          transcript: 'problem',
          latitude: 1,
          longitude: 2,
        ).canSubmit,
        isFalse,
      );
      expect(validDraft().copyWith(latitude: 91).canSubmit, isFalse);
      expect(validDraft().copyWith(longitude: double.nan).canSubmit, isFalse);
    },
  );

  test('manual corrections override individual AI fields', () {
    const draft = ReportDraft(
      transcript: 'actual details',
      manualTitle: 'Corrected title',
      analysis: ReportAnalysis(
        category: DemandCategory.water,
        severity: Severity.high,
        title: 'AI title',
      ),
    );
    expect(draft.effectiveAnalysis!.title, 'Corrected title');
    expect(draft.effectiveAnalysis!.severity, Severity.high);
    expect(draft.effectiveAnalysis!.category, DemandCategory.water);
  });

  test('photo count is cumulative across picker invocations', () {
    PhotoRules.checkCount(0, 2);
    PhotoRules.checkCount(2, 1);
    expect(
      () => PhotoRules.checkCount(2, 2),
      throwsA(isA<ValidationFailure>()),
    );
    expect(
      () => PhotoRules.checkCount(3, 1),
      throwsA(isA<ValidationFailure>()),
    );
  });

  test(
    'image validation uses bytes rather than a forged file extension',
    () async {
      final photo = XFile.fromData(
        png,
        name: 'evidence.png',
        mimeType: 'image/png',
      );
      expect(await PhotoRules.validate(photo), 'image/png');
      await expectLater(
        PhotoRules.validate(
          XFile.fromData(
            Uint8List.fromList(<int>[1, 2, 3]),
            name: 'fake.jpg',
            mimeType: 'image/jpeg',
          ),
        ),
        throwsA(isA<ValidationFailure>()),
      );
      await expectLater(
        PhotoRules.validate(
          XFile.fromData(
            Uint8List(PhotoRules.maxBytes + 1),
            name: 'oversize.png',
          ),
        ),
        throwsA(isA<ValidationFailure>()),
      );
    },
  );

  test('read DTO maps display URLs separately from asset IDs and aliases', () {
    final demand = demandFromJson(reportJson());
    expect(demand.photoUrls.single, startsWith('https://res.cloudinary.com/'));
    expect(demand.photoUrls, isNot(contains('asset-database-id')));
    expect(demand.description, 'Please repair');
    expect(demand.ward, 'Ward 4');
    expect(demand.district, 'Test district');
    expect(demand.timeline.length, 1);
  });

  test('unknown lifecycle status is an explicit protocol failure', () {
    expect(
      () => demandFromJson(reportJson()..['status'] = 'invented'),
      throwsA(isA<ServerFailure>()),
    );
  });

  test(
    'business API appends version once and attaches only an ID token',
    () async {
      for (final base in <String>[
        'https://api.example.test',
        'https://api.example.test/api/v1',
      ]) {
        final api = ApiClient(
          baseUrl: base,
          token: () async => 'firebase-id-token',
          client: MockClient((request) async {
            expect(
              request.url.toString(),
              'https://api.example.test/api/v1/users/me',
            );
            expect(
              request.headers['Authorization'],
              'Bearer firebase-id-token',
            );
            return http.Response('{}', 200);
          }),
        );
        await api.get('users/me');
        api.close();
      }
      expect(
        () => ApiClient(
          baseUrl: 'http://public.example.test',
          token: () async => 'token',
        ),
        throwsA(isA<ValidationFailure>()),
      );
    },
  );

  test('successful uploads reuse asset IDs and report retries reuse Idempotency-Key', () async {
    final keys = <String?>[];
    var uploads = 0;
    var signatures = 0;
    var creates = 0;
    final api = ApiClient(
      baseUrl: 'https://api.example.test',
      token: () async => 'id-token',
      client: MockClient((request) async {
        expect(request.headers['Authorization'], 'Bearer id-token');
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        if (request.url.path.endsWith('/media/signature')) {
          signatures++;
          expect(body['content_type'], 'image/png');
          return http.Response(
            jsonEncode(<String, Object?>{
              'upload_id': 'intent-1',
              'upload_url': 'https://api.cloudinary.com/v1_1/demo/image/upload',
              'parameters': <String, String>{
                'api_key': 'public-key',
                'timestamp': '1',
                'signature': 'signed',
                'public_id': 'fixed-id',
                'overwrite': 'false',
              },
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/media/complete')) {
          expect(body, <String, Object?>{
            'upload_id': 'intent-1',
            'public_id': 'fixed-id',
            'version': 123,
            'signature': 'cloud-result',
          });
          return http.Response(
            jsonEncode(<String, Object?>{
              'id': 'asset-database-id',
              'url':
                  'https://res.cloudinary.com/demo/image/upload/fixed-id.png',
            }),
            200,
          );
        }
        creates++;
        keys.add(request.headers['Idempotency-Key']);
        expect(body['media_ids'], <String>['asset-database-id']);
        expect(body.containsKey('photo_urls'), isFalse);
        expect(body.containsKey('reporter_id'), isFalse);
        return creates == 1
            ? http.Response('{}', 503)
            : http.Response(jsonEncode(reportJson()), 201);
      }),
    );
    final repo = HttpReportRepository(
      api,
      uploadClient: MockClient((request) async {
        uploads++;
        expect(request.url.host, 'api.cloudinary.com');
        expect(
          request.headers.keys.any(
            (header) => header.toLowerCase() == 'authorization',
          ),
          isFalse,
        );
        expect(
          utf8.decode(request.bodyBytes, allowMalformed: true),
          contains('fixed-id'),
        );
        return http.Response(
          jsonEncode(<String, Object?>{
            'public_id': 'fixed-id',
            'version': 123,
            'signature': 'cloud-result',
          }),
          200,
        );
      }),
    );
    addTearDown(api.close);
    addTearDown(repo.close);
    final draft = validDraft(
      photos: <XFile>[XFile.fromData(png, name: 'evidence.png')],
    );
    await expectLater(
      repo.submit(draft, 'local-user'),
      throwsA(isA<ServerFailure>()),
    );
    final saved = await repo.submit(draft, 'local-user');
    expect(saved.id, 'report-1');
    expect(keys[0], isNotEmpty);
    expect(keys[0], keys[1]);
    expect(uploads, 1);
    expect(signatures, 1);
  });

  test(
    'untrusted upload destinations never receive the photo or token',
    () async {
      var uploadAttempted = false;
      final api = ApiClient(
        baseUrl: 'https://api.example.test',
        token: () async => 'token',
        client: MockClient(
          (_) async => http.Response(
            jsonEncode(<String, Object?>{
              'upload_id': 'i',
              'upload_url': 'https://attacker.example/image/upload',
              'parameters': <String, String>{},
            }),
            200,
          ),
        ),
      );
      final repo = HttpReportRepository(
        api,
        uploadClient: MockClient((_) async {
          uploadAttempted = true;
          return http.Response('{}', 200);
        }),
      );
      addTearDown(api.close);
      addTearDown(repo.close);
      await expectLater(
        repo.uploadPhotos(<XFile>[XFile.fromData(png, name: 'x.png')], 'u'),
        throwsA(isA<ServerFailure>()),
      );
      expect(uploadAttempted, isFalse);
    },
  );

  test('completion retries reuse upload intent and media caches are scoped to user', () async {
    var owner = 'a';
    var uploads = 0;
    var signatures = 0;
    var completes = 0;
    final api = ApiClient(
      baseUrl: 'https://api.example.test',
      token: () async => 'token-$owner',
      client: MockClient((request) async {
        if (request.url.path.endsWith('/media/signature')) {
          signatures++;
          return http.Response(
            jsonEncode(<String, Object?>{
              'upload_id': 'intent-$owner',
              'upload_url': 'https://api.cloudinary.com/v1_1/demo/image/upload',
              'parameters': <String, String>{'public_id': 'photo-$owner'},
            }),
            200,
          );
        }
        completes++;
        if (completes == 1) return http.Response('{}', 503);
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['upload_id'], 'intent-$owner');
        return http.Response(
          jsonEncode(<String, Object?>{
            'id': 'media-$owner',
            'url':
                'https://res.cloudinary.com/demo/image/upload/photo-$owner.png',
          }),
          200,
        );
      }),
    );
    final repository = HttpReportRepository(
      api,
      uploadClient: MockClient((_) async {
        uploads++;
        return http.Response(
          jsonEncode(<String, Object?>{
            'public_id': 'photo-$owner',
            'version': 123,
            'signature': 'result-signature',
          }),
          200,
        );
      }),
    );
    addTearDown(api.close);
    addTearDown(repository.close);
    final photo = XFile.fromData(png, name: 'photo.png');
    await expectLater(
      repository.uploadPhotos(<XFile>[photo], owner),
      throwsA(isA<ServerFailure>()),
    );
    expect(
      (await repository.uploadPhotos(<XFile>[photo], owner)).single.id,
      'media-a',
    );
    expect(uploads, 1);
    expect(signatures, 1);
    owner = 'b';
    expect(
      (await repository.uploadPhotos(<XFile>[photo], owner)).single.id,
      'media-b',
    );
    expect(uploads, 2);
    expect(signatures, 2);
  });
}
