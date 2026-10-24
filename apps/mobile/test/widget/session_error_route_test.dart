import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmaang/app.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/core/routing/routes.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/auth/presentation/session_error_screen.dart';
import 'package:janmaang/features/onboarding/presentation/onboarding_screen.dart';
import 'package:janmaang/features/splash/presentation/splash_screen.dart';

void main() {
  setUp(() {
    SplashGate.completed = false;
    SplashGate.intended = null;
  });

  testWidgets(
    'an unconfirmed restored session shows the error, not onboarding',
    (tester) async {
      tester.view.physicalSize = const Size(900, 2200);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            authStateProvider.overrideWith(
              (ref) => Stream<AppUser?>.error(
                const NetworkFailure(
                  'The server is starting up or unreachable. Retry in a minute.',
                ),
              ),
            ),
          ],
          child: const JanMaangApp(),
        ),
      );
      await tester.pump();
      await tester.pump(
        SplashScreen.duration + const Duration(milliseconds: 100),
      );
      await tester.pump(const Duration(seconds: 1));
      await tester.pump(const Duration(seconds: 1));

      expect(find.byType(SessionErrorScreen), findsOneWidget);
      expect(find.byType(OnboardingScreen), findsNothing);
      expect(find.textContaining('starting up or unreachable'), findsOneWidget);
      expect(find.text('Sign out'), findsOneWidget);
    },
  );
}
