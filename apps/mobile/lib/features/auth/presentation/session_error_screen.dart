import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/providers.dart';
import '../../../shared/widgets/jm_states.dart';

/// Shown when a restored Firebase session cannot be confirmed by the API —
/// a sleeping or unreachable server, an unprovisioned account, or a staff
/// account in the citizen app. Never silently treated as "signed out".
class SessionErrorScreen extends ConsumerWidget {
  const SessionErrorScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final error = ref.watch(authStateProvider).error;
    return Scaffold(
      body: SafeArea(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            JmErrorView(
              title: 'We could not confirm your account',
              error: error ?? 'Unknown error',
              // Resubscribing replays the current Firebase user, which
              // requests the profile again.
              onRetry: () => ref.invalidate(authStateProvider),
            ),
            TextButton(
              onPressed: () => ref.read(authRepositoryProvider).signOut(),
              child: const Text('Sign out'),
            ),
          ],
        ),
      ),
    );
  }
}
