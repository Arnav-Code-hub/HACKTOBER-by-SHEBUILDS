import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/config/app_config.dart';
import '../../../core/localization/app_strings.dart';
import '../../../core/providers.dart';
import '../../../core/routing/routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/janmaang_colors.dart';
import '../../../core/theme/janmaang_typography.dart';
import '../../../core/theme/motion.dart';
import '../../../shared/models/demand_enums.dart';
import '../../../shared/models/provenance.dart';
import '../../../shared/widgets/jm_featured_carousel.dart';
import '../../../shared/widgets/jm_demo_notice.dart';
import '../../../shared/widgets/jm_provenance_badge.dart';
import '../../../shared/widgets/jm_section_header.dart';
import '../../../shared/widgets/jm_states.dart';
import '../../../shared/widgets/jm_surfaces.dart';
import '../../demands/domain/demands_repository.dart';
import '../../demands/presentation/widgets/demand_list_card.dart';
import 'home_providers.dart';
import 'widgets/home_map_preview.dart';
import 'widgets/report_hero_card.dart';

/// Citizen Home.
///
/// Keeps the information architecture it always had — greeting, the hero
/// reporting card, Community Pulse, Near You, what gets built — and re-lays it
/// in the soft-surface language: a tinted page, white cards floating on it, a
/// four-colour tile grid for the pulse figures, and fully rounded rows for
/// everything navigable.
///
/// There is no app bar. The greeting *is* the header, which buys back a whole
/// bar's worth of vertical space on a phone and is the pattern the rest of the
/// product now follows.
///
/// The list scrolls edge to edge and each section supplies its own horizontal
/// padding, so a section can bleed to the screen edges while everything else
/// stays on the margin.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  static const _gutter = EdgeInsets.symmetric(horizontal: Insets.marginMobile);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final strings = AppStrings.of(context);
    final pulse = ref.watch(communityPulseProvider);
    final nearby = ref.watch(nearbyDemandsProvider);
    final isWide = MediaQuery.sizeOf(context).width >= Breakpoints.medium;

    final name = user?.greetingName ?? '';
    final place = user?.locationLabel.isNotEmpty == true
        ? user!.locationLabel
        : '${AppConfig.defaultDistrict}, ${AppConfig.defaultState}';

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(communityPulseProvider);
            ref.invalidate(nearbyDemandsProvider);
            await ref.read(communityPulseProvider.future);
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            // navClearance keeps the last element clear of the floating
            // navigation bar, which the shell draws over the body.
            padding: const EdgeInsets.only(
              top: Insets.md,
              bottom: Insets.navClearance,
            ),
            children: <Widget>[
              Padding(
                padding: _gutter,
                child: JmEnter(
                  child: JmGreetingHeader(
                    greeting: name.isEmpty
                        ? strings.text('namaste')
                        : '${strings.text('namaste')}, $name',
                    subtitle: place,
                    initials: _initials(name),
                    hasUnread: AppConfig.useMocks,
                    onAvatarTap: () => context.pushNamed(AppRoute.profile.name),
                    onNotifications: () =>
                        context.pushNamed(AppRoute.profile.name),
                  ),
                ),
              ),
              const SizedBox(height: Insets.md),

              if (!AppConfig.useMocks) ...<Widget>[
                Padding(
                  padding: _gutter,
                  child: JmPillRow(
                    title: strings.text('saved_reports'),
                    subtitle: strings.text('saved_reports_help'),
                    icon: Icons.track_changes,
                    tint: JmTint.blue,
                    onTap: () => context.goNamed(AppRoute.track.name),
                  ),
                ),
                const SizedBox(height: Insets.md),
              ],
              const Padding(
                padding: _gutter,
                child: JmDemoNotice(
                  message:
                      'Community figures, nearby reports and maps are '
                      'sample data for Yadgir. Use Report and Track for '
                      'your own reports.',
                ),
              ),
              const SizedBox(height: Insets.md),
              JmEnter(index: 1, child: const _FeaturedStrip()),
              const SizedBox(height: Insets.md),
              JmEnter(index: 2, child: const _CategoryScroller()),
              const SizedBox(height: Insets.lg),

              Padding(
                padding: _gutter,
                // Deliberately not IntrinsicHeight: the pulse panel contains a
                // shrink-wrapped GridView, and a viewport cannot report an
                // intrinsic height. Top-aligning the two columns gives the same
                // bento reading without asking for a measurement Flutter cannot
                // provide.
                child: isWide
                    ? Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Expanded(
                            flex: 8,
                            child: JmEnter(
                              index: 3,
                              child: ReportHeroCard(
                                onStartReport: (c) => _startReport(context, c),
                              ),
                            ),
                          ),
                          const SizedBox(width: Insets.md),
                          Expanded(
                            flex: 5,
                            child: JmEnter(
                              index: 4,
                              child: _CommunityPulse(
                                pulse: pulse,
                                strings: strings,
                              ),
                            ),
                          ),
                        ],
                      )
                    : Column(
                        children: <Widget>[
                          JmEnter(
                            index: 3,
                            child: ReportHeroCard(
                              onStartReport: (c) => _startReport(context, c),
                            ),
                          ),
                          const SizedBox(height: Insets.lg),
                          JmEnter(
                            index: 4,
                            child: _CommunityPulse(
                              pulse: pulse,
                              strings: strings,
                            ),
                          ),
                        ],
                      ),
              ),

              const SizedBox(height: Insets.lg),

              Padding(
                padding: _gutter,
                child: JmSectionHeader(
                  title: strings.text('near_you'),
                  icon: Icons.near_me_outlined,
                  actionLabel: 'Demo map',
                  onAction: () => context.pushNamed(AppRoute.map.name),
                ),
              ),
              const SizedBox(height: Insets.md),

              Padding(
                padding: _gutter,
                child: JmEnter(
                  index: 5,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(Corners.lg),
                    child: SizedBox(
                      height: 190,
                      child: HomeMapPreview(
                        onTap: () => context.pushNamed(AppRoute.map.name),
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: Insets.md),

              Padding(
                padding: _gutter,
                child: nearby.when(
                  loading: () => const JmSkeletonList(count: 3, itemHeight: 88),
                  error: (error, _) => JmErrorView(
                    error: error,
                    onRetry: () => ref.invalidate(nearbyDemandsProvider),
                  ),
                  data: (demands) {
                    if (demands.isEmpty) {
                      return JmEmptyState(
                        icon: Icons.explore_off_outlined,
                        title: strings.text('nothing_nearby'),
                        message: strings.text('be_first'),
                        actionLabel: strings.text('report_a_need'),
                        onAction: () =>
                            _startReport(context, ReportChannel.voice),
                      );
                    }
                    return Column(
                      children: <Widget>[
                        for (var i = 0; i < demands.length; i++) ...<Widget>[
                          JmEnter(
                            index: 6 + i,
                            child: DemandListCard(
                              demand: demands[i],
                              onTap: () => context.pushNamed(
                                AppConfig.useMocks
                                    ? AppRoute.demandDetail.name
                                    : AppRoute.demoDemandDetail.name,
                                pathParameters: <String, String>{
                                  'id': demands[i].id,
                                },
                              ),
                            ),
                          ),
                          const SizedBox(height: Insets.sm + Insets.xs),
                        ],
                      ],
                    );
                  },
                ),
              ),

              const SizedBox(height: Insets.lg),

              // The two places a curious citizen goes next. Rows rather than a
              // link and a button, so they read as destinations.
              Padding(
                padding: _gutter,
                child: Column(
                  children: <Widget>[
                    JmEnter(
                      index: 10,
                      child: JmPillRow(
                        title: strings.text('money_goes'),
                        subtitle: strings.text('every_allocation'),
                        icon: Icons.account_balance_wallet_outlined,
                        tint: JmTint.green,
                        onTap: () => context.goNamed(AppRoute.ledger.name),
                      ),
                    ),
                    const SizedBox(height: Insets.sm + Insets.xs),
                    JmEnter(
                      index: 11,
                      child: JmPillRow(
                        title: strings.text('methodology'),
                        subtitle: strings.text('figures_built'),
                        icon: Icons.science_outlined,
                        tint: JmTint.blue,
                        onTap: () => context.pushNamed(AppRoute.method.name),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: Insets.lg),
              const Padding(padding: _gutter, child: _HomeFooter()),
            ],
          ),
        ),
      ),
    );
  }

  /// Up to two letters for the avatar.
  static String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'))
      ..removeWhere((p) => p.isEmpty);
    if (parts.isEmpty) return '';
    if (parts.length == 1) {
      return parts.first.characters.take(1).toString().toUpperCase();
    }
    return (parts.first.characters.take(1).toString() +
            parts.last.characters.take(1).toString())
        .toUpperCase();
  }

  void _startReport(BuildContext context, ReportChannel channel) {
    context.pushNamed(
      AppRoute.report.name,
      queryParameters: <String, String>{'channel': channel.name},
    );
  }
}

