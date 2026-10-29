import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/app_config.dart';
import '../../../core/localization/app_strings.dart';
import '../../../core/providers.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/janmaang_typography.dart';
import '../../../shared/widgets/jm_app_bar.dart';
import '../../../shared/widgets/jm_card.dart';
import '../data/notification_repository.dart';
import '../domain/notification_item.dart';

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  late final NotificationRepository _repository;
  late Future<NotificationPage> _page;

  @override
  void initState() {
    super.initState();
    _repository = NotificationRepository(ref.read(apiClientProvider));
    // Demo mode has no API session; never show it as a failed load.
    _page = AppConfig.useMocks
        ? Future<NotificationPage>.value(NotificationPage.empty)
        : _repository.load();
  }

  void _reload() => setState(() => _page = _repository.load());

  Future<void> _markRead(String id) async {
    try {
      await _repository.markRead(id);
      if (mounted) _reload();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppStrings.of(context).text('notifications_error')),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final scheme = Theme.of(context).colorScheme;
    if (AppConfig.useMocks) {
      return Scaffold(
        appBar: JmAppBar.task(title: strings.text('notifications_inbox')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(Insets.lg),
            child: Text(
              strings.text('notifications_demo'),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }
    return Scaffold(
      appBar: JmAppBar.task(title: strings.text('notifications_inbox')),
      body: FutureBuilder<NotificationPage>(
        future: _page,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(Insets.lg),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(strings.text('notifications_error')),
                    const SizedBox(height: Insets.md),
                    OutlinedButton(
                      onPressed: _reload,
                      child: Text(strings.text('notifications_retry')),
                    ),
                  ],
                ),
              ),
            );
          }
          final page = snapshot.data!;
          if (page.items.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(Insets.lg),
                child: Text(
                  strings.text('notifications_empty'),
                  style: JanMaangTypography.bodyMd.copyWith(
                    color: scheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: ListView.separated(
              padding: const EdgeInsets.all(Insets.marginMobile),
              itemCount: page.items.length,
              separatorBuilder: (context, index) =>
                  const SizedBox(height: Insets.sm),
              itemBuilder: (context, index) => _NotificationCard(
                item: page.items[index],
                onMarkRead: page.items[index].isRead
                    ? null
                    : () => _markRead(page.items[index].id),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _NotificationCard extends StatelessWidget {
  const _NotificationCard({required this.item, required this.onMarkRead});

  final NotificationItem item;
  final VoidCallback? onMarkRead;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final strings = AppStrings.of(context);
    final stamp = MaterialLocalizations.of(context)
        .formatShortDate(item.createdAt.toLocal());
    return JmCard(
      padding: const EdgeInsets.all(Insets.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  item.title,
                  style: JanMaangTypography.titleLg.copyWith(
                    color: scheme.onSurface,
                  ),
                ),
              ),
              if (!item.isRead)
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: scheme.primary,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
          const SizedBox(height: Insets.xs),
          Text(
            item.body,
            style: JanMaangTypography.bodyMd.copyWith(
              color: scheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: Insets.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  stamp,
                  style: JanMaangTypography.bodySm.copyWith(
                    color: scheme.onSurfaceVariant,
                  ),
                ),
              ),
              if (onMarkRead != null)
                TextButton(
                  onPressed: onMarkRead,
                  child: Text(strings.text('notification_mark_read')),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
