import '../../demands/domain/demand.dart';
import 'report_draft.dart';

import 'package:image_picker/image_picker.dart';

class UploadedMedia {
  const UploadedMedia({required this.id, required this.url, this.thumbnailUrl});
  final String id;
  final String url;
  final String? thumbnailUrl;
}

abstract interface class ReportRepository {
  /// Optional server-side classification; may be unavailable in Day 1 live mode.
  Future<ReportAnalysis> analyze({
    required String transcript,
    List<String> photoPaths = const <String>[],
  });

  /// Persists the report and returns the created demand.
  Future<Demand> submit(ReportDraft draft, String uid);

  /// Uploads local evidence and returns asset IDs separately from delivery URLs.
  Future<List<UploadedMedia>> uploadPhotos(List<XFile> photos, String uid);
}
