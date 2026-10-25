import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:janmaang/core/providers.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';
import 'package:janmaang/features/report/presentation/report_controller.dart';

final _identityProvider = NotifierProvider<_Identity, AppUser?>(_Identity.new);

class _Identity extends Notifier<AppUser?> {
  @override
  AppUser? build() => const AppUser(uid: 'citizen-a');
  void change(AppUser? user) => state = user;
}

void main() {
  test(
    'draft and idempotency key survive leaving and reopening report',
    () async {
      final container = ProviderContainer(
        overrides: [
          currentUserProvider.overrideWith(
            (ref) => ref.watch(_identityProvider),
          ),
        ],
      );
      addTearDown(container.dispose);
      final first = container.listen(reportControllerProvider, (_, _) {});
      final controller = container.read(reportControllerProvider.notifier);
      controller.updateTranscript('Do not lose this draft');
      final key = container.read(reportControllerProvider).draft.submissionKey;
      first.close();
      await container.pump();
      final reopened = container.listen(reportControllerProvider, (_, _) {});
      addTearDown(reopened.close);
      expect(
        container.read(reportControllerProvider).draft.transcript,
        'Do not lose this draft',
      );
      expect(container.read(reportControllerProvider).draft.submissionKey, key);
    },
  );

  test(
    'logout or identity change clears another citizen draft and photos',
    () async {
      final container = ProviderContainer(
        overrides: [
          currentUserProvider.overrideWith(
            (ref) => ref.watch(_identityProvider),
          ),
        ],
      );
      addTearDown(container.dispose);
      final subscription = container.listen(
        reportControllerProvider,
        (_, _) {},
      );
      addTearDown(subscription.close);
      final controller = container.read(reportControllerProvider.notifier);
      controller.updateTranscript('Private citizen A report');
      await controller.addPhotos(<XFile>[
        XFile.fromData(
          Uint8List.fromList(<int>[
            137,
            80,
            78,
            71,
            13,
            10,
            26,
            10,
            0,
            0,
            0,
            0,
          ]),
          name: 'photo.png',
        ),
      ]);
      final firstKey = container
          .read(reportControllerProvider)
          .draft
          .submissionKey;
      expect(container.read(reportControllerProvider).draft.photos.length, 1);
      container.read(_identityProvider.notifier).change(null);
      await container.pump();
      expect(
        container.read(reportControllerProvider).draft.transcript,
        isEmpty,
      );
      expect(container.read(reportControllerProvider).draft.photos, isEmpty);
      expect(
        container.read(reportControllerProvider).draft.submissionKey,
        isNot(firstKey),
      );
      container
          .read(_identityProvider.notifier)
          .change(const AppUser(uid: 'citizen-b'));
      await container.pump();
      expect(
        container.read(reportControllerProvider).draft.transcript,
        isEmpty,
      );
    },
  );
}
