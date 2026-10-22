import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/routes.dart';
import '../../../core/errors/failure.dart';
import '../../../core/services/media_service.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/janmaang_typography.dart';
import '../../../shared/models/demand_enums.dart';
import '../../../shared/widgets/jm_app_bar.dart';
import '../../../shared/widgets/jm_card.dart';
import '../../../shared/widgets/jm_mic_button.dart';
import '../../../shared/widgets/jm_photo_dropzone.dart';
import '../../../shared/widgets/jm_states.dart';
import 'report_controller.dart';
import 'widgets/analysis_bento.dart';
import 'widgets/location_action_card.dart';
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
  bool _typing = false;

  @override
  void initState() {
    super.initState();
    // The Home card decides which entry point opened this screen.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final controller = ref.read(reportControllerProvider.notifier)
        ..setChannel(widget.channel);
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
    });
  }

  @override
  void dispose() {
    _textController.dispose();
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
    final state = ref.watch(reportControllerProvider);
    final controller = ref.read(reportControllerProvider.notifier);

    // A matching cluster means the citizen should join rather than duplicate.
    ref.listen(reportControllerProvider, (previous, next) {
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
      appBar: JmAppBar.task(title: 'Report a Need'),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            Insets.marginMobile,
            Insets.lg,
            Insets.marginMobile,
            Insets.xl,
          ),
          children: <Widget>[
            Center(
              child: Text(
                'Tell us what your community needs.',
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
                label: Text(_typing ? 'Use voice instead' : 'Type it instead'),
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
              const JmInlineLoader(message: 'Understanding your report…'),
            ],

            const SizedBox(height: Insets.md),
            OutlinedButton.icon(
              onPressed: state.draft.hasTranscript && !state.isBusy
                  ? controller.analyze
                  : null,
              icon: const Icon(Icons.auto_awesome_outlined),
              label: const Text('Suggest details (optional)'),
            ),
            const SizedBox(height: Insets.md),
            Text(
              'Report details',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const Text(
              'Enter these yourself if suggestions are unavailable. '
              'These are your reported details; officials will review them.',
            ),
            const SizedBox(height: Insets.sm),
            TextFormField(
              initialValue: state.draft.manualTitle,
              enabled: !state.isBusy,
              decoration: const InputDecoration(labelText: 'Short title'),
              onChanged: controller.updateManualTitle,
            ),
            const SizedBox(height: Insets.sm),
            DropdownButtonFormField<DemandCategory>(
              initialValue: state.draft.manualCategory,
              decoration: const InputDecoration(labelText: 'Category'),
              items: <DropdownMenuItem<DemandCategory>>[
                for (final category in DemandCategory.values)
                  DropdownMenuItem(
                    value: category,
                    child: Text(category.label),
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
              initialValue: state.draft.manualSeverity ?? Severity.medium,
              decoration: const InputDecoration(labelText: 'Reported severity'),
              items: <DropdownMenuItem<Severity>>[
                for (final severity in Severity.values)
                  DropdownMenuItem(
                    value: severity,
                    child: Text(severity.label),
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
              'Add a photo',
              style: JanMaangTypography.titleLg.copyWith(
                color: scheme.onSurface,
              ),
            ),
            const SizedBox(height: Insets.sm),
            JmPhotoDropzone(
              onTap: state.isBusy ? () {} : _pickPhotos,
              title: 'Add a photo of the problem',
              subtitle:
                  'Optional · JPEG, PNG, WebP · 3 photos total · 10 MB each',
              photos: state.draft.photos,
              onRemove: state.isBusy ? null : controller.removePhoto,
              height: 120,
            ),

            if (state.isSearchingCluster) ...<Widget>[
              const SizedBox(height: Insets.md),
              const JmInlineLoader(
                message: 'Finding similar requests in this area…',
              ),
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
                  : const Text('Submit report'),
            ),
            const SizedBox(height: Insets.sm),
            Center(
              child: Text(
                state.draft.canSubmit
                    ? 'Submit to save your report. Unsent drafts stay only in this tab.'
                    : 'Add the problem, title and category, then pin its location.',
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
    // Pinning on a full map needs the Maps SDK key; until then the citizen can
    // still file with the coarse fix from their device.
    final controller = ref.read(reportControllerProvider.notifier);
    await controller.useCurrentLocation();
    if (!context.mounted) return;
    if (!ref.read(reportControllerProvider).draft.hasLocation) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Pinned to your current position. Drag-to-pin arrives '
          'with the map key.',
        ),
      ),
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
            decoration: const InputDecoration(
              hintText:
                  'e.g. Our village has had no drinking water for two '
                  'months.',
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
