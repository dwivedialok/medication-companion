import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../l10n/app_localizations.dart';
import '../providers/locale_provider.dart';

class LanguageSelector extends StatelessWidget {
  final bool compact;

  const LanguageSelector({super.key, this.compact = false});

  String _labelForCode(AppLocalizations l10n, String code) {
    return switch (code) {
      'en-IN' => l10n.langEnglish,
      'hi-IN' => l10n.langHindi,
      'ta-IN' => l10n.langTamil,
      'te-IN' => l10n.langTelugu,
      'bn-IN' => l10n.langBengali,
      _ => LocaleProvider.supportedLanguages[code] ?? code,
    };
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final localeProvider = context.watch<LocaleProvider>();
    final theme = Theme.of(context);

    final dropdown = DropdownButtonHideUnderline(
      child: DropdownButton<String>(
        value: localeProvider.languageCode,
        isExpanded: !compact,
        icon: Icon(Icons.language, color: theme.colorScheme.primary, size: 20),
        items: LocaleProvider.supportedLanguages.keys
            .map(
              (code) => DropdownMenuItem(
                value: code,
                child: Text(_labelForCode(l10n, code)),
              ),
            )
            .toList(),
        onChanged: (code) {
          if (code != null) {
            context.read<LocaleProvider>().setLanguageCode(code);
          }
        },
      ),
    );

    if (compact) {
      return dropdown;
    }

    return InputDecorator(
      decoration: InputDecoration(
        labelText: l10n.appLanguage,
        border: const OutlineInputBorder(),
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      ),
      child: dropdown,
    );
  }
}
