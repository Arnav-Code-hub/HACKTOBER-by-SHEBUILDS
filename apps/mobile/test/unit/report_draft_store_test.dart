import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:janmaang/features/report/data/report_draft_store.dart';
import 'package:janmaang/features/report/domain/report_draft.dart';
import 'package:janmaang/shared/models/demand_enums.dart';
import 'package:shared_preferences/shared_preferences.dart';

ReportDraft draft() => ReportDraft(
  transcript: 'Handpump broken near the school',
  channel: ReportChannel.text,
  latitude: 16.76,
  longitude: 77.14,
  locationLabel: 'Ward 4',
  manualTitle: 'Broken handpump',
  manualCategory: DemandCategory.water,
  manualSeverity: Severity.high,
  analysis: const ReportAnalysis(
    category: DemandCategory.water,
    severity: Severity.high,
    title: 'Handpump not working',
    summary: 'No water from the handpump.',
    detectedLanguage: 'hi',
  ),
  photos: <XFile>[XFile('before.jpg')],
);

void main() {
  setUp(() => SharedPreferences.setMockInitialValues(<String, Object>{}));

  test('restores the text, location, manual fields and analysis', () async {
    final store = SharedPreferencesReportDraftStore();
    await store.save('citizen-1', draft());
    final restored = await store.load('citizen-1');

    expect(restored, isNotNull);
    expect(restored!.transcript, 'Handpump broken near the school');
    expect(restored.channel, ReportChannel.text);
    expect(restored.latitude, 16.76);
    expect(restored.longitude, 77.14);
    expect(restored.locationLabel, 'Ward 4');
    expect(restored.manualTitle, 'Broken handpump');
    expect(restored.manualCategory, DemandCategory.water);
    expect(restored.manualSeverity, Severity.high);
    expect(restored.analysis?.title, 'Handpump not working');
    expect(restored.analysis?.detectedLanguage, 'hi');
  });

  test('never stores photos', () async {
    final store = SharedPreferencesReportDraftStore();
    await store.save('citizen-1', draft());
    expect((await store.load('citizen-1'))!.photos, isEmpty);
  });

  test('discarding removes the draft', () async {
    final store = SharedPreferencesReportDraftStore();
    await store.save('citizen-1', draft());
    await store.clear('citizen-1');
    expect(await store.load('citizen-1'), isNull);
  });

  test('a draft never reaches another account on the same device', () async {
    final store = SharedPreferencesReportDraftStore();
    await store.save('citizen-1', draft());
    expect(await store.load('citizen-2'), isNull);
    // Loading as another user also deletes the first user's draft.
    expect(await store.load('citizen-1'), isNull);
  });

  test('an empty draft is not kept', () async {
    final store = SharedPreferencesReportDraftStore();
    await store.save('citizen-1', const ReportDraft());
    expect(await store.load('citizen-1'), isNull);
  });

  test('a corrupt saved draft is dropped instead of crashing', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'janmaang.reportDraft.citizen-1': '{not json',
    });
    final store = SharedPreferencesReportDraftStore();
    expect(await store.load('citizen-1'), isNull);
  });
}