/// The photography, full-bleed and high on the page.
///
/// It opens the dashboard with the thing the whole platform is pointed at — a
/// road, a water connection, a transit line — before a single figure appears.
class _FeaturedStrip extends StatelessWidget {
  const _FeaturedStrip();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: HomeScreen._gutter,
      child: JmFeaturedCarousel(height: 168),
    );
  }
}

/// A horizontal run of the reporting categories.
///
/// Gives the dashboard somewhere to go that is not a list, and gives a citizen
/// who already knows what is wrong a one-tap route into the map filtered to
/// that category. Scrolls past the gutter deliberately.
class _CategoryScroller extends StatelessWidget {
  const _CategoryScroller();

  /// The six a citizen actually reports. `other` is deliberately absent — it
  /// is a fallback for classification, not something anyone goes looking for.
  static const _shown = <(DemandCategory, JmTint)>[
    (DemandCategory.water, JmTint.blue),
    (DemandCategory.roads, JmTint.clay),
    (DemandCategory.lighting, JmTint.amber),
    (DemandCategory.sanitation, JmTint.green),
    (DemandCategory.electricity, JmTint.orchid),
    (DemandCategory.transport, JmTint.navy),
  ];

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;

    return SizedBox(
      height: 92,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: Insets.marginMobile),
        itemCount: _shown.length,
        separatorBuilder: (_, _) =>
            const SizedBox(width: Insets.sm + Insets.xs),
        itemBuilder: (context, i) {
          final (category, tint) = _shown[i];
          return Semantics(
            button: true,
            label: '${category.label} reports',
            excludeSemantics: true,
            child: Material(
              color: tint.background(brightness),
              borderRadius: BorderRadius.circular(Corners.lg),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => context.pushNamed(AppRoute.map.name),
                child: SizedBox(
                  width: 84,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: <Widget>[
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: tint.well(brightness),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          category.icon,
                          size: 19,
                          color: tint.foreground(brightness),
                        ),
                      ),
                      const SizedBox(height: Insets.sm - 2),
                      Text(
                        category.label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: JanMaangTypography.withWeight(
                          JanMaangTypography.caption,
                          FontWeight.w700,
                        ).copyWith(color: tint.foreground(brightness)),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

/// The 2×2 impact grid.
///
/// Four figures, four colours, four icons. Colour sorts them at a glance and
/// the icons carry the same sorting for anyone the colour does not reach.
class _CommunityPulse extends StatelessWidget {
  const _CommunityPulse({required this.pulse, required this.strings});

  final AsyncValue<CommunityPulse> pulse;
  final AppStrings strings;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        JmSectionHeader(
          title: strings.text('community_pulse'),
          icon: Icons.insights_outlined,
        ),
        const SizedBox(height: Insets.md),
        pulse.when(
          loading: () => const JmSkeletonList(count: 2, itemHeight: 86),
          error: (error, _) =>
              SizedBox(height: 200, child: JmErrorView(error: error)),
          data: (data) => GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisSpacing: Insets.sm + Insets.xs,
            mainAxisSpacing: Insets.sm + Insets.xs,
            childAspectRatio: 1.62,
            children: <Widget>[
              JmTintTile(
                value: data.activeDemands,
                label: strings.text('active_demands'),
                icon: Icons.campaign_outlined,
                tint: JmTint.navy,
              ),
              JmTintTile(
                value: data.peopleAffected,
                label: strings.text('people_affected'),
                icon: Icons.groups_outlined,
                tint: JmTint.blue,
              ),
              JmTintTile(
                value: data.underReview,
                label: strings.text('under_review'),
                icon: Icons.hourglass_top_outlined,
                tint: JmTint.amber,
              ),
              JmTintTile(
                value: data.funded,
                label: strings.text('funded'),
                icon: Icons.verified_outlined,
                tint: JmTint.green,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Closing line, plus the provenance stamp.
///
/// The figures above are modelled, and saying so here — rather than in a
/// footnote nobody opens — is the point.
class _HomeFooter extends StatelessWidget {
  const _HomeFooter();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Column(
      children: <Widget>[
        Text(
          'Every demand is public. Every rupee is traceable.',
          textAlign: TextAlign.center,
          style: JanMaangTypography.bodySm.copyWith(
            color: scheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Insets.sm + Insets.xs),
        const JmProvenanceBadge(
          stamp: ProvenanceStamp(
            provenance: Provenance.syntheticRural,
            precision: LocationPrecision.approximateCentroid,
          ),
        ),
      ],
    );
  }
}
