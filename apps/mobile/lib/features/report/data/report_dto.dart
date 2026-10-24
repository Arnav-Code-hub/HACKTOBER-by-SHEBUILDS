import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_fields.dart';
import '../../../shared/models/demand_enums.dart';
import '../../demands/domain/demand.dart';

/// Explicit mapping keeps snake_case API records and Cloudinary media IDs out
/// of the UI's display URL fields.
///
/// Every field is type-checked, required or optional, so any malformed record
/// fails with a [ServerFailure] — never a `TypeError`. A detail view shows
/// that failure; a list skips the record and counts it.
Demand demandFromJson(Object? value) {
  try {
    return _demandFromJson(jsonObject(value));
  } on Failure {
    rethrow;
  } on TypeError {
    // Backstop for any shape a reader below does not cover.
    throw const ServerFailure('The API returned a malformed report.');
  }
}

Demand _demandFromJson(Map<String, dynamic> data) {
  final id = data.requiredString('id');
  // The agreed lifecycle — see docs/api/day1-frontend-contract.md. `verified`
  // means validated by the Panchayat; citizen confirmation is
  // `citizen_verified`.
  final rawStatus = data.requiredString('status');
  final status = switch (rawStatus) {
    'reported' => DemandStatus.reported,
    'verified' => DemandStatus.verified,
    'rejected' => DemandStatus.rejected,
    'prioritised' || 'prioritized' => DemandStatus.prioritised,
    'funded' => DemandStatus.funded,
    'in_progress' || 'awaiting_verification' => DemandStatus.inProgress,
    'citizen_verified' => DemandStatus.citizenVerified,
    _ => throw const ServerFailure(
      'The API returned an unsupported report status.',
    ),
  };

  final media = data['media'];
  if (media is! List) {
    throw const ServerFailure('The report media field is missing.');
  }
  final urls = <String>[];
  final thumbnails = <String>[];
  for (final item in media) {
    final asset = jsonObject(item);
    asset.requiredString('id');
    final url = asset.requiredHttpsUrl('url');
    urls.add(url);
    thumbnails.add(asset.optionalHttpsUrl('thumbnail_url') ?? url);
  }

  final category = DemandCategory.values
      .where((c) => c.name == data.requiredString('category'))
      .firstOrNull;
  final severity = Severity.values
      .where((s) => s.name == data.requiredString('severity'))
      .firstOrNull;
  if (category == null || severity == null) {
    throw const ServerFailure(
      'The API returned an unsupported category or severity.',
    );
  }
  final channel = data.optionalString('channel');

  return Demand(
    id: id,
    code: data.optionalString('code') ?? id,
    title: data.requiredString('title'),
    reporterId: data.requiredString('reporter_id'),
    category: category,
    severity: severity,
    status: status,
    createdAt: data.requiredDate('created_at'),
    updatedAt: data.optionalDate('updated_at'),
    description:
        data.optionalString('description') ??
        data.optionalString('summary') ??
        '',
    transcript: data.optionalString('transcript') ?? '',
    ward:
        data.optionalString('ward') ??
        data.optionalString('location_label') ??
        '',
    district:
        data.optionalString('district') ??
        data.optionalString('district_name') ??
        '',
    latitude: data.optionalNum('latitude')?.toDouble(),
    longitude: data.optionalNum('longitude')?.toDouble(),
    photoUrls: urls,
    photoThumbnailUrls: thumbnails,
    scoreBreakdown: _scoreBreakdown(data['score_breakdown']),
    clusterId: data.optionalString('cluster_id'),
    supporterCount: data.optionalInt('supporter_count') ?? 0,
    rank: data.optionalInt('rank'),
    totalRanked: data.optionalInt('total_ranked'),
    priorityScore: data.optionalNum('priority_score')?.toDouble() ?? 0,
    channel: ReportChannel.values.firstWhere(
      (c) => c.name == channel,
      orElse: () => ReportChannel.text,
    ),
    // Only the current status is known. Its date is `status_changed_at`,
    // which the API defines as when this status took effect; without it the
    // event is undated rather than given the creation date or `updated_at`.
    timeline: <TimelineEvent>[
      TimelineEvent(
        status: status,
        state: TimelineState.active,
        at: data.optionalDate('status_changed_at'),
      ),
    ],
    awaitingVerification: rawStatus == 'awaiting_verification',
    rejectionReason: data.optionalString('rejection_reason'),
  );
}

/// The five ranking factors, if the report is ranked. A seeded or default
/// input is labelled so it is never read as an official measurement.
List<PriorityFactor> _scoreBreakdown(Object? value) {
  if (value == null) return const <PriorityFactor>[];
  if (value is! List) {
    throw const ServerFailure('The API returned an invalid score breakdown.');
  }
  return value.map(_priorityFactor).toList();
}

PriorityFactor _priorityFactor(Object? item) {
  final factor = jsonObject(item);
  final label = factor.requiredString('label');
  final score = factor.optionalNum('score');
  final weight = factor.optionalNum('weight');
  final isDemo = factor.requiredBool('is_demo');
  if (score == null ||
      score < 0 ||
      score > 100 ||
      weight == null ||
      weight < 0 ||
      weight > 1) {
    throw const ServerFailure('The API returned an invalid score breakdown.');
  }
  final share = '${(weight * 100).round()}% of the score';
  return PriorityFactor(
    label: label,
    score: score.round(),
    isDemo: isDemo,
    explanation: isDemo
        ? '$share · Demo value: a seeded or neutral default, not an '
              'official measurement.'
        : share,
  );
}
