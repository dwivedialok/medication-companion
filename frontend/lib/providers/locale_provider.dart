import 'package:flutter/material.dart';

/// Maps UI + audio language codes used across the app.
class LocaleProvider extends ChangeNotifier {
  LocaleProvider({String initialCode = 'en-IN'}) : _languageCode = initialCode;

  static const supportedLanguages = {
    'en-IN': 'English',
    'hi-IN': 'Hindi',
    'ta-IN': 'Tamil',
    'te-IN': 'Telugu',
    'bn-IN': 'Bengali',
  };

  String _languageCode;

  String get languageCode => _languageCode;

  Locale get locale {
    final parts = _languageCode.split('-');
    if (parts.length == 2) {
      return Locale(parts[0], parts[1]);
    }
    return Locale(parts[0]);
  }

  void setLanguageCode(String code) {
    if (!supportedLanguages.containsKey(code) || code == _languageCode) {
      return;
    }
    _languageCode = code;
    notifyListeners();
  }
}
