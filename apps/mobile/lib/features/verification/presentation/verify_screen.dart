import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/failure.dart';
import '../../../core/providers.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/janmaang_typography.dart';
import '../../../shared/models/demand_enums.dart';
import '../../../shared/widgets/jm_app_bar.dart';
import '../../../shared/widgets/jm_card.dart';
import '../../../shared/widgets/jm_states.dart';
import '../../demands/presentation/demand_providers.dart';
import '../domain/verification.dart';

final verificationRequestProvider = FutureProvider.autoDispose
    .family<VerificationRequest, String>((ref, id) {
      return ref.watch(verificationRepositoryProvider).getRequest(id);
    });

/// Citizen Verification — the Stitch "Closing the Loop" screen.
///
/// The citizen's original photo beside the officer's completion photo, then
/// the binary judgement. This is the step that makes the whole ledger
/// meaningful: the person who reported the problem decides whether public
/// money actually solved it. The photos support that judgement; they are not
/// proof of a repair.
class VerifyScreen extends ConsumerStatefulWidget {
  const VerifyScreen({super.key, required this.demandId});

  final String demandId;

  @override
  ConsumerState<VerifyScreen> createState() => _VerifyScreenState();
}

class _VerifyScreenState extends ConsumerState<VerifyScreen> {
  final _comment = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final requestAsync = ref.watch(
      verificationRequestProvider(widget.demandId),
    );
    // Keeps the signed-in user resolved for the verdict buttons.
    ref.watch(currentUserProvider);

