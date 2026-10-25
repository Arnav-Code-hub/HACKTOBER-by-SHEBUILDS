import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../errors/failure.dart';

/// Validates cumulative attachment count and actual image headers before upload.
/// The backend remains responsible for enforcing the same limits independently.
abstract final class PhotoRules {
  static const maxPhotos = 3;
  static const maxBytes = 10 * 1024 * 1024;

  static void checkCount(int existing, int incoming) {
    if (existing + incoming > maxPhotos) {
      throw const ValidationFailure('Choose no more than 3 photos in total.');
    }
  }

  static Future<String> validate(XFile photo) async {
    final size = await photo.length();
    if (size > maxBytes || size == 0) {
      throw const ValidationFailure(
        'Each photo must be non-empty and at most 10 MB.',
      );
    }
    final bytes = await photo
        .openRead(0, size < 12 ? size : 12)
        .fold<List<int>>(<int>[], (all, chunk) => all..addAll(chunk));
    if (bytes.length >= 3 &&
        bytes[0] == 0xff &&
        bytes[1] == 0xd8 &&
        bytes[2] == 0xff) {
      return 'image/jpeg';
    }
    const png = <int>[137, 80, 78, 71, 13, 10, 26, 10];
    if (bytes.length >= 8 &&
        List.generate(8, (i) => bytes[i] == png[i]).every((v) => v)) {
      return 'image/png';
    }
    if (bytes.length >= 12 &&
        String.fromCharCodes(bytes.take(4)) == 'RIFF' &&
        String.fromCharCodes(bytes.skip(8).take(4)) == 'WEBP') {
      return 'image/webp';
    }
    throw const ValidationFailure('Choose a JPEG, PNG, or WebP photo.');
  }
}

/// Camera and gallery access for evidence photos.
class MediaService {
  MediaService(this._picker);

  final ImagePicker _picker;

  /// Captures a photo. Geotag/time authenticity is not established by capture.
  Future<XFile?> capturePhoto({int existingCount = 0}) async {
    PhotoRules.checkCount(existingCount, 1);
    final file = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 82,
      maxWidth: 2000,
    );
    if (file != null) await PhotoRules.validate(file);
    return file;
  }

  Future<List<XFile>> pickPhotos({int existingCount = 0}) async {
    PhotoRules.checkCount(existingCount, 1);
    final files = await _picker.pickMultiImage(
      imageQuality: 82,
      maxWidth: 2000,
    );
    PhotoRules.checkCount(existingCount, files.length);
    for (final file in files) {
      await PhotoRules.validate(file);
    }
    return files;
  }
}

final mediaServiceProvider = Provider<MediaService>(
  (ref) => MediaService(ImagePicker()),
);
