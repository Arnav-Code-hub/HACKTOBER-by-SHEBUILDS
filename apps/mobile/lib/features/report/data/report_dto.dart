import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
import '../../../shared/models/demand_enums.dart';
import '../../demands/domain/demand.dart';

/// Explicit mapping keeps snake_case API records and Cloudinary media IDs out
/// of the UI's display URL fields. Unknown lifecycle values fail visibly.
Demand demandFromJson(Object? value) {
  final data = jsonObject(value);
  final id = data['id'];
  final createdAt = DateTime.tryParse(data['created_at']?.toString() ?? '');
  if (id is! String ||
      createdAt == null ||
      data['title'] is! String ||
      data['reporter_id'] is! String) {
    throw const ServerFailure('The API returned an incomplete report.');
  }
  // The agreed lifecycle — see docs/api/day1-frontend-contract.md. `verified`
  // means validated by the Panchayat; citizen confirmation is
  // `citizen_verified`.
  final rawStatus = data['status'];
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
    final url = asset['url'];
    final thumbnail = asset['thumbnail_url'];
    if (asset['id'] is! String ||
        url is! String ||
        Uri.tryParse(url)?.scheme != 'https' ||
        (thumbnail != null &&
            (thumbnail is! String ||
                Uri.tryParse(thumbnail)?.scheme != 'https'))) {
      throw const ServerFailure('The API returned invalid media metadata.');
    }
    urls.add(url);
    thumbnails.add(thumbnail as String? ?? url);
  }
  final category = data['category'] as String?;
  final severity = data['severity'] as String?;
  if (!DemandCategory.values.any((c) => c.name == category) ||
      !Severity.values.any((s) => s.name == severity)) {
    throw const ServerFailure(
      'The API returned an unsupported category or severity.',
    );
  }
  return Demand(
    id: id,
    code: data['code'] as String? ?? id,
    title: data['title'] as String,
    reporterId: data['reporter_id'] as String,
    category: DemandCategory.fromName(category),
    severity: Severity.fromName(severity),
    status: status,
    createdAt: createdAt,
    updatedAt: DateTime.tryParse(data['updated_at']?.toString() ?? ''),
    description:
        data['description'] as String? ?? data['summary'] as String? ?? '',
    transcript: data['transcript'] as String? ?? '',
    ward: data['ward'] as String? ?? data['location_label'] as String? ?? '',
    district:
        data['district'] as String? ?? data['district_name'] as String? ?? '',
    latitude: (data['latitude'] as num?)?.toDouble(),
    longitude: (data['longitude'] as num?)?.toDouble(),
    photoUrls: urls,
    photoThumbnailUrls: thumbnails,
    scoreBreakdown: _scoreBreakdown(data['score_breakdown']),
    clusterId: data['cluster_id'] as String?,
    supporterCount: (data['supporter_count'] as num?)?.toInt() ?? 0,
    rank: (data['rank'] as num?)?.toInt(),
    totalRanked: (data['total_ranked'] as num?)?.toInt(),
    priorityScore: (data['priority_score'] as num?)?.toDouble() ?? 0,
    channel: ReportChannel.values.firstWhere(
      (c) => c.name == data['channel'],
      orElse: () => ReportChannel.text,
    ),
    // Day 1 does not invent earlier/later lifecycle events.
    timeline: <TimelineEvent>[
      TimelineEvent(status: status, state: TimelineState.active, at: createdAt),
    ],
    awaitingVerification: rawStatus == 'awaiting_verification',
    rejectionReason: data['rejection_reason'] as String?,
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
  final label = factor['label'];
  final score = factor['score'];
  final weight = factor['weight'];
  final isDemo = factor['is_demo'];
  if (label is! String ||
      score is! num ||
      score < 0 ||
      score > 100 ||
      weight is! num ||
      isDemo is! bool) {
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
