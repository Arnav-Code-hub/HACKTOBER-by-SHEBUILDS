import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_auth/firebase_auth.dart';

import 'config/app_config.dart';
import 'network/api_client.dart';
import 'network/unavailable_repositories.dart';
import '../features/auth/data/firebase_auth_repository.dart';
import '../features/demands/data/http_demands_repository.dart';
import '../features/report/data/http_report_repository.dart';

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

/// Composition root. The compile-time mode selects labelled demo stores or
/// Firebase Auth + authenticated HTTP. Unfinished live features fail explicitly.

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

final demandsRepositoryProvider = Provider<DemandsRepository>((ref) {
  if (!AppConfig.useMocks) {
    return HttpDemandsRepository(ref.watch(apiClientProvider));
  }
  final repository = MockDemandsRepository();
  ref.onDispose(repository.dispose);
  return repository;
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
      : UnavailableVerificationRepository(),
);

final ledgerRepositoryProvider = Provider<LedgerRepository>(
  (ref) => AppConfig.useMocks
      ? MockLedgerRepository()
      : UnavailableLedgerRepository(),
);

/// The signed-in citizen, or null. Drives the router's auth redirect.
final authStateProvider = StreamProvider<AppUser?>(
  (ref) => ref.watch(authRepositoryProvider).authStateChanges(),
);

/// Convenience read of the current user; null while signed out.
final currentUserProvider = Provider<AppUser?>(
  (ref) => ref.watch(authStateProvider).value,
);
