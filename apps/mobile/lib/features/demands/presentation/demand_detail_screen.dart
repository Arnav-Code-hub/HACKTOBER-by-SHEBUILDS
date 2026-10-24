import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_config.dart';
import '../../../core/providers.dart';
import '../../../core/routing/routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/janmaang_typography.dart';
import '../../../shared/models/demand_enums.dart';
import '../../../shared/widgets/jm_app_bar.dart';
import '../../../shared/widgets/jm_card.dart';
import '../../../shared/widgets/jm_metric_bar.dart';
import '../../../shared/widgets/jm_rank_badge.dart';
import '../../../shared/widgets/jm_states.dart';
import '../../../shared/widgets/jm_status_chip.dart';
import '../../../shared/widgets/jm_timeline.dart';
import '../domain/demand.dart';
import 'demand_providers.dart';

/// Track Demand — the Stitch "Transparency Flow" screen.
///
/// Rank badge and public code, the demand title, the "Why is this ranked #2?"
/// card with its five metric bars and the objection action, and the status
/// timeline. Two columns on wide screens, stacked on mobile.
class DemandDetailScreen extends ConsumerWidget {
  const DemandDetailScreen({super.key, required this.demandId});

  final String demandId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final demandAsync = ref.watch(demandProvider(demandId));
    final userId = ref.watch(currentUserProvider)?.uid;

    return Scaffold(
      appBar: JmAppBar.task(title: 'Demand'),
      body: demandAsync.when(
        loading: () => const JmLoader(message: 'Loading this demand…'),
        error: (error, _) => JmErrorView(
          error: error,
          onRetry: () => ref.invalidate(demandProvider(demandId)),
        ),
        data: (demand) => _Body(
          demand: demand,
          // Only the original reporter is asked; the API enforces it too.
          canVerify: demand.awaitingVerification && demand.reporterId == userId,
        ),
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({required this.demand, required this.canVerify});

  final Demand demand;
  final bool canVerify;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isWide = MediaQuery.of(context).size.width >= Breakpoints.medium;

    final ranking = _RankingCard(demand: demand);
    final timeline = _TimelineCard(demand: demand);

    return ListView(
      padding: const EdgeInsets.fromLTRB(
        Insets.marginMobile,
        Insets.lg,
        Insets.marginMobile,
        Insets.xl,
      ),
      children: <Widget>[
        Wrap(
          spacing: Insets.sm,
          runSpacing: Insets.sm,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: <Widget>[
            if (demand.rank != null)
              JmRankBadge(rank: demand.rank!, total: demand.totalRanked),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: Insets.sm,
                vertical: Insets.xs,
              ),
              decoration: BoxDecoration(
                color: scheme.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(Corners.sm),
              ),
              child: Text(
                demand.code,
                style: JanMaangTypography.tabularNums.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ),
            JmStatusChip.forStatus(demand.status),
          ],
        ),
        const SizedBox(height: Insets.md),
        Text(
          demand.title,
          style: JanMaangTypography.displayLgMobile.copyWith(
            color: scheme.onSurface,
          ),
        ),
        if (demand.description.isNotEmpty) ...<Widget>[
          const SizedBox(height: Insets.sm),
          Text(
            demand.description,
            style: JanMaangTypography.bodyMd.copyWith(
              color: scheme.onSurfaceVariant,
            ),
          ),
        ],
        if (demand.status == DemandStatus.rejected) ...<Widget>[
          const SizedBox(height: Insets.md),
          JmCard(
            backgroundColor: scheme.errorContainer,
            borderColor: scheme.error,
            child: Text(
              demand.rejectionReason == null
                  ? 'The Panchayat did not accept this report.'
                  : 'The Panchayat did not accept this report: '
                        '${demand.rejectionReason}',
              style: JanMaangTypography.bodyMd.copyWith(
                color: scheme.onErrorContainer,
              ),
            ),
          ),
        ],
        if (canVerify) ...<Widget>[
          const SizedBox(height: Insets.md),
          JmCard(
            backgroundColor: scheme.tertiaryContainer,
            borderColor: scheme.tertiary,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'The officer says the work is done.',
                  style: JanMaangTypography.titleLg.copyWith(
                    color: scheme.onTertiaryContainer,
                  ),
                ),
                const SizedBox(height: Insets.xs),
                Text(
                  'You reported this problem, so you decide whether it is '
                  'really fixed.',
                  style: JanMaangTypography.bodySm.copyWith(
                    color: scheme.onTertiaryContainer,
                  ),
                ),
                const SizedBox(height: Insets.md),
                FilledButton.icon(
                  onPressed: () => context.pushNamed(
                    AppRoute.verify.name,
                    pathParameters: <String, String>{'id': demand.id},
                  ),
                  icon: const Icon(Icons.fact_check_outlined, size: 20),
                  label: const Text('Verify the repair'),
                ),
              ],
            ),
          ),
        ],
        if (demand.photoUrls.isNotEmpty) ...<Widget>[
          const SizedBox(height: Insets.md),
          Text(
            'Report evidence',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: Insets.sm),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              for (var i = 0; i < demand.photoUrls.length; i++)
                _EvidenceThumbnail(
                  // The thumbnail variant keeps the page light on slow
                  // connections; tapping opens the full-size photo.
                  thumbnailUrl: i < demand.photoThumbnailUrls.length
                      ? demand.photoThumbnailUrls[i]
                      : demand.photoUrls[i],
                  fullUrl: demand.photoUrls[i],
                ),
            ],
          ),
        ],
        const SizedBox(height: Insets.lg),

        if (isWide)
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Expanded(flex: 7, child: ranking),
                const SizedBox(width: Insets.lg),
                Expanded(flex: 5, child: timeline),
              ],
            ),
          )
        else ...<Widget>[ranking, const SizedBox(height: Insets.lg), timeline],
      ],
    );
  }
}

