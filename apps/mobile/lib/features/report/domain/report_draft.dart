import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';

import '../../../shared/models/demand_enums.dart';

/// What the report screen is holding before it becomes a Demand.
@immutable
class ReportDraft {
  const ReportDraft({
    this.transcript = '',
    this.channel = ReportChannel.voice,
    this.analysis,
    this.latitude,
    this.longitude,
    this.locationLabel = '',
    this.photos = const <XFile>[],
    this.manualTitle = '',
    this.manualCategory,
    this.manualSeverity,
    this.submissionKey,
  });

  final String transcript;
  final ReportChannel channel;

  /// Optional server suggestion. Manual fields take precedence.
  final ReportAnalysis? analysis;
  final double? latitude;
  final double? longitude;
  final String locationLabel;
  final List<XFile> photos;
  final String manualTitle;
  final DemandCategory? manualCategory;
  final Severity? manualSeverity;
  final String? submissionKey;

  List<String> get photoPaths => photos.map((p) => p.path).toList();

  ReportAnalysis? get effectiveAnalysis {
    final category = manualCategory ?? analysis?.category;
    final title = manualTitle.trim().isNotEmpty
        ? manualTitle.trim()
        : analysis?.title;
    if (category == null || title == null || title.trim().isEmpty) return null;
    return ReportAnalysis(
      category: category,
      severity: manualSeverity ?? analysis?.severity ?? Severity.medium,
      title: title,
      summary: transcript.trim(),
    );
  }

  bool get hasTranscript => transcript.trim().isNotEmpty;

  bool get hasLocation =>
      latitude != null &&
      longitude != null &&
      latitude!.isFinite &&
      longitude!.isFinite &&
      latitude! >= -90 &&
      latitude! <= 90 &&
      longitude! >= -180 &&
      longitude! <= 180;

  /// The report can be submitted once we know what it is and where it is.
  bool get canSubmit =>
      hasTranscript && effectiveAnalysis != null && hasLocation;

  ReportDraft copyWith({
    String? transcript,
    ReportChannel? channel,
    ReportAnalysis? analysis,
    double? latitude,
    double? longitude,
    String? locationLabel,
    List<XFile>? photos,
    String? manualTitle,
    DemandCategory? manualCategory,
    Severity? manualSeverity,
    String? submissionKey,
  }) => ReportDraft(
    transcript: transcript ?? this.transcript,
    channel: channel ?? this.channel,
    analysis: analysis ?? this.analysis,
    latitude: latitude ?? this.latitude,
    longitude: longitude ?? this.longitude,
    locationLabel: locationLabel ?? this.locationLabel,
    photos: photos ?? this.photos,
    manualTitle: manualTitle ?? this.manualTitle,
    manualCategory: manualCategory ?? this.manualCategory,
    manualSeverity: manualSeverity ?? this.manualSeverity,
    submissionKey: submissionKey ?? this.submissionKey,
  );
}

/// Structured output of the server-side Gemini call. The three cards on the
/// report screen render exactly these fields.
@immutable
class ReportAnalysis {
  const ReportAnalysis({
    required this.category,
    required this.severity,
    required this.title,
    this.mentionedLocation = '',
    this.summary = '',
    this.detectedLanguage = 'en',
  });

  final DemandCategory category;
  final Severity severity;
  final String title;

  /// "Location Mentioned" — what the citizen said, before they pin it exactly.
  final String mentionedLocation;
  final String summary;
  final String detectedLanguage;
}
