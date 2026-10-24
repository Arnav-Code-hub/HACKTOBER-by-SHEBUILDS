import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/core/theme/app_theme.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/demands/domain/demand.dart';
import 'package:janmaang/features/demands/presentation/demand_detail_screen.dart';
import 'package:janmaang/features/demands/presentation/demand_providers.dart';
import 'package:janmaang/features/verification/data/http_verification_repository.dart'
    show staleVerificationMessage;
import 'package:janmaang/features/verification/domain/verification.dart';
import 'package:janmaang/features/verification/domain/verification_repository.dart';
import 'package:janmaang/features/verification/presentation/verify_screen.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

class FakeVerificationRepository implements VerificationRepository {
  FakeVerificationRepository(this.request, {this.submitError});
  final VerificationRequest request;
  final Failure? submitError;
  final submitted = <VerificationSubmission>[];
  int loads = 0;

  @override
  Future<VerificationRequest> getRequest(String demandId) async {
    loads++;
    return request;
  }

  @override
  Future<void> submit(VerificationSubmission submission, String uid) async {
    submitted.add(submission);
    if (submitError != null) throw submitError!;
  }

  @override
  Future<FieldAssignment> getAssignment(String assignmentId) =>
      throw UnimplementedError();

  @override
  Stream<List<FieldAssignment>> watchAssignments(String uid) =>
      throw UnimplementedError();
}

const reporter = AppUser(uid: 'local-user', displayName: 'Rajesh');

const openRequest = VerificationRequest(
  demandId: 'r1',
  demandTitle: 'Handpump not working',
  reportCode: 'YDG-WTR-0001',
  question: 'Is the water source working now?',
  workOrderId: 'w1',
  round: 2,
  beforePhotoUrl: 'https://res.cloudinary.com/d/before.jpg',
  reportedAgo: '2w ago',
  afterPhotoUrl: 'https://res.cloudinary.com/d/after.jpg',
  completedAgo: '1d ago',
  evidenceCardUrl: 'https://res.cloudinary.com/d/card.jpg',
);

Future<void> pumpScreen(
  WidgetTester tester,
  Widget screen,
  List<Override> overrides,
) async {
  tester.view.physicalSize = const Size(900, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: <Override>[
        authStateProvider.overrideWith(
          (ref) => Stream<AppUser?>.value(reporter),
        ),
        ...overrides,
      ],
      child: MaterialApp(theme: AppTheme.light, home: screen),
    ),
  );
  await tester.pumpAndSettle();
}

Demand demand({required String reporterId, required bool awaiting}) => Demand(
  id: 'r1',
  code: 'YDG-WTR-0001',
  title: 'Handpump not working',
  reporterId: reporterId,
  category: DemandCategory.water,
  severity: Severity.high,
  status: DemandStatus.inProgress,
  awaitingVerification: awaiting,
  createdAt: DateTime.utc(2026, 10, 11),
);

void main() {
  testWidgets(
    'shows before and after evidence, then records a confirmed verdict',
    (tester) async {
      final repository = FakeVerificationRepository(openRequest);
      await pumpScreen(tester, const VerifyScreen(demandId: 'r1'), <Override>[
        verificationRepositoryProvider.overrideWithValue(repository),
      ]);

      expect(find.text('BEFORE'), findsOneWidget);
      expect(find.text('AFTER'), findsOneWidget);
      expect(find.text('Officer photo · 1d ago'), findsOneWidget);
      expect(
        find.textContaining('they do not prove the repair'),
        findsOneWidget,
      );
      expect(find.text('Evidence card'), findsOneWidget);
      expect(find.textContaining('round 2'), findsOneWidget);

      await tester.enterText(find.byType(TextField), 'Dry again by evening.');
      await tester.ensureVisible(find.text('No, still broken'));
      await tester.tap(find.text('No, still broken'));
      await tester.pumpAndSettle();
      expect(find.textContaining('No new money is allocated'), findsOneWidget);
      expect(repository.submitted, isEmpty);

      await tester.tap(find.text('Confirm'));
      await tester.pumpAndSettle();
      final [verdict] = repository.submitted;
      expect(verdict.isFixed, isFalse);
      expect(verdict.workOrderId, 'w1');
      expect(verdict.round, 2);
      expect(verdict.note, 'Dry again by evening.');
    },
  );

  testWidgets('a stale round explains itself and reloads the latest evidence', (
    tester,
  ) async {
    final repository = FakeVerificationRepository(
      openRequest,
      submitError: const ConflictFailure(staleVerificationMessage),
    );
    await pumpScreen(tester, const VerifyScreen(demandId: 'r1'), <Override>[
      verificationRepositoryProvider.overrideWithValue(repository),
    ]);
    expect(repository.loads, 1);

    await tester.ensureVisible(find.text('Yes, it is fixed'));
    await tester.tap(find.text('Yes, it is fixed'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Confirm'));
    await tester.pumpAndSettle();

    expect(
      find.text('This repair was updated — reload to see the latest evidence'),
      findsOneWidget,
    );
    // Still on the screen: nothing was recorded, so it does not close.
    expect(find.text('Is the problem fixed?'), findsOneWidget);

    await tester.tap(find.text('Reload'));
    await tester.pumpAndSettle();
    expect(repository.loads, 2);
  });

  testWidgets('cancelling the confirmation records nothing', (tester) async {
    final repository = FakeVerificationRepository(openRequest);
    await pumpScreen(tester, const VerifyScreen(demandId: 'r1'), <Override>[
      verificationRepositoryProvider.overrideWithValue(repository),
    ]);
    await tester.ensureVisible(find.text('Yes, it is fixed'));
    await tester.tap(find.text('Yes, it is fixed'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(repository.submitted, isEmpty);
  });

  testWidgets('a citizen who cannot verify sees why, and no verdict buttons', (
    tester,
  ) async {
    const blocked = VerificationRequest(
      demandId: 'r1',
      demandTitle: 'Handpump not working',
      question: 'Is the water source working now?',
      workOrderId: 'w1',
      canVerify: false,
      blockedReason: 'Only the person who reported this can verify it.',
    );
    await pumpScreen(tester, const VerifyScreen(demandId: 'r1'), <Override>[
      verificationRepositoryProvider.overrideWithValue(
        FakeVerificationRepository(blocked),
      ),
    ]);
    expect(find.textContaining('Only the person'), findsOneWidget);
    expect(find.text('Yes, it is fixed'), findsNothing);
    expect(find.text('No, still broken'), findsNothing);
  });

  testWidgets('the report page asks only its reporter to verify', (
    tester,
  ) async {
    await pumpScreen(
      tester,
      const DemandDetailScreen(demandId: 'r1'),
      <Override>[
        demandProvider.overrideWith(
          (ref, id) async => demand(reporterId: 'local-user', awaiting: true),
        ),
      ],
    );
    expect(find.text('Verify the repair'), findsOneWidget);
  });

  testWidgets('another citizen viewing the report is not asked', (
    tester,
  ) async {
    await pumpScreen(
      tester,
      const DemandDetailScreen(demandId: 'r1'),
      <Override>[
        demandProvider.overrideWith(
          (ref, id) async => demand(reporterId: 'someone-else', awaiting: true),
        ),
      ],
    );
    expect(find.text('Verify the repair'), findsNothing);
  });
}
