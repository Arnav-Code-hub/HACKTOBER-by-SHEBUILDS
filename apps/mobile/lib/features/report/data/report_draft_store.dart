import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../shared/models/demand_enums.dart';
import '../domain/report_draft.dart';

abstract interface class ReportDraftStore {
  Future<ReportDraft?> load(String uid);
  Future<void> save(String uid, ReportDraft draft);
  Future<void> clear(String uid);
}

final reportDraftStoreProvider = Provider<ReportDraftStore>(
  (ref) => SharedPreferencesReportDraftStore(),
);

class SharedPreferencesReportDraftStore implements ReportDraftStore {
  static const _prefix = 'janmaang.reportDraft.';
  Future<void> _writeQueue = Future<void>.value();

  String _key(String uid) => '$_prefix$uid';

  Future<void> _enqueue(Future<void> Function() operation) {
    final write = _writeQueue.then((_) => operation());
    _writeQueue = write.catchError((Object _) {});
    return write;
  }

  @override
  Future<ReportDraft?> load(String uid) async {
    await _writeQueue;
    final preferences = await SharedPreferences.getInstance();
    await _removeOtherUsers(preferences, uid);
    final raw = preferences.getString(_key(uid));
    if (raw == null) return null;
    try {
      return _decode(jsonDecode(raw) as Map<String, Object?>);
    } catch (_) {
      await preferences.remove(_key(uid));
      return null;
    }
  }

  @override
  Future<void> save(String uid, ReportDraft draft) => _enqueue(() async {
    final preferences = await SharedPreferences.getInstance();
    await _removeOtherUsers(preferences, uid);
    if (!draft.hasSavedContent) {
      await preferences.remove(_key(uid));
      return;
    }
    await preferences.setString(_key(uid), jsonEncode(_encode(draft)));
  });

  @override
  Future<void> clear(String uid) => _enqueue(() async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.remove(_key(uid));
  });

  Future<void> _removeOtherUsers(
    SharedPreferences preferences,
    String uid,
  ) async {
    for (final key in preferences.getKeys()) {
      if (key.startsWith(_prefix) && key != _key(uid)) {
        await preferences.remove(key);
      }
    }
  }

  Map<String, Object?> _encode(ReportDraft draft) => <String, Object?>{
    'transcript': draft.transcript,
    'channel': draft.channel.name,
    'latitude': draft.latitude,
    'longitude': draft.longitude,
    'locationLabel': draft.locationLabel,
    'manualTitle': draft.manualTitle,
    'manualCategory': draft.manualCategory?.name,
    'manualSeverity': draft.manualSeverity?.name,
    'submissionKey': draft.submissionKey,
    'analysis': draft.analysis == null
        ? null
        : <String, Object?>{
            'category': draft.analysis!.category.name,
            'severity': draft.analysis!.severity.name,
            'title': draft.analysis!.title,
            'mentionedLocation': draft.analysis!.mentionedLocation,
            'summary': draft.analysis!.summary,
            'detectedLanguage': draft.analysis!.detectedLanguage,
          },
  };

  ReportDraft _decode(Map<String, Object?> json) {
    DemandCategory? category(String? name) {
      for (final value in DemandCategory.values) {
        if (value.name == name) return value;
      }
      return null;
    }

    Severity? severity(String? name) {
      for (final value in Severity.values) {
        if (value.name == name) return value;
      }
      return null;
    }

    ReportAnalysis? analysis() {
      final value = json['analysis'];
      if (value is! Map<String, dynamic>) return null;
      final analysisCategory = category(value['category'] as String?);
      final analysisSeverity = severity(value['severity'] as String?);
      if (analysisCategory == null || analysisSeverity == null) return null;
      return ReportAnalysis(
        category: analysisCategory,
        severity: analysisSeverity,
        title: value['title'] as String? ?? '',
        mentionedLocation: value['mentionedLocation'] as String? ?? '',
        summary: value['summary'] as String? ?? '',
        detectedLanguage: value['detectedLanguage'] as String? ?? 'en',
      );
    }

    final channelName = json['channel'] as String? ?? 'voice';
    return ReportDraft(
      transcript: json['transcript'] as String? ?? '',
      channel: ReportChannel.values.firstWhere(
        (value) => value.name == channelName,
        orElse: () => ReportChannel.voice,
      ),
      analysis: analysis(),
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      locationLabel: json['locationLabel'] as String? ?? '',
      manualTitle: json['manualTitle'] as String? ?? '',
      manualCategory: category(json['manualCategory'] as String?),
      manualSeverity: severity(json['manualSeverity'] as String?),
      submissionKey: json['submissionKey'] as String?,
    );
  }
}

extension SavedReportDraft on ReportDraft {
  bool get hasSavedContent =>
      transcript.trim().isNotEmpty ||
      manualTitle.trim().isNotEmpty ||
      locationLabel.trim().isNotEmpty ||
      analysis != null;
}
