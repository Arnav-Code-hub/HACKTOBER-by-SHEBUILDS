import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:janmaang/core/config/app_config.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/core/routing/routes.dart';
import 'package:janmaang/core/theme/app_theme.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/demands/data/demand_fixtures.dart';
import 'package:janmaang/features/demands/data/http_demands_repository.dart';
import 'package:janmaang/features/demands/presentation/demand_detail_screen.dart';
import 'package:janmaang/features/demands/presentation/demand_providers.dart';
import 'package:janmaang/features/home/presentation/home_providers.dart';
import 'package:janmaang/features/home/presentation/home_screen.dart';
import 'package:janmaang/features/leaderboard/data/leaderboard_repository.dart';
import 'package:janmaang/features/leaderboard/presentation/leaderboard_screen.dart';
import 'package:janmaang/features/ledger/presentation/ledger_screen.dart';
import 'package:janmaang/features/map/presentation/map_controller.dart';
import 'package:janmaang/shared/widgets/jm_demo_notice.dart';

const citizen = AppUser(uid: 'mock-uid', displayName: 'Test citizen');

void main() {
  test(
    'community previews load without using the citizen reports API',
    () async {
      final requests = <http.Request>[];
      final api = ApiClient(
        baseUrl: 'http://localhost:8000',
        token: () async => 'test-token',
        client: MockClient((request) async {
          requests.add(request);
          return http.Response(
            jsonEncode(<String, Object?>{
              'items': <Object?>[
                {
                  'id': 'real-report',
                  'code': 'DEMO-0001',
                  'title': 'Saved report',
                  'reporter_id': 'mock-uid',
                  'category': 'water',
                  'severity': 'medium',
                  'status': 'reported',
                  'media': <Object?>[],
                  'created_at': '2026-10-25T08:00:00Z',
                },
              ],
            }),
            200,
          );
        }),
      );
      addTearDown(api.close);
      final container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(api),
          currentUserProvider.overrideWithValue(citizen),
        ],
      );
      addTearDown(container.dispose);
      container.listen(communityPulseProvider, (_, _) {});
      container.listen(nearbyDemandsProvider, (_, _) {});
      container.listen(ledgerEntriesProvider, (_, _) {});
      container.listen(ledgerSummaryProvider, (_, _) {});
      container.listen(leaderboardProvider, (_, _) {});
      final pulse = await container.read(communityPulseProvider.future);
      final nearby = await container.read(nearbyDemandsProvider.future);
      final ledger = await container.read(ledgerEntriesProvider.future);
      final summary = await container.read(ledgerSummaryProvider.future);
      final ranks = await container.read(leaderboardProvider.future);
      expect(pulse.activeDemands, greaterThan(0));
      expect(nearby, isNotEmpty);
      expect(ledger, hasLength(summary.projectsFunded));
      expect(
        summary.totalAllocated,
        ledger.fold<int>(0, (sum, e) => sum + e.amount),
      );
      expect(ranks, isNotEmpty);
      expect(container.read(allIssuesProvider), isNotEmpty);
      expect(requests, isEmpty);

      if (!AppConfig.useMocks) {
        expect(
          container.read(demandsRepositoryProvider),
          isA<HttpDemandsRepository>(),
        );
        container.listen(myDemandsProvider, (_, _) {});
        final mine = await container.read(myDemandsProvider.future);
        expect(mine.map((d) => d.id), ['real-report']);
        expect(requests.single.url.path, '/api/v1/reports');
        expect(requests.single.url.queryParameters['mine'], 'true');
        expect(requests.single.headers['authorization'], 'Bearer test-token');
      }
    },
  );

  Future<void> pump(WidgetTester tester, Widget screen) async {
    tester.view.physicalSize = const Size(430, 2600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authStateProvider.overrideWith(
            (ref) => Stream<AppUser?>.value(citizen),
          ),
        ],
        child: MaterialApp(theme: AppTheme.light, home: screen),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(seconds: 1));
  }

  testWidgets('Home restores pulse and nearby cards with a demo label', (
    tester,
  ) async {
    await pump(tester, const HomeScreen());
    expect(find.byType(JmDemoNotice), findsOneWidget);
    expect(find.text('Active demands'), findsOneWidget);
    expect(find.text('Near you'), findsOneWidget);
    expect(find.text('What does your community need?'), findsOneWidget);
    if (!AppConfig.useMocks) {
      expect(find.text('My saved reports'), findsOneWidget);
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('Ranks renders contributors and responds to period selection', (
    tester,
  ) async {
    await pump(tester, const LeaderboardScreen());
    expect(find.text('Demo data'), findsOneWidget);
    expect(find.text('Leaderboard'), findsOneWidget);
    expect(find.text('ALL CONTRIBUTORS'), findsOneWidget);
    expect(find.text('· you'), findsNothing);
    await tester.tap(find.text('This year'));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('ALL CONTRIBUTORS'), findsOneWidget);
    final container = ProviderScope.containerOf(
      tester.element(find.byType(LeaderboardScreen)),
    );
    expect(container.read(leaderboardPeriodProvider).name, 'year');
    expect(tester.takeException(), isNull);
  });

  testWidgets('Ledger resolves its totals and allocation rows', (tester) async {
    await pump(tester, const LedgerScreen());
    expect(find.text('Demo data'), findsOneWidget);
    expect(find.text('Streetlight Installation'), findsOneWidget);
    expect(find.text('Loading the ledger…'), findsNothing);
    expect(find.text('Totalling allocations…'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('sample details never offer verification or ranking writes', (
    tester,
  ) async {
    final sample = DemandFixtures.streetlightFixed.copyWith(
      awaitingVerification: true,
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authStateProvider.overrideWith(
            (ref) => Stream<AppUser?>.value(citizen),
          ),
          demoDemandProvider(sample.id).overrideWith((ref) async => sample),
        ],
        child: MaterialApp(
          theme: AppTheme.light,
          home: DemandDetailScreen(demandId: sample.id, preview: true),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('Demo data'), findsOneWidget);
    expect(find.text(sample.title), findsOneWidget);
    expect(find.text('Verify the repair'), findsNothing);
    expect(find.text('Question this ranking'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Home sample cards navigate to the preview in a live build', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(430, 3000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final target = AppConfig.useMocks
        ? AppRoute.demandDetail
        : AppRoute.demoDemandDetail;
    final router = GoRouter(
      initialLocation: '/home',
      routes: [
        GoRoute(path: '/home', builder: (_, _) => const HomeScreen()),
        GoRoute(
          path: target.path,
          name: target.name,
          builder: (_, state) => DemandDetailScreen(
            demandId: state.pathParameters['id']!,
            preview: !AppConfig.useMocks,
          ),
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authStateProvider.overrideWith(
            (ref) => Stream<AppUser?>.value(citizen),
          ),
        ],
        child: MaterialApp.router(theme: AppTheme.light, routerConfig: router),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(seconds: 1));
    final title = find.text(DemandFixtures.nearby.first.title);
    await tester.ensureVisible(title);
    await tester.tap(title);
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    await tester.pump(const Duration(seconds: 1));
    final detail = tester.widget<DemandDetailScreen>(
      find.byType(DemandDetailScreen),
    );
    expect(detail.demandId, DemandFixtures.nearby.first.id);
    expect(detail.preview, !AppConfig.useMocks);
    expect(find.text(DemandFixtures.nearby.first.code), findsWidgets);
    if (!AppConfig.useMocks) expect(find.text('Demo data'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
