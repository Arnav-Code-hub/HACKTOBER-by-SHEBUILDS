import 'package:flutter/material.dart';

class ConfigurationErrorApp extends StatelessWidget {
  const ConfigurationErrorApp({super.key, required this.message});
  final String message;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'JanMaang configuration',
    home: Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Text(
                  'Live setup required',
                  style: TextStyle(fontSize: 28),
                ),
                const SizedBox(height: 16),
                Text(message),
                const SizedBox(height: 16),
                const Text(
                  'Provide the public Firebase settings and API_BASE_URL '
                  'with --dart-define-from-file. See config/live.example.json. '
                  'Reload after updating the build configuration.',
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
