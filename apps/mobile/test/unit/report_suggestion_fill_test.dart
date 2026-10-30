import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/report/domain/report_draft.dart';
import 'package:janmaang/features/report/domain/report_repository.dart';
import 'package:janmaang/features/report/presentation/report_controller.dart';
import 'package:janmaang/shared/models/demand_enums.dart';

class _Suggesting implements ReportRepository {
  @override
  Future<ReportAnalysis> analyze({
    required String transcript,
    List<String> photoPaths = const <String>[],
  }) async => const ReportAnalysis(
    category: DemandCategory.water,
    severity: Severity.high,
    title: 'Broken handpump in ward 4',
    mentionedLocation: 'ward 4',
  );

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

ProviderContainer _container() {
  final container = ProviderContainer(
    overrides: [
      currentUserProvider.overrideWith(
        (ref) => const AppUser(uid: 'citizen-a'),
      ),
      reportRepositoryProvider.overrideWithValue(_Suggesting()),
    ],
  );
  addTearDown(container.dispose);
  final subscription = container.listen(reportControllerProvider, (_, _) {});
  addTearDown(subscription.close);
  return container;
}

void main() {
  test(
    'a suggestion fills the report details the citizen left empty',
    () async {
      final container = _container();
      final controller = container.read(reportControllerProvider.notifier);
      controller.updateTranscript('Handpump in ward 4 is broken');
      await controller.analyze();
      final draft = container.read(reportControllerProvider).draft;
      expect(draft.manualTitle, 'Broken handpump in ward 4');
      expect(draft.manualCategory, DemandCategory.water);
      expect(draft.manualSeverity, Severity.high);
      expect(draft.locationLabel, 'ward 4');
    },
  );

  test('a suggestion never replaces details the citizen entered', () async {
    final container = _container();
    final controller = container.read(reportControllerProvider.notifier);
    controller.updateTranscript('Handpump in ward 4 is broken');
    controller.updateManualTitle('My own title');
    controller.updateManualCategory(DemandCategory.roads);
    controller.updateManualSeverity(Severity.low);
    await controller.analyze();
    final draft = container.read(reportControllerProvider).draft;
    expect(draft.manualTitle, 'My own title');
    expect(draft.manualCategory, DemandCategory.roads);
    expect(draft.manualSeverity, Severity.low);
    expect(draft.analysis?.category, DemandCategory.water);
  });
}
