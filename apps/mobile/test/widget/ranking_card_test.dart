import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/core/theme/app_theme.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/demands/domain/demand.dart';
import 'package:janmaang/features/demands/presentation/demand_detail_screen.dart';
import 'package:janmaang/features/demands/presentation/demand_providers.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

Future<void> pumpDetail(WidgetTester tester, DemandStatus status) async {
  tester.view.physicalSize = const Size(900, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authStateProvider.overrideWith(
          (ref) => Stream<AppUser?>.value(const AppUser(uid: 'local-user')),
        ),
        demandProvider.overrideWith(
          (ref, id) async => Demand(
            id: 'r1',
            code: 'JM-1',
            title: 'Handpump not working',
            reporterId: 'local-user',
            category: DemandCategory.water,
            severity: Severity.high,
            status: status,
            createdAt: DateTime.utc(2026, 10, 11),
          ),
        ),
      ],
      child: MaterialApp(
        theme: AppTheme.light,
        home: const DemandDetailScreen(demandId: 'r1'),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('an unranked report still being clustered says so', (
    tester,
  ) async {
    await pumpDetail(tester, DemandStatus.verified);
    expect(find.text('Not ranked yet'), findsOneWidget);
  });

  for (final status in <DemandStatus>[
    DemandStatus.funded,
    DemandStatus.inProgress,
    DemandStatus.citizenVerified,
  ]) {
    testWidgets('a ${status.name} report explains it left the ranking', (
      tester,
    ) async {
      await pumpDetail(tester, status);
      expect(find.text('No longer in the ranking'), findsOneWidget);
      expect(find.textContaining('still being verified'), findsNothing);
    });
  }
}
