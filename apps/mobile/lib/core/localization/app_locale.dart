import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const supportedAppLocales = <Locale>[
  Locale('en'),
  Locale('hi'),
  Locale('mr'),
  Locale('bn'),
  Locale('as'),
  Locale('pa'),
];

const appLanguageNames = <String, String>{
  'en': 'English',
  'hi': 'हिन्दी',
  'mr': 'मराठी',
  'bn': 'বাংলা',
  'as': 'অসমীয়া',
  'pa': 'ਪੰਜਾਬੀ',
};

final appLocaleProvider = AsyncNotifierProvider<AppLocaleController, Locale>(
  AppLocaleController.new,
);

class AppLocaleController extends AsyncNotifier<Locale> {
  static const _preferenceKey = 'app_language_code';

  @override
  Future<Locale> build() async {
    final preferences = await SharedPreferences.getInstance();
    final languageCode = preferences.getString(_preferenceKey) ?? 'en';
    return supportedAppLocales.firstWhere(
      (locale) => locale.languageCode == languageCode,
      orElse: () => const Locale('en'),
    );
  }

  Future<void> setLanguage(String languageCode) async {
    final locale = supportedAppLocales.firstWhere(
      (candidate) => candidate.languageCode == languageCode,
      orElse: () => const Locale('en'),
    );
    state = AsyncData(locale);
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_preferenceKey, locale.languageCode);
  }
}
