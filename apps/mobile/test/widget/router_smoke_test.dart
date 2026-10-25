import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmaang/app.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/core/routing/routes.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/splash/presentation/splash_screen.dart';

/// Boots the real app — router, shell, bottom navigation and all — signed in.
///
/// Screens can build perfectly in isolation and still fail inside the shell,
/// so this exercises the tree the user actually gets.
void main() {
  const citizen = AppUser(
    uid: 'mock-uid',
    displayName: 'Rajesh',
    district: 'Yadgir',
    state: 'Karnataka',
    ward: 'Ward 4',
  );

  // SplashGate is process-wide: without resetting it, whichever test runs
  // second would skip the splash and exercise a different path.
  setUp(() {
    SplashGate.completed = false;
    SplashGate.intended = null;
  });

  Future<void> boot(
    WidgetTester tester, {
    Size size = const Size(900, 2200),
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authStateProvider.overrideWith(
            (ref) => Stream<AppUser?>.value(citizen),
          ),
        ],
        child: const JanMaangApp(),
      ),
    );
    await tester.pump();
    // Cold start lands on the splash, which runs a staged reveal before handing
    // over to the router. Pump past it, then let the shell's route transition
    // finish — not pumpAndSettle, because Home animates continuously.
    await tester.pump(
      SplashScreen.duration + const Duration(milliseconds: 100),
    );
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
  }

  testWidgets('lands on Home inside the shell, with all five destinations', (
    tester,
  ) async {
    await boot(tester);

    expect(tester.takeException(), isNull);
    for (final label in <String>[
      'Home',
      'Track',
      'Report',
      'Ranks',
      'Ledger',
    ]) {
      expect(find.text(label), findsWidgets, reason: '$label destination');
    }

    // Home's own content, not just the chrome around it.
    expect(find.text('What does your community need?'), findsOneWidget);
  });

  testWidgets('renders on a narrow phone too', (tester) async {
    await boot(tester, size: const Size(390, 2200));

    expect(tester.takeException(), isNull);
    expect(find.text('What does your community need?'), findsOneWidget);
  });
}
