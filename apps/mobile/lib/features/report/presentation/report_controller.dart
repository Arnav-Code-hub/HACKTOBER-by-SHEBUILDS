import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/config/app_config.dart';
import '../../../core/errors/failure.dart';
import '../../../core/localization/app_locale.dart';
import '../../../core/network/api_client.dart';
import '../../../core/providers.dart';
import '../../../core/services/location_service.dart';
import '../../../core/services/speech_service.dart';
import '../../../core/services/media_service.dart';
import '../../../shared/models/demand_enums.dart';
import '../../demands/domain/demand.dart';
import '../../demands/domain/demand_cluster.dart';
import '../domain/report_draft.dart';
import '../data/report_draft_store.dart';

/// Everything the Report screen needs to render, in one immutable value.
@immutable
class ReportState {
  const ReportState({
    this.draft = const ReportDraft(),
    this.isListening = false,
    this.isAnalyzing = false,
    this.isSearchingCluster = false,
    this.isSubmitting = false,
    this.similarCluster,
    this.submitted,
    this.error,
    this.speechAvailable = true,
  });

  final ReportDraft draft;
  final bool isListening;
  final bool isAnalyzing;

  /// Drives the "Finding similar requests in this area…" banner.
  final bool isSearchingCluster;
  final bool isSubmitting;

  /// Non-null once a matching cluster is found — routes to "You are not alone".
  final DemandCluster? similarCluster;
  final Demand? submitted;
  final Failure? error;
  final bool speechAvailable;

  bool get isBusy => isAnalyzing || isSearchingCluster || isSubmitting;

  ReportState copyWith({
    ReportDraft? draft,
    bool? isListening,
    bool? isAnalyzing,
    bool? isSearchingCluster,
    bool? isSubmitting,
    DemandCluster? similarCluster,
    Demand? submitted,
    Failure? error,
    bool? speechAvailable,
    bool clearError = false,
    bool clearCluster = false,
  }) => ReportState(
    draft: draft ?? this.draft,
    isListening: isListening ?? this.isListening,
    isAnalyzing: isAnalyzing ?? this.isAnalyzing,
    isSearchingCluster: isSearchingCluster ?? this.isSearchingCluster,
    isSubmitting: isSubmitting ?? this.isSubmitting,
    similarCluster: clearCluster
        ? null
        : (similarCluster ?? this.similarCluster),
    submitted: submitted ?? this.submitted,
    error: clearError ? null : (error ?? this.error),
    speechAvailable: speechAvailable ?? this.speechAvailable,
  );
}

/// Orchestrates the report flow: listen → transcribe → analyse (Gemini,
/// server-side) → pin location → look for a cluster → submit.
class ReportController extends Notifier<ReportState> {
  @override
  ReportState build() {
    // Preserve an unsent form across navigation, but never across identities.
    ref.watch(currentUserProvider.select((user) => user?.uid));
    final speech = ref.read(speechServiceProvider);
    ref.onDispose(() => unawaited(speech.stop()));
    return ReportState(draft: ReportDraft(submissionKey: newRequestKey()));
  }

  void setChannel(ReportChannel channel) {
    state = state.copyWith(draft: state.draft.copyWith(channel: channel));
  }

  void restoreDraft(ReportDraft draft) {
    state = state.copyWith(draft: draft, clearError: true);
  }

  Future<void> toggleListening() async {
    final speech = ref.read(speechServiceProvider);

    if (state.isListening) {
      await speech.stop();
      state = state.copyWith(isListening: false);
      if (state.draft.hasTranscript) await analyze();
      return;
    }

    final available = await speech.initialize();
    if (!available) {
      state = state.copyWith(
        speechAvailable: false,
        error: const PermissionFailure(
          'Microphone access is unavailable. You can type the request instead.',
        ),
      );
      return;
    }

    state = state.copyWith(
      isListening: true,
      clearError: true,
      draft: state.draft.copyWith(transcript: '', channel: ReportChannel.voice),
    );

    String? speechLocale;
    try {
      final languageCode =
          ref.read(appLocaleProvider).value?.languageCode ?? 'en';
      for (final locale in await speech.locales()) {
        if (locale.toLowerCase().split(RegExp('[-_]')).first == languageCode) {
          speechLocale = locale;
          break;
        }
      }
    } catch (_) {
      // Keep the device's default if locale discovery is unavailable.
    }

    await speech.listen(
      localeId: speechLocale,
      onResult: (text) {
        state = state.copyWith(draft: state.draft.copyWith(transcript: text));
      },
      onDone: () async {
        if (!state.isListening) return;
        state = state.copyWith(isListening: false);
        if (state.draft.hasTranscript) await analyze();
      },
    );
  }

  void updateTranscript(String text) {
    state = state.copyWith(
      draft: state.draft.copyWith(transcript: text),
      clearError: true,
    );
  }

  void updateManualTitle(String title) => state = state.copyWith(
    draft: state.draft.copyWith(manualTitle: title),
    clearError: true,
  );

  void updateManualCategory(DemandCategory category) => state = state.copyWith(
    draft: state.draft.copyWith(manualCategory: category),
    clearError: true,
  );

  void updateManualSeverity(Severity severity) => state = state.copyWith(
    draft: state.draft.copyWith(manualSeverity: severity),
    clearError: true,
  );

  void showFailure(Failure failure) => state = state.copyWith(error: failure);

