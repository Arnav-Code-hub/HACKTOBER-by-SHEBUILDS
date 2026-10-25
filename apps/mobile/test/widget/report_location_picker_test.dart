import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/core/services/location_service.dart';
import 'package:janmaang/core/theme/app_theme.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/report/presentation/report_controller.dart';
import 'package:janmaang/features/report/presentation/report_screen.dart';
import 'package:janmaang/features/report/presentation/widgets/report_location_picker.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

class DeniedLocationService extends LocationService {
  int calls = 0;
  @override
  Future<ResolvedPosition> currentPosition() async {
    calls++;
    throw const PermissionFailure('Device location denied.');
  }
}

void main() {
  testWidgets('no report location is assumed before a map tap', (tester) async {
    await tester.pumpWidget(
      MaterialApp(theme: AppTheme.light, home: const ReportLocationPicker()),
    );
    await tester.pump();
    final use = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Use this location'),
    );
    expect(use.onPressed, isNull);
    expect(
      find.text('No location selected. Tap the map to choose.'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('manual pin returns to the report without calling device GPS', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(430, 1600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final gps = DeniedLocationService();
    final container = ProviderContainer(
      overrides: [
        currentUserProvider.overrideWithValue(
          const AppUser(uid: 'test-citizen'),
        ),
        locationServiceProvider.overrideWithValue(gps),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: AppTheme.light,
          home: const ReportScreen(channel: ReportChannel.text),
        ),
      ),
    );
    await tester.pump();
    await tester.tap(find.text('Select on Map'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byType(ReportLocationPicker), findsOneWidget);
    expect(gps.calls, 0);
    await tester.tapAt(tester.getCenter(find.byType(FlutterMap)));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.text('Use this location'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    final draft = container.read(reportControllerProvider).draft;
    expect(draft.hasLocation, isTrue);
    expect(draft.latitude, closeTo(16.76, 0.01));
    expect(draft.longitude, closeTo(77.14, 0.01));
    expect(draft.locationLabel, startsWith('Map pin:'));
    expect(gps.calls, 0);
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byType(ReportLocationPicker), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'cancelling manual pinning preserves the existing report location',
    (tester) async {
      tester.view.physicalSize = const Size(430, 1600);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      final container = ProviderContainer(
        overrides: [
          currentUserProvider.overrideWithValue(
            const AppUser(uid: 'test-citizen'),
          ),
        ],
      );
      addTearDown(container.dispose);
      container.listen(reportControllerProvider, (_, _) {});
      container
          .read(reportControllerProvider.notifier)
          .setLocation(
            latitude: 16.77,
            longitude: 77.15,
            label: 'Existing selected point',
          );
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            theme: AppTheme.light,
            home: const ReportScreen(channel: ReportChannel.text),
          ),
        ),
      );
      await tester.pump();
      await tester.tap(find.text('Select on Map'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(find.text('16.77000, 77.15000'), findsOneWidget);
      await tester.tapAt(
        tester.getCenter(find.byType(FlutterMap)) + const Offset(40, 40),
      );
      await tester.pump();
      await tester.tap(find.byTooltip('Back').hitTestable());
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      final draft = container.read(reportControllerProvider).draft;
      expect(draft.latitude, 16.77);
      expect(draft.longitude, 77.15);
      expect(draft.locationLabel, 'Existing selected point');
      expect(tester.takeException(), isNull);
    },
  );

  test('manual pinning clears an earlier GPS error', () {
    final container = ProviderContainer(
      overrides: [
        currentUserProvider.overrideWithValue(
          const AppUser(uid: 'test-citizen'),
        ),
      ],
    );
    addTearDown(container.dispose);
    container.listen(reportControllerProvider, (_, _) {});
    final controller = container.read(reportControllerProvider.notifier);
    controller.showFailure(const PermissionFailure('Device location denied.'));
    controller.setLocation(
      latitude: 16.76,
      longitude: 77.14,
      label: 'Manual point',
    );
    expect(container.read(reportControllerProvider).error, isNull);
    expect(container.read(reportControllerProvider).draft.hasLocation, isTrue);
  });
}