    return Scaffold(
      appBar: JmAppBar.task(title: 'Verify'),
      body: requestAsync.when(
        loading: () => const JmLoader(),
        error: (error, _) => JmErrorView(
          error: error,
          onRetry: () =>
              ref.invalidate(verificationRequestProvider(widget.demandId)),
        ),
        data: (request) => _body(context, request),
      ),
    );
  }

  Widget _body(BuildContext context, VerificationRequest request) {
    final scheme = Theme.of(context).colorScheme;

    return ListView(
      padding: const EdgeInsets.fromLTRB(
        Insets.marginMobile,
        Insets.lg,
        Insets.marginMobile,
        Insets.xl,
      ),
      children: <Widget>[
        Text(
          'Is the problem fixed?',
          style: JanMaangTypography.displayLgMobile.copyWith(
            color: scheme.onSurface,
          ),
        ),
        const SizedBox(height: Insets.sm),
        RichText(
          text: TextSpan(
            style: JanMaangTypography.bodyMd.copyWith(
              color: scheme.onSurfaceVariant,
            ),
            children: <InlineSpan>[
              const TextSpan(text: 'Original Report: '),
              TextSpan(
                text: request.demandTitle,
                style: JanMaangTypography.withWeight(
                  JanMaangTypography.bodyMd,
                  FontWeight.w600,
                ).copyWith(color: scheme.onSurface),
              ),
              if (request.reportCode != null)
                TextSpan(text: ' · ${request.reportCode}'),
            ],
          ),
        ),
        if (request.round > 1) ...<Widget>[
          const SizedBox(height: Insets.md),
          _Note(
            icon: Icons.replay,
            text:
                'You said this was not fixed before. The officer has '
                'submitted new completion evidence (round ${request.round}).',
          ),
        ],
        const SizedBox(height: Insets.lg),

        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Expanded(
              child: _EvidenceColumn(
                label: 'BEFORE',
                photoUrl: request.beforePhotoUrl,
                caption: request.reportedAgo.isEmpty
                    ? 'Your report'
                    : 'Reported ${request.reportedAgo}',
                semanticLabel: 'Your original photo of the problem',
              ),
            ),
            const SizedBox(width: Insets.md),
            Expanded(
              child: _EvidenceColumn(
                label: 'AFTER',
                photoUrl: request.afterPhotoUrl,
                caption: request.afterPhotoUrl == null
                    ? 'No completion photo'
                    : 'Officer photo · ${request.completedAgo}',
                semanticLabel: "The officer's completion photo",
              ),
            ),
          ],
        ),
        const SizedBox(height: Insets.md),
        const _Note(
          icon: Icons.visibility_outlined,
          text:
              'These photos help you judge — they do not prove the repair. '
              'If you can, check the place yourself before answering.',
        ),

        if (request.evidenceCardUrl != null) ...<Widget>[
          const SizedBox(height: Insets.lg),
          Text(
            'Evidence card',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: Insets.sm),
          ClipRRect(
            borderRadius: BorderRadius.circular(Corners.lg),
            child: Image.network(
              request.evidenceCardUrl!,
              fit: BoxFit.contain,
              semanticLabel: 'Before and after evidence card',
              errorBuilder: (_, _, _) => const Padding(
                padding: EdgeInsets.all(Insets.md),
                child: Text('The evidence card could not load.'),
              ),
            ),
          ),
        ],

        const SizedBox(height: Insets.xl),
        if (!request.canVerify)
          _Note(
            icon: Icons.info_outline,
            text:
                request.blockedReason ??
                'This repair is not waiting for your verification.',
          )
        else ...<Widget>[
          Text(
            request.question,
            style: JanMaangTypography.headlineSm.copyWith(
              color: scheme.onSurface,
            ),
          ),
          const SizedBox(height: Insets.md),
          TextField(
            controller: _comment,
            enabled: !_submitting,
            maxLength: 500,
            maxLines: 3,
            minLines: 2,
            decoration: const InputDecoration(
              labelText: 'What do you see? (optional)',
              hintText: 'For example: water flows, but only in the morning.',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: Insets.md),
          FilledButton.icon(
            onPressed: _submitting
                ? null
                : () => _submit(request, isFixed: true),
            icon: const Icon(Icons.check_circle, size: 20),
            label: const Text('Yes, it is fixed'),
            style: FilledButton.styleFrom(
              backgroundColor: scheme.tertiaryFixed,
              foregroundColor: scheme.onTertiaryFixed,
            ),
          ),
          const SizedBox(height: Insets.md),
          OutlinedButton.icon(
            onPressed: _submitting
                ? null
                : () => _submit(request, isFixed: false),
            icon: Icon(Icons.cancel, size: 20, color: scheme.error),
            label: Text(
              'No, still broken',
              style: JanMaangTypography.labelMd.copyWith(color: scheme.error),
            ),
            style: OutlinedButton.styleFrom(
              side: BorderSide(color: scheme.error),
              minimumSize: const Size.fromHeight(52),
            ),
          ),
          const SizedBox(height: Insets.lg),
          const _Note(
            icon: Icons.info_outline,
            text:
                'Your verification matters. It helps measure whether public '
                'projects actually solve the problem.',
          ),
        ],
      ],
    );
  }

  Future<void> _submit(
    VerificationRequest request, {
    required bool isFixed,
  }) async {
    final user = ref.read(currentUserProvider);
    if (user == null) {
      // Never a silent no-op on a verdict button.
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Your session has ended. Sign in again to verify.'),
        ),
      );
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(isFixed ? 'Confirm it is fixed?' : 'Report it is still broken?'),
        content: Text(
          isFixed
              ? 'The repair will be marked citizen verified. This is recorded '
                    'publicly and cannot be changed.'
              : 'The work will go back to the officer for correction. No new '
                    'money is allocated.',
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _submitting = true);
    try {
      await ref
          .read(verificationRepositoryProvider)
          .submit(
            VerificationSubmission(
              demandId: widget.demandId,
              kind: VerificationKind.citizen,
              isFixed: isFixed,
              note: _comment.text,
              workOrderId: request.workOrderId,
              round: request.round,
            ),
            user.uid,
          );
      // The saved verdict changes the report's status everywhere it shows.
      ref
        ..invalidate(verificationRequestProvider(widget.demandId))
        ..invalidate(demandProvider(widget.demandId))
        ..invalidate(myDemandsProvider);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            isFixed
                ? 'Thank you. This repair is now citizen verified.'
                : 'Recorded. The work has been returned to the officer.',
          ),
        ),
      );
      Navigator.of(context).maybePop();
    } on Failure catch (failure) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(failure.message)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class _Note extends StatelessWidget {
  const _Note({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return JmCard(
      backgroundColor: scheme.surfaceContainer,
      borderColor: scheme.outlineVariant,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, size: 18, color: scheme.secondary),
          const SizedBox(width: Insets.sm),
          Expanded(
            child: Text(
              text,
              style: JanMaangTypography.bodySm.copyWith(
                color: scheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EvidenceColumn extends StatelessWidget {
  const _EvidenceColumn({
    required this.label,
    required this.photoUrl,
    required this.caption,
    required this.semanticLabel,
  });

  final String label;
  final String? photoUrl;
  final String caption;
  final String semanticLabel;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label,
          style: JanMaangTypography.labelMd.copyWith(
            color: scheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Insets.sm),
        ClipRRect(
          borderRadius: BorderRadius.circular(Corners.lg),
          child: Container(
            height: 150,
            decoration: BoxDecoration(
              color: scheme.surfaceContainerHigh,
              border: Border.all(color: scheme.outlineVariant),
              borderRadius: BorderRadius.circular(Corners.lg),
            ),
            child: Stack(
              fit: StackFit.expand,
              children: <Widget>[
                if (photoUrl != null)
                  // Contain, not cover: cropping could hide the damage or the
                  // repair the citizen is judging.
                  Image.network(
                    photoUrl!,
                    fit: BoxFit.contain,
                    semanticLabel: semanticLabel,
                    errorBuilder: (_, _, _) => Center(
                      child: Icon(
                        Icons.broken_image_outlined,
                        color: scheme.onSurfaceVariant,
                      ),
                    ),
                  )
                else
                  Center(
                    child: Icon(
                      Icons.photo_outlined,
                      size: 30,
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: Insets.sm,
                      vertical: Insets.xs,
                    ),
                    color: scheme.inverseSurface.withValues(alpha: 0.72),
                    child: Text(
                      caption,
                      style: JanMaangTypography.labelMd.copyWith(
                        color: scheme.onInverseSurface,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