  /// Requests an optional server-side suggestion. Manual details still submit
  /// when this feature is unavailable; no Gemini key is sent to the client.
  Future<void> analyze() async {
    if (!state.draft.hasTranscript) return;
    final transcript = state.draft.transcript;
    final key = state.draft.submissionKey;
    state = state.copyWith(isAnalyzing: true, clearError: true);
    try {
      final analysis = await ref
          .read(reportRepositoryProvider)
          .analyze(
            transcript: state.draft.transcript,
            photoPaths: state.draft.photoPaths,
          );
      if (state.draft.submissionKey != key) return;
      state = state.copyWith(
        isAnalyzing: false,
        draft: state.draft.transcript != transcript
            ? state.draft
            // The suggestion fills only details the citizen left empty;
            // anything they entered stays theirs.
            : state.draft.copyWith(
                analysis: analysis,
                manualTitle: state.draft.manualTitle.trim().isEmpty
                    ? analysis.title
                    : state.draft.manualTitle,
                manualCategory: state.draft.manualCategory ?? analysis.category,
                manualSeverity: state.draft.manualSeverity ?? analysis.severity,
                locationLabel: state.draft.locationLabel.isEmpty
                    ? analysis.mentionedLocation
                    : state.draft.locationLabel,
              ),
      );
    } on Failure catch (failure) {
      if (state.draft.submissionKey != key) return;
      state = state.copyWith(isAnalyzing: false, error: failure);
    } catch (_) {
      if (state.draft.submissionKey != key) return;
      state = state.copyWith(
        isAnalyzing: false,
        error: const ServerFailure(
          'Suggestions failed. Enter report details manually.',
        ),
      );
    }
  }

  Future<void> useCurrentLocation() async {
    state = state.copyWith(clearError: true);
    try {
      final position = await ref
          .read(locationServiceProvider)
          .currentPosition();
      state = state.copyWith(
        draft: state.draft.copyWith(
          latitude: position.latitude,
          longitude: position.longitude,
          locationLabel: position.label,
        ),
      );
      await _searchForCluster();
    } on Failure catch (failure) {
      state = state.copyWith(error: failure);
    }
  }

  void setLocation({
    required double latitude,
    required double longitude,
    required String label,
  }) {
    state = state.copyWith(
      clearError: true,
      draft: state.draft.copyWith(
        latitude: latitude,
        longitude: longitude,
        locationLabel: label,
      ),
    );
    unawaited(_searchForCluster());
  }

  Future<void> addPhotos(List<XFile> photos) async {
    final key = state.draft.submissionKey;
    try {
      PhotoRules.checkCount(state.draft.photos.length, photos.length);
      for (final photo in photos) {
        await PhotoRules.validate(photo);
      }
      if (state.draft.submissionKey != key) return;
      // Recheck after awaiting: another picker callback may have completed.
      PhotoRules.checkCount(state.draft.photos.length, photos.length);
      state = state.copyWith(
        draft: state.draft.copyWith(
          photos: <XFile>[...state.draft.photos, ...photos],
        ),
        clearError: true,
      );
    } on Failure catch (failure) {
      state = state.copyWith(error: failure);
    } catch (_) {
      state = state.copyWith(
        error: const ValidationFailure(
          'This photo could not be read. Choose another.',
        ),
      );
    }
  }

  void removePhoto(int index) {
    final next = <XFile>[...state.draft.photos]..removeAt(index);
    state = state.copyWith(draft: state.draft.copyWith(photos: next));
  }

  /// The "Finding similar requests in this area…" step. If a cluster comes
  /// back, the UI offers "You are not alone" before filing a duplicate.
  Future<void> _searchForCluster() async {
    if (!AppConfig.useMocks) return; // Day 2 capability, never a fake match.
    final draft = state.draft;
    final analysis = draft.effectiveAnalysis;
    if (analysis == null || !draft.hasLocation) return;

    state = state.copyWith(isSearchingCluster: true, clearCluster: true);
    try {
      final cluster = await ref
          .read(demandsRepositoryProvider)
          .findSimilarCluster(
            category: analysis.category,
            latitude: draft.latitude!,
            longitude: draft.longitude!,
          );
      state = state.copyWith(
        isSearchingCluster: false,
        similarCluster: cluster,
      );
    } on Failure catch (failure) {
      state = state.copyWith(isSearchingCluster: false, error: failure);
    }
  }

  Future<Demand?> submit() async {
    if (state.isSubmitting) return null;
    final user = ref.read(currentUserProvider);
    if (user == null) {
      state = state.copyWith(
        error: const AuthFailure('Please sign in before filing a report.'),
      );
      return null;
    }
    if (!state.draft.canSubmit) {
      state = state.copyWith(
        error: const ValidationFailure(
          'Add what the problem is and where it is before submitting.',
        ),
      );
      return null;
    }

    state = state.copyWith(isSubmitting: true, clearError: true);
    final key = state.draft.submissionKey;
    try {
      final demand = await ref
          .read(reportRepositoryProvider)
          .submit(state.draft, user.uid);
      if (state.draft.submissionKey != key ||
          ref.read(currentUserProvider)?.uid != user.uid) {
        return null;
      }
      state = state.copyWith(isSubmitting: false, submitted: demand);
      unawaited(ref.read(reportDraftStoreProvider).clear(user.uid));
      return demand;
    } on Failure catch (failure) {
      if (state.draft.submissionKey != key) return null;
      state = state.copyWith(isSubmitting: false, error: failure);
      return null;
    } catch (_) {
      if (state.draft.submissionKey != key) return null;
      state = state.copyWith(
        isSubmitting: false,
        error: const ServerFailure(
          'Submission could not finish. Keep this tab open and retry.',
        ),
      );
      return null;
    }
  }

  void reset() =>
      state = ReportState(draft: ReportDraft(submissionKey: newRequestKey()));

  void dismissError() => state = state.copyWith(clearError: true);
}

final reportControllerProvider =
    NotifierProvider<ReportController, ReportState>(ReportController.new);