/// "Why is this ranked #2?" — the five priority factors, each a labelled bar.
class _RankingCard extends StatelessWidget {
  const _RankingCard({required this.demand});

  final Demand demand;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    if (demand.scoreBreakdown.isEmpty) {
      // Only open demand is ranked; funded work leaves the ranking (the API
      // returns no rank or breakdown for it).
      final funded =
          demand.status.isOnLifecycle &&
          !demand.status.isBefore(DemandStatus.funded);
      return JmCard(
        padding: const EdgeInsets.all(Insets.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              funded ? 'No longer in the ranking' : 'Not ranked yet',
              style: JanMaangTypography.titleLg.copyWith(
                color: scheme.onSurface,
              ),
            ),
            const SizedBox(height: Insets.xs),
            Text(
              funded
                  ? 'This problem has been funded, so it no longer competes '
                        'for funding in the district ranking.'
                  : 'This demand is still being verified and clustered. '
                        'Ranking happens once similar reports are merged.',
              style: JanMaangTypography.bodySm.copyWith(
                color: scheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
    }

    return JmCard(
      padding: const EdgeInsets.all(Insets.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  'Why is this ranked #${demand.rank}?',
                  style: JanMaangTypography.headlineSm.copyWith(
                    color: scheme.onSurface,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.info_outline, size: 20),
                color: scheme.onSurfaceVariant,
                tooltip: 'How ranking works',
                onPressed: () => _showMethodology(context),
              ),
            ],
          ),
          const SizedBox(height: Insets.md),
          for (final factor in demand.scoreBreakdown) ...<Widget>[
            JmMetricBar(
              label: factor.label,
              score: factor.score,
              explanation: factor.explanation,
            ),
            const SizedBox(height: Insets.md),
          ],
          // Ranking appeals are not connected to the live API yet.
          if (AppConfig.useMocks) ...<Widget>[
            const SizedBox(height: Insets.xs),
            OutlinedButton.icon(
              onPressed: () => context.pushNamed(
                AppRoute.questionRanking.name,
                pathParameters: <String, String>{'id': demand.id},
              ),
              icon: const Icon(Icons.gavel_outlined, size: 18),
              label: const Text('Question this ranking'),
            ),
          ],
        ],
      ),
    );
  }

  void _showMethodology(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        final scheme = Theme.of(context).colorScheme;
        return Padding(
          padding: const EdgeInsets.fromLTRB(
            Insets.lg,
            0,
            Insets.lg,
            Insets.xl,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'How ranking works',
                style: JanMaangTypography.headlineSm.copyWith(
                  color: scheme.onSurface,
                ),
              ),
              const SizedBox(height: Insets.sm),
              Text(
                'Every demand is scored on five public factors: how many people '
                'it affects, the infrastructure gap it leaves, the equity of '
                'past spending in that ward, how severe the failure is, and how '
                'long it has gone unaddressed.\n\n'
                'The weights are published and identical for every demand in '
                'the district. No official can move a demand up the list by '
                'hand — they can only fund down it.',
                style: JanMaangTypography.bodyMd.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _TimelineCard extends StatelessWidget {
  const _TimelineCard({required this.demand});

  final Demand demand;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return JmCard(
      padding: const EdgeInsets.all(Insets.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Status Timeline',
            style: JanMaangTypography.titleLg.copyWith(color: scheme.onSurface),
          ),
          const SizedBox(height: Insets.lg),
          if (demand.timeline.isEmpty)
            Text(
              'No status updates yet.',
              style: JanMaangTypography.bodySm.copyWith(
                color: scheme.onSurfaceVariant,
              ),
            )
          else
            JmTimeline(events: demand.timeline),
        ],
      ),
    );
  }
}

class _EvidenceThumbnail extends StatelessWidget {
  const _EvidenceThumbnail({required this.thumbnailUrl, required this.fullUrl});

  final String thumbnailUrl;
  final String fullUrl;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Open report photo',
      child: InkWell(
        borderRadius: BorderRadius.circular(Corners.base),
        onTap: () => showDialog<void>(
          context: context,
          builder: (context) => Dialog(
            child: InteractiveViewer(
              child: Image.network(
                fullUrl,
                fit: BoxFit.contain,
                errorBuilder: (_, _, _) => const Padding(
                  padding: EdgeInsets.all(Insets.lg),
                  child: Text('The photo could not load.'),
                ),
              ),
            ),
          ),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(Corners.base),
          child: Image.network(
            thumbnailUrl,
            width: 160,
            height: 120,
            fit: BoxFit.cover,
            errorBuilder: (_, _, _) => const SizedBox(
              width: 160,
              height: 120,
              child: Center(child: Text('Photo could not load.')),
            ),
          ),
        ),
      ),
    );
  }
}
