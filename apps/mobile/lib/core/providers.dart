import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';

import 'config/app_config.dart';
import 'network/api_client.dart';
import '../features/auth/data/firebase_auth_repository.dart';
import '../features/demands/data/http_demands_repository.dart';
import '../features/report/data/http_report_repository.dart';
import '../features/verification/data/http_verification_repository.dart';

import '../features/auth/data/auth_repository_mock.dart';
import '../features/auth/domain/app_user.dart';
import '../features/auth/domain/auth_repository.dart';
import '../features/demands/data/demands_repository_mock.dart';
import '../features/demands/domain/demands_repository.dart';
import '../features/ledger/data/ledger_repository_mock.dart';
import '../features/ledger/domain/ledger_repository.dart';
import '../features/report/data/report_repository_mock.dart';
import '../features/report/domain/report_repository.dart';
import '../features/verification/data/verification_repository_mock.dart';
import '../features/verification/domain/verification_repository.dart';

/// Auth and reporting use the selected mode. Community previews have a separate
/// demo store so browsing examples never replaces a citizen's live records.

final apiClientProvider = Provider<ApiClient>((ref) {
  final client = ApiClient(
    baseUrl: AppConfig.apiBaseUrl,
    token: () async => FirebaseAuth.instance.currentUser?.getIdToken(),
  );
  ref.onDispose(client.close);
  return client;
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  if (!AppConfig.useMocks) {
    return FirebaseAuthRepository(
      FirebaseAuth.instance,
      ref.watch(apiClientProvider),
    );
  }
  final repository = MockAuthRepository();
  ref.onDispose(repository.dispose);
  return repository;
});

final demoDemandsRepositoryProvider = Provider<MockDemandsRepository>((ref) {
  final repository = MockDemandsRepository();
  ref.onDispose(repository.dispose);
  return repository;
});

final demandsRepositoryProvider = Provider<DemandsRepository>((ref) {
  if (!AppConfig.useMocks) {
    return HttpDemandsRepository(ref.watch(apiClientProvider));
  }
  return ref.watch(demoDemandsRepositoryProvider);
});

final reportRepositoryProvider = Provider<ReportRepository>((ref) {
  if (!AppConfig.useMocks) {
    final repository = HttpReportRepository(ref.watch(apiClientProvider));
    ref.onDispose(repository.close);
    return repository;
  }
  final demands = ref.watch(demandsRepositoryProvider);
  // Demo submission updates the same in-memory demand list shown by the UI.
  if (demands is MockDemandsRepository) return MockReportRepository(demands);
  throw StateError(
    'reportRepositoryProvider must be overridden when Firebase is enabled.',
  );
});

final verificationRepositoryProvider = Provider<VerificationRepository>(
  (ref) => AppConfig.useMocks
      ? MockVerificationRepository()
      : HttpVerificationRepository(ref.watch(apiClientProvider)),
);

final ledgerRepositoryProvider = Provider<LedgerRepository>(
  (ref) => MockLedgerRepository(),
);

/// The signed-in citizen, or null. Drives the router's auth redirect.
final authStateProvider = StreamProvider<AppUser?>(
  (ref) => ref.watch(authRepositoryProvider).authStateChanges(),
  // No automatic retry: each attempt waits on the API wake-up and profile
  // call. The session-error screen offers an explicit Retry instead.
  retry: (_, _) => null,
);

/// Convenience read of the current user; null while signed out.
final currentUserProvider = Provider<AppUser?>(
  (ref) => ref.watch(authStateProvider).value,
);
