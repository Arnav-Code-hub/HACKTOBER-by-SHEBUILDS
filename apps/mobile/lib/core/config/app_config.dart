/// Public compile-time configuration. Firebase client settings identify the
/// project; privileged Cloudinary/Gemini/Admin secrets stay on the backend.
abstract final class AppConfig {
  static const appName = 'JanMaang';

  /// Defaults to true so the whole UI is navigable before a Firebase project
  /// is attached. Use a public config JSON with USE_MOCKS=false for live mode.
  static const useMocks = bool.fromEnvironment('USE_MOCKS', defaultValue: true);

  /// Google Maps needs a platform API key in the Android manifest / iOS plist.
  /// Until that is provisioned the map surfaces render the styled static
  /// placeholder the Stitch designs show.
  static const mapsEnabled = bool.fromEnvironment(
    'MAPS_ENABLED',
    defaultValue: false,
  );

  /// Starts the mock build already signed in.
  ///
  /// For demos, screenshots and UI review, where stepping through OTP every
  /// reload is friction with no informational value. Has no effect once
  /// [useMocks] is false — real auth always requires real credentials.
  static const demoSignedIn =
      bool.fromEnvironment('DEMO_SIGNED_IN') && useMocks;

  static const defaultDistrict = 'Yadgir';
  static const defaultState = 'Karnataka';
  static const supportPhone = '1800-000-0000';

  /// Region the Cloud Functions are deployed to.
  static const functionsRegion = 'asia-south1';

  /// Public Firebase client configuration; never put Admin/Gemini/Cloudinary
  /// secrets in a dart-define (all client values are visible to the browser).
  static const apiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const firebaseApiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const firebaseAppId = String.fromEnvironment('FIREBASE_APP_ID');
  static const firebaseMessagingSenderId = String.fromEnvironment(
    'FIREBASE_MESSAGING_SENDER_ID',
  );
  static const firebaseProjectId = String.fromEnvironment(
    'FIREBASE_PROJECT_ID',
  );
  static const firebaseAuthDomain = String.fromEnvironment(
    'FIREBASE_AUTH_DOMAIN',
  );

  static List<String> get missingLiveConfiguration => <String>[
    if (apiBaseUrl.isEmpty) 'API_BASE_URL',
    if (firebaseApiKey.isEmpty) 'FIREBASE_API_KEY',
    if (firebaseAppId.isEmpty) 'FIREBASE_APP_ID',
    if (firebaseMessagingSenderId.isEmpty) 'FIREBASE_MESSAGING_SENDER_ID',
    if (firebaseProjectId.isEmpty) 'FIREBASE_PROJECT_ID',
    if (firebaseAuthDomain.isEmpty) 'FIREBASE_AUTH_DOMAIN',
  ];
}
