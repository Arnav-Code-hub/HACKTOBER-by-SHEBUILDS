import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
import '../../../core/services/media_service.dart';
import '../../../shared/models/demand_enums.dart';
import '../../demands/domain/demand.dart';
import '../domain/report_draft.dart';
import '../domain/report_repository.dart';
import 'report_dto.dart';

class HttpReportRepository implements ReportRepository {
  HttpReportRepository(this._api, {http.Client? uploadClient})
    : _uploads = uploadClient ?? http.Client();
  final ApiClient _api;
  final http.Client _uploads;
  final Map<String, Map<XFile, UploadedMedia>> _uploadedByUser =
      <String, Map<XFile, UploadedMedia>>{};
  final Map<String, Map<XFile, Map<String, Object?>>> _pendingByUser =
      <String, Map<XFile, Map<String, Object?>>>{};
  final Expando<String> _keys = Expando<String>();

  @override
  Future<ReportAnalysis> analyze({
    required String transcript,
    List<String> photoPaths = const <String>[],
  }) async {
    const unavailable =
        'Suggestions are unavailable right now. Enter the details yourself.';
    try {
      // Photos stay in the evidence flow; suggestions send only the transcript.
      final data = jsonObject(
        await _api.post('reports/suggest', <String, Object?>{
          'transcript': transcript.trim(),
        }),
      );
      String text(String key, int max, {bool emptyAllowed = false}) {
        final value = data[key];
        if (value is! String ||
            value.length > max ||
            (!emptyAllowed && value.trim().isEmpty)) {
          throw const ServerFailure(unavailable);
        }
        return value.trim();
      }

      final categoryName = text('category', 30);
      final severityName = text('severity', 30);
      final category = DemandCategory.values.where(
        (v) => v.name == categoryName,
      );
      final severity = Severity.values.where((v) => v.name == severityName);
      final language = text('detected_language', 2);
      if (category.isEmpty ||
          severity.isEmpty ||
          !const <String>{
            'en',
            'hi',
            'mr',
            'bn',
            'ta',
            'te',
            'kn',
            'gu',
          }.contains(language) ||
          !data.containsKey('mentioned_location') ||
          (data['mentioned_location'] != null &&
              data['mentioned_location'] is! String)) {
        throw const ServerFailure(unavailable);
      }
      final location = data['mentioned_location'] == null
          ? ''
          : text('mentioned_location', 200, emptyAllowed: true);
      return ReportAnalysis(
        category: category.first,
        severity: severity.first,
        title: text('title', 120),
        summary: text('summary', 500),
        mentionedLocation: location,
        detectedLanguage: language,
      );
    } on RateLimitFailure {
      throw const RateLimitFailure(
        'Too many suggestion requests; wait a minute.',
      );
    } on ServerFailure {
      throw const ServerFailure(unavailable);
    }
  }

  @override
  Future<Demand> submit(ReportDraft draft, String uid) async {
    final details = draft.effectiveAnalysis;
    if (!draft.canSubmit || details == null) {
      throw const ValidationFailure(
        'Add details and a valid location before submitting.',
      );
    }
    final media = await uploadPhotos(draft.photos, uid);
    final key = draft.submissionKey ?? (_keys[draft] ??= newRequestKey());
    return demandFromJson(
      await _api.post('reports', <String, Object?>{
        'transcript': draft.transcript.trim(),
        'title': details.title,
        'category': details.category.name,
        'severity': details.severity.name,
        'summary': details.summary.isEmpty
            ? draft.transcript.trim()
            : details.summary,
        'latitude': draft.latitude,
        'longitude': draft.longitude,
        'location_label': draft.locationLabel,
        'channel': draft.channel.name,
        'media_ids': media.map((asset) => asset.id).toList(),
      }, idempotencyKey: key),
    );
  }

  @override
  Future<List<UploadedMedia>> uploadPhotos(
    List<XFile> photos,
    String uid,
  ) async {
    PhotoRules.checkCount(0, photos.length);
    final uploaded = _uploadedByUser.putIfAbsent(
      uid,
      () => <XFile, UploadedMedia>{},
    );
    final pending = _pendingByUser.putIfAbsent(
      uid,
      () => <XFile, Map<String, Object?>>{},
    );
    final result = <UploadedMedia>[];
    for (final photo in photos) {
      final cached = uploaded[photo];
      if (cached != null) {
        result.add(cached);
        continue;
      }
      final type = await PhotoRules.validate(photo);
      try {
        var completion = pending[photo];
        if (completion == null) {
          final signed = jsonObject(
            await _api.post('media/signature', <String, Object?>{
              'filename': photo.name,
              'content_type': type,
              'bytes': await photo.length(),
              'kind': 'report',
            }),
          );
          final uri = Uri.tryParse(signed['upload_url']?.toString() ?? '');
          if (uri == null ||
              uri.scheme != 'https' ||
              uri.host != 'api.cloudinary.com' ||
              uri.userInfo.isNotEmpty ||
              uri.hasQuery ||
              uri.hasFragment ||
              !RegExp(r'^/v1_1/[^/]+/(image|auto)/upload$')
                  .hasMatch(uri.path)) {
            throw const ServerFailure(
              'The API returned an untrusted upload destination.',
            );
          }
          final parameters = jsonObject(signed['parameters']);
          if (signed['upload_id'] is! String ||
              parameters.values.any((value) => value is! String) ||
              parameters.containsKey('file')) {
            throw const ServerFailure(
              'The API returned invalid upload parameters.',
            );
          }
          // Separate unauthenticated client: Firebase tokens never go to Cloudinary.
          final request = http.MultipartRequest('POST', uri)
            ..fields.addAll(parameters.cast<String, String>())
            ..files.add(
              http.MultipartFile.fromBytes(
                'file',
                await photo.readAsBytes(),
                filename: photo.name,
                contentType: MediaType.parse(type),
              ),
            );
          final response = await http.Response.fromStream(
            await _uploads.send(request).timeout(const Duration(seconds: 60)),
          ).timeout(const Duration(seconds: 60));
          if (response.statusCode < 200 || response.statusCode >= 300) {
            throw const NetworkFailure(
              'Photo upload failed. Keep this tab open and retry.',
            );
          }
          final upload = jsonObject(jsonDecode(response.body));
          if (upload['public_id'] is! String ||
              upload['version'] is! num ||
              upload['signature'] is! String) {
            throw const ServerFailure(
              'Cloudinary returned incomplete upload metadata.',
            );
          }
          completion = <String, Object?>{
            'upload_id': signed['upload_id'],
            'public_id': upload['public_id'],
            'version': upload['version'],
            'signature': upload['signature'],
          };
          pending[photo] = completion;
        }
        // Retrying a failed completion call reuses the same upload intent.
        final asset = jsonObject(await _api.post('media/complete', completion));
        if (asset['id'] is! String ||
            asset['url'] is! String ||
            Uri.tryParse(asset['url'] as String)?.scheme != 'https') {
          throw const ServerFailure(
            'The API returned invalid completed media.',
          );
        }
        final media = UploadedMedia(
          id: asset['id'] as String,
          url: asset['url'] as String,
          thumbnailUrl: asset['thumbnail_url'] as String?,
        );
        uploaded[photo] = media;
        pending.remove(photo);
        result.add(media);
      } on Failure {
        rethrow;
      } catch (_) {
        throw const NetworkFailure(
          'Photo upload could not finish. Keep this tab open and retry.',
        );
      }
    }
    return result;
  }

  void close() => _uploads.close();
}
