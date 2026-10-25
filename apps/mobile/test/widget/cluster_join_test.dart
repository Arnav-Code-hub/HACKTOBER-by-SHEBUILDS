import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/core/theme/app_theme.dart';
import 'package:janmaang/features/demands/data/demand_fixtures.dart';
import 'package:janmaang/features/demands/data/demands_repository_mock.dart';
import 'package:janmaang/features/demands/presentation/cluster_screen.dart';
import 'package:janmaang/features/demands/presentation/demand_providers.dart';

/// Answers a join with a fixed count, or fails the way the live API can.
class _JoinOutcome extends MockDemandsRepository {
  _JoinOutcome({this.failure});

  final Failure? failure;
  int calls = 0;

  @override
  Future<int> joinCluster(String clusterId) async {
    calls++;
    if (failure case final failure?) throw failure;
    return 5;
  }
}

Future<void> _pumpCluster(WidgetTester tester, _JoinOutcome repository) async {
  tester.view.physicalSize = const Size(900, 2600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  addTearDown(repository.dispose);
  // No signed-in user is provided: the API authenticates the join, so the
  // screen must not depend on one being loaded.
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        demandsRepositoryProvider.overrideWithValue(repository),
        clusterProvider.overrideWith(
          (ref, id) async => DemandFixtures.waterCluster,
        ),
      ],
      child: MaterialApp(
        theme: AppTheme.light,
        home: ClusterScreen(clusterId: DemandFixtures.waterCluster.id),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a recorded join reports the actual supporter count', (
    tester,
  ) async {
    final repository = _JoinOutcome();
    await _pumpCluster(tester, repository);

    await tester.tap(find.text('Join this demand'));
    await tester.pumpAndSettle();

    expect(repository.calls, 1);
    expect(
      find.text('Your support is recorded. 5 people support this demand.'),
      findsOneWidget,
    );
    expect(find.text('Voice added'), findsOneWidget);
    expect(find.textContaining('moved up'), findsNothing);
  });

  testWidgets('a refused join shows why and can be tried again', (
    tester,
  ) async {
    final repository = _JoinOutcome(
      failure: const ConflictFailure(
        'This repair is already awaiting or past citizen verification.',
      ),
    );
    await _pumpCluster(tester, repository);

    await tester.tap(find.text('Join this demand'));
    await tester.pumpAndSettle();

    expect(
      find.text(
        'This repair is already awaiting or past citizen verification.',
      ),
      findsOneWidget,
    );
    expect(find.text('Join this demand'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
