import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/routes.dart';
import '../../../core/localization/app_strings.dart';
import '../../../core/errors/failure.dart';
import '../../../core/providers.dart';
import '../../../core/services/media_service.dart';
import '../../../core/services/location_service.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/janmaang_typography.dart';
import '../../../shared/models/demand_enums.dart';
import '../../../shared/widgets/jm_app_bar.dart';
import '../../../shared/widgets/jm_card.dart';
import '../../../shared/widgets/jm_mic_button.dart';
import '../../../shared/widgets/jm_photo_dropzone.dart';
import '../../../shared/widgets/jm_states.dart';
import 'report_controller.dart';
import '../data/report_draft_store.dart';
import '../domain/report_draft.dart';
import 'widgets/analysis_bento.dart';
import 'widgets/location_action_card.dart';
import 'widgets/report_location_picker.dart';
import 'widgets/transcript_card.dart';
import '../../demands/presentation/demand_providers.dart';

/// Report a Need — the Stitch "Report a Need — Voice Interaction" screen.
///
/// Mic control with pulse rings, the live transcript card, the three-card AI
/// extraction bento, the location action card, and the cluster-search banner.
/// The bottom navigation is suppressed here: this is a linear, transactional
/// flow, exactly as the design specifies.
class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key, this.channel = ReportChannel.voice});

  final ReportChannel channel;

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  late final TextEditingController _textController = TextEditingController();
  late final TextEditingController _titleController = TextEditingController(
    text: ref.read(reportControllerProvider).draft.manualTitle,
  );
  bool _typing = false;
  ReportDraft? _savedDraft;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _prepareDraft());
  }

  Future<void> _prepareDraft() async {
    final uid = ref.read(currentUserProvider)?.uid;
    final store = ref.read(reportDraftStoreProvider);
    final saved = uid == null ? null : await store.load(uid);
    if (!mounted) return;

    final controller = ref.read(reportControllerProvider.notifier);
    final current = ref.read(reportControllerProvider).draft;
    if (current.hasSavedContent) {
      controller.setChannel(widget.channel);
      return;
    }

    if (saved != null) {
      setState(() => _savedDraft = saved);
      return;
    }

    controller.setChannel(widget.channel);
    switch (widget.channel) {
      case ReportChannel.text:
        setState(() => _typing = true);
      case ReportChannel.photo:
        _pickPhotos();
      case ReportChannel.location:
        controller.useCurrentLocation();
      case ReportChannel.voice:
        break;
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    _titleController.dispose();
    super.dispose();
  }

  Future<void> _pickPhotos() async {
    try {
      final photos = await ref
          .read(mediaServiceProvider)
          .pickPhotos(
            existingCount: ref
                .read(reportControllerProvider)
                .draft
                .photos
                .length,
          );
      if (!mounted || photos.isEmpty) return;
      await ref.read(reportControllerProvider.notifier).addPhotos(photos);
    } on Failure catch (failure) {
      if (mounted) {
        ref.read(reportControllerProvider.notifier).showFailure(failure);
      }
    } catch (_) {
      if (mounted) {
        ref
            .read(reportControllerProvider.notifier)
            .showFailure(
              const ValidationFailure(
                'Photos could not be selected. Check browser permissions.',
              ),
            );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final strings = AppStrings.of(context);
    final state = ref.watch(reportControllerProvider);
    final controller = ref.read(reportControllerProvider.notifier);

    // A matching cluster means the citizen should join rather than duplicate.
    ref.listen(reportControllerProvider, (previous, next) {
      // A suggestion or a restored draft can set the title from outside the
      // field; typing already matches, so the cursor is left alone then.
      if (_titleController.text != next.draft.manualTitle) {
        _titleController.text = next.draft.manualTitle;
      }
      final uid = ref.read(currentUserProvider)?.uid;
      if (uid != null) {
        final store = ref.read(reportDraftStoreProvider);
        if (next.submitted != null) {
          unawaited(store.clear(uid));
        } else if (next.draft.hasSavedContent) {
          unawaited(store.save(uid, next.draft));
        } else if (previous?.draft.hasSavedContent == true) {
          unawaited(store.clear(uid));
        }
      }
      final cluster = next.similarCluster;
      if (cluster != null && previous?.similarCluster == null && mounted) {
        context.pushNamed(
          AppRoute.cluster.name,
          pathParameters: <String, String>{'id': cluster.id},
        );
      }
      final error = next.error;
      if (error != null && previous?.error != error && mounted) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(error.message)));
        controller.dismissError();
      }
    });

    return Scaffold(
      appBar: JmAppBar.task(title: strings.text('report_title')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            Insets.marginMobile,
            Insets.lg,
            Insets.marginMobile,
            Insets.xl,
          ),
          children: <Widget>[
            if (_savedDraft != null) ...<Widget>[
              JmCard(
                padding: const EdgeInsets.all(Insets.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      strings.text('draft_available'),
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: Insets.xs),
                    Text(strings.text('draft_storage_note')),
                    const SizedBox(height: Insets.sm),
                    Wrap(
                      spacing: Insets.sm,
                      children: <Widget>[
                        FilledButton(
                          onPressed: () {
                            final draft = _savedDraft!;
                            controller.restoreDraft(draft);
                            _textController.text = draft.transcript;
                            setState(() {
                              _typing = draft.channel == ReportChannel.text;
                              _savedDraft = null;
                            });
                          },
                          child: Text(strings.text('restore_draft')),
                        ),
                        TextButton(
                          onPressed: () async {
                            final uid = ref.read(currentUserProvider)?.uid;
                            if (uid != null) {
                              await ref
                                  .read(reportDraftStoreProvider)
                                  .clear(uid);
                            }
                            if (mounted) setState(() => _savedDraft = null);
                          },
                          child: Text(strings.text('discard_draft')),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: Insets.md),
            ],
            Center(
              child: Text(
                strings.text('report_prompt'),
                textAlign: TextAlign.center,
                style: JanMaangTypography.titleLg.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ),
            const SizedBox(height: Insets.md),

            Center(
              child: JmMicButton(
                isListening: state.isListening,
                onPressed: controller.toggleListening,
              ),
            ),

            Center(
              child: TextButton.icon(
                onPressed: () => setState(() => _typing = !_typing),
                icon: Icon(
                  _typing ? Icons.mic_none : Icons.keyboard_outlined,
                  size: 18,
                ),
                label: Text(
                  strings.text(_typing ? 'use_voice' : 'type_instead'),
                ),
              ),
            ),
            const SizedBox(height: Insets.md),

            if (_typing || !state.speechAvailable)
              _TypedInput(
                controller: _textController,
                onChanged: controller.updateTranscript,
                onSubmitted: (_) => controller.analyze(),
                enabled: !state.isBusy,
              )
            else if (state.draft.hasTranscript)
              TranscriptCard(
                transcript: state.draft.transcript,
                isRecording: state.isListening,
              ),

            if (state.isAnalyzing) ...<Widget>[
              const SizedBox(height: Insets.md),
              JmInlineLoader(message: strings.text('understanding_report')),
            ],

            const SizedBox(height: Insets.md),
            OutlinedButton.icon(
              onPressed: state.draft.hasTranscript && !state.isBusy
                  ? controller.analyze
                  : null,
              icon: const Icon(Icons.auto_awesome_outlined),
              label: Text(strings.text('suggest_details')),
            ),
            const SizedBox(height: Insets.md),
            Text(
              strings.text('report_details'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            Text(strings.text('manual_suggestion_help')),
            const SizedBox(height: Insets.sm),
            TextFormField(
              controller: _titleController,
              enabled: !state.isBusy,
              decoration: InputDecoration(
                labelText: strings.text('short_title'),
              ),
              onChanged: controller.updateManualTitle,
            ),
            const SizedBox(height: Insets.sm),
            // Keyed by value: initialValue is read once, so a suggestion
            // or restored draft rebuilds the field to show its choice.
            DropdownButtonFormField<DemandCategory>(
              key: ValueKey(state.draft.manualCategory),
              initialValue: state.draft.manualCategory,
              decoration: InputDecoration(labelText: strings.text('category')),
              items: <DropdownMenuItem<DemandCategory>>[
                for (final category in DemandCategory.values)
                  DropdownMenuItem(
                    value: category,
                    child: Text(strings.category(category)),
                  ),
              ],
              onChanged: state.isBusy
                  ? null
                  : (value) {
                      if (value != null) controller.updateManualCategory(value);
                    },
            ),
            const SizedBox(height: Insets.sm),
            DropdownButtonFormField<Severity>(
              key: ValueKey(state.draft.manualSeverity),
              initialValue: state.draft.manualSeverity ?? Severity.medium,
              decoration: InputDecoration(
                labelText: strings.text('reported_severity'),
              ),
              items: <DropdownMenuItem<Severity>>[
                for (final severity in Severity.values)
                  DropdownMenuItem(
                    value: severity,
                    child: Text(strings.severity(severity)),
                  ),
              ],
              onChanged: state.isBusy
                  ? null
                  : (value) {
                      if (value != null) controller.updateManualSeverity(value);
                    },
            ),

            if (state.draft.analysis != null) ...<Widget>[
              const SizedBox(height: Insets.lg),
              AnalysisBento(
                analysis: state.draft.analysis!,
                pinnedLocation: state.draft.locationLabel,
              ),
            ],
            const SizedBox(height: Insets.lg),
            LocationActionCard(
              hasLocation: state.draft.hasLocation,
              locationLabel: state.draft.locationLabel,
              onUseMyLocation: controller.useCurrentLocation,
              onSelectOnMap: () => _selectOnMap(context),
            ),

            const SizedBox(height: Insets.lg),
            Text(
              strings.text('add_photo'),
              style: JanMaangTypography.titleLg.copyWith(
                color: scheme.onSurface,
              ),
            ),
            const SizedBox(height: Insets.sm),
            JmPhotoDropzone(
              onTap: state.isBusy ? () {} : _pickPhotos,
              title: strings.text('add_photo_problem'),
              subtitle: strings.text('photo_details'),
              photos: state.draft.photos,
              onRemove: state.isBusy ? null : controller.removePhoto,
              height: 120,
            ),

            if (state.isSearchingCluster) ...<Widget>[
              const SizedBox(height: Insets.md),
              JmInlineLoader(message: strings.text('finding_similar')),
            ],

            const SizedBox(height: Insets.xl),
            FilledButton(
              onPressed: state.draft.canSubmit && !state.isBusy
                  ? () => _submit(context)
                  : null,
              child: state.isSubmitting
                  ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: scheme.onPrimary,
                      ),
                    )
                  : Text(strings.text('submit_report')),
            ),
            const SizedBox(height: Insets.sm),
            Center(
              child: Text(
                state.draft.canSubmit
                    ? strings.text('submit_hint_ready')
                    : strings.text('submit_hint_missing'),
                textAlign: TextAlign.center,
                style: JanMaangTypography.bodySm.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _selectOnMap(BuildContext context) async {
    final draft = ref.read(reportControllerProvider).draft;
    final position = await Navigator.of(context).push<ResolvedPosition>(
      MaterialPageRoute<ResolvedPosition>(
        builder: (_) => ReportLocationPicker(
          initialPosition: draft.hasLocation
              ? ResolvedPosition(
                  latitude: draft.latitude!,
                  longitude: draft.longitude!,
                  label: draft.locationLabel,
                )
              : null,
        ),
      ),
    );
    if (!mounted || position == null) return;
    ref
        .read(reportControllerProvider.notifier)
        .setLocation(
          latitude: position.latitude,
          longitude: position.longitude,
          label: position.label,
        );
  }

  Future<void> _submit(BuildContext context) async {
    final demand = await ref.read(reportControllerProvider.notifier).submit();
    if (demand == null || !context.mounted) return;
    ref.invalidate(myDemandsProvider);
    ref.invalidate(demandProvider(demand.id));
    ref.read(reportControllerProvider.notifier).reset();
    context.pushReplacementNamed(
      AppRoute.demandDetail.name,
      pathParameters: <String, String>{'id': demand.id},
    );
  }
}

class _TypedInput extends StatelessWidget {
  const _TypedInput({
    required this.controller,
    required this.onChanged,
    required this.onSubmitted,
    required this.enabled,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final ValueChanged<String> onSubmitted;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final strings = AppStrings.of(context);
    return JmCard(
      padding: const EdgeInsets.all(Insets.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(
                Icons.format_quote,
                size: 16,
                color: scheme.onSurfaceVariant,
              ),
              const SizedBox(width: Insets.sm),
              Text(
                'IN YOUR OWN WORDS',
                style: JanMaangTypography.labelMd.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
          const SizedBox(height: Insets.sm),
          TextField(
            controller: controller,
            enabled: enabled,
            maxLines: 5,
            minLines: 3,
            textInputAction: TextInputAction.done,
            style: JanMaangTypography.bodyLg.copyWith(color: scheme.onSurface),
            decoration: InputDecoration(
              hintText: strings.text('report_example'),
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              filled: false,
              contentPadding: EdgeInsets.zero,
            ),
            onChanged: onChanged,
            onSubmitted: onSubmitted,
          ),
        ],
      ),
    );
  }
}
