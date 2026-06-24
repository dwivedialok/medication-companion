import 'package:flutter/material.dart';

import '../l10n/app_localizations.dart';
import '../utils/password_strength.dart';

class PasswordStrengthIndicator extends StatelessWidget {
  final PasswordStrength strength;

  const PasswordStrengthIndicator({super.key, required this.strength});

  @override
  Widget build(BuildContext context) {
    if (strength == PasswordStrength.empty) {
      return const SizedBox.shrink();
    }

    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);
    final (label, color, segments) = _attrs(l10n, theme);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 8),
        Row(
          children: List.generate(4, (index) {
            final filled = index < segments;
            return Expanded(
              child: Container(
                height: 4,
                margin: EdgeInsets.only(right: index == 3 ? 0 : 6),
                decoration: BoxDecoration(
                  color: filled ? color : theme.colorScheme.outlineVariant,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 6),
        Text(
          label,
          style: theme.textTheme.labelMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  (String, Color, int) _attrs(AppLocalizations l10n, ThemeData theme) {
    return switch (strength) {
      PasswordStrength.weak => (l10n.passwordStrengthWeak, theme.colorScheme.error, 1),
      PasswordStrength.fair => (l10n.passwordStrengthFair, Colors.orange.shade700, 2),
      PasswordStrength.good => (l10n.passwordStrengthGood, Colors.lightGreen.shade700, 3),
      PasswordStrength.strong => (l10n.passwordStrengthStrong, Colors.green.shade700, 4),
      PasswordStrength.empty => ('', theme.colorScheme.outline, 0),
    };
  }
}
