import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';

import 'core/config/app_config.dart';
import 'core/config/configuration_error_screen.dart';
import 'core/network/api_client.dart';

/// Initializes Firebase for explicitly configured live builds. Missing setup
/// renders an actionable error screen and never falls back to demo data.
Future<void> bootstrap(Widget Function() builder) async {
  await runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      if (!AppConfig.useMocks) {
        final missing = AppConfig.missingLiveConfiguration;
        if (missing.isNotEmpty) {
          runApp(
            ConfigurationErrorApp(message: 'Missing: ${missing.join(', ')}.'),
          );
          return;
        }
        try {
          // Validate the business API URL before allowing any SDK login.
          ApiClient(
            baseUrl: AppConfig.apiBaseUrl,
            token: () async => null,
          ).close();
          await Firebase.initializeApp(
            options: const FirebaseOptions(
              apiKey: AppConfig.firebaseApiKey,
              appId: AppConfig.firebaseAppId,
              messagingSenderId: AppConfig.firebaseMessagingSenderId,
              projectId: AppConfig.firebaseProjectId,
              authDomain: AppConfig.firebaseAuthDomain,
            ),
          );
        } catch (_) {
          runApp(
            const ConfigurationErrorApp(
              message:
                  'Firebase or API configuration is invalid. Check the public '
                  'settings, authorized domains, and API_BASE_URL.',
            ),
          );
          return;
        }
      }

      FlutterError.onError = (details) {
        FlutterError.presentError(details);
        if (kReleaseMode) {
          // Crashlytics takes over here once Firebase is initialised.
        }
      };

      runApp(ProviderScope(child: builder()));
    },
    (error, stack) {
      debugPrint('Uncaught error: $error\n$stack');
    },
  );
}
