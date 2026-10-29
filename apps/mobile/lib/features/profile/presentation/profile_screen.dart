import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/providers.dart';
import '../../../core/localization/app_strings.dart';
import '../../../core/routing/routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/janmaang_typography.dart';
import '../../../shared/widgets/app_language_selector.dart';
import '../../../shared/widgets/jm_app_bar.dart';
import '../../../shared/widgets/jm_card.dart';
import '../../../shared/widgets/jm_logo.dart';
import '../../../shared/widgets/jm_status_chip.dart';
import '../../auth/presentation/auth_controller.dart';

/// Profile and settings. Built from the side-nav footer of the Stitch console
/// (profile chip, Settings, Support) reworked for a mobile screen.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final user = ref.watch(currentUserProvider);
    final strings = AppStrings.of(context);

    return Scaffold(
      appBar: JmAppBar.task(title: strings.text('profile')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
          Insets.marginMobile,
          Insets.lg,
          Insets.marginMobile,
          Insets.xl,
        ),
        children: <Widget>[
          JmCard(
            padding: const EdgeInsets.all(Insets.lg),
            child: Row(
              children: <Widget>[
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: scheme.primaryContainer,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.person,
                    size: 28,
                    color: scheme.onPrimaryContainer,
                  ),
                ),
                const SizedBox(width: Insets.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        user?.displayName ?? strings.text('citizen'),
                        style: JanMaangTypography.titleLg.copyWith(
                          color: scheme.onSurface,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        user?.phoneNumber ?? user?.email ?? '',
                        style: JanMaangTypography.bodySm.copyWith(
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                      if (user?.aadhaarVerified ?? false) ...<Widget>[
                        const SizedBox(height: Insets.sm),
                        const JmStatusChip(
                          label: 'HIGH TRUST',
                          tone: JmTone.success,
                          icon: Icons.verified_user,
                          dense: true,
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: Insets.md),

          if (user?.locationLabel.isNotEmpty ?? false)
            _Tile(
              icon: Icons.location_on_outlined,
              title: strings.text('reporting_from'),
              subtitle:
                  '${user!.locationLabel}${user.ward.isEmpty ? '' : ' • ${user.ward}'}',
            ),
          _Tile(
            icon: Icons.fact_check_outlined,
            title: strings.text('field_verification'),
            subtitle: strings.text('field_verification_help'),
            onTap: () => context.pushNamed(
              AppRoute.fieldVerification.name,
              pathParameters: <String, String>{'id': 'assignment-1'},
            ),
          ),
          _Tile(
            icon: Icons.notifications_outlined,
            title: strings.text('notifications'),
            subtitle: strings.text('notifications_inbox'),
            onTap: () => context.pushNamed(AppRoute.notifications.name),
          ),
          _Tile(
            icon: Icons.help_outline,
            title: strings.text('support'),
            subtitle: strings.text('support_help'),
          ),
          const SizedBox(height: Insets.md),
          const AppLanguageSelector(),
          const SizedBox(height: Insets.lg),

          const SizedBox(height: Insets.lg),
          Center(child: JmLogo.full(width: 200)),
          const SizedBox(height: Insets.lg),

          OutlinedButton.icon(
            onPressed: () async {
              await ref.read(authControllerProvider.notifier).signOut();
              if (context.mounted) context.goNamed(AppRoute.onboarding.name);
            },
            icon: const Icon(Icons.logout, size: 18),
            label: Text(strings.text('sign_out')),
          ),
        ],
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: Insets.sm),
      child: JmCard(
        onTap: onTap,
        radius: Corners.base,
        child: Row(
          children: <Widget>[
            Icon(icon, size: 20, color: scheme.onSurfaceVariant),
            const SizedBox(width: Insets.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    title,
                    style: JanMaangTypography.bodyMd.copyWith(
                      color: scheme.onSurface,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: JanMaangTypography.bodySm.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            if (onTap != null)
              Icon(
                Icons.chevron_right,
                size: 20,
                color: scheme.onSurfaceVariant,
              ),
          ],
        ),
      ),
    );
  }
}
