import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../l10n/app_localizations.dart';
import '../models/prescription_result.dart';

String severityChipLabel(AppLocalizations l10n, String severity) =>
    switch (severity) {
      'HIGH' => l10n.sevChipHigh,
      'MODERATE' => l10n.sevChipModerate,
      'LOW' => l10n.sevChipLow,
      'INFO' => l10n.sevChipInfo,
      _ => l10n.sevChipNone,
    };

class ResultScreen extends StatefulWidget {
  final PrescriptionResult result;

  const ResultScreen({super.key, required this.result});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  final _player = AudioPlayer();
  PlayerState _playerState = PlayerState.stopped;

  @override
  void initState() {
    super.initState();
    _player.onPlayerStateChanged.listen((s) {
      if (mounted) setState(() => _playerState = s);
    });
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  PrescriptionResult get _r => widget.result;

  Future<void> _toggleAudio() async {
    if (_playerState == PlayerState.playing) {
      await _player.pause();
    } else {
      await _player.play(UrlSource(_r.audioUrl));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);

    final brandLookup = <String, String>{
      for (final d in _r.resolvedDrugs)
        if (d.genericName.isNotEmpty)
          d.genericName.toLowerCase().trim(): d.rawName,
    };

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.prescriptionAnalysis),
        leading: IconButton(
          icon: const Icon(Icons.home),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _SeverityBanner(severity: _r.overallSeverity),
              const SizedBox(height: 16),

              if (_r.resolvedDrugs.isNotEmpty) ...[
                _SectionHeader(l10n.medicationsFound(_r.resolvedDrugs.length)),
                ..._r.resolvedDrugs.map((d) => _DrugCard(drug: d)),
                const SizedBox(height: 16),
              ],

              if (_r.interactions.isNotEmpty) ...[
                _SectionHeader(l10n.interactions(_r.interactions.length)),
                ..._r.interactions.map(
                  (ix) => _InteractionCard(
                    interaction: ix,
                    brandLookup: brandLookup,
                  ),
                ),
                const SizedBox(height: 16),
              ],

              _SectionHeader(l10n.summary),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(
                    _r.explanationLocalised.isNotEmpty
                        ? _r.explanationLocalised
                        : _r.explanationEn,
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              if (_r.audioUrl.isNotEmpty) ...[
                _SectionHeader(l10n.audioExplanation),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    child: Row(
                      children: [
                        IconButton.filled(
                          onPressed: _toggleAudio,
                          icon: Icon(
                            _playerState == PlayerState.playing
                                ? Icons.pause
                                : Icons.play_arrow,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _playerState == PlayerState.playing
                                ? l10n.playing
                                : l10n.tapToPlay,
                            style: theme.textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              if (_r.doctorQuestions.isNotEmpty) ...[
                _SectionHeader(l10n.doctorQuestions),
                if (Localizations.localeOf(context).languageCode != 'en')
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Text(
                      l10n.shownInEnglishNote,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: _r.doctorQuestions
                          .map((q) => Padding(
                                padding: const EdgeInsets.only(bottom: 8),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text('• ',
                                        style: TextStyle(
                                            fontWeight: FontWeight.bold)),
                                    Expanded(
                                        child: Text(
                                      q,
                                      style: theme.textTheme.bodyMedium,
                                    )),
                                  ],
                                ),
                              ))
                          .toList(),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: theme.colorScheme.outlineVariant),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline,
                        color: theme.colorScheme.onSurfaceVariant, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        Localizations.localeOf(context).languageCode == 'en'
                            ? (_r.disclaimer.isNotEmpty
                                ? _r.disclaimer
                                : l10n.disclaimerHome)
                            : l10n.disclaimerHome,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              OutlinedButton.icon(
                onPressed: () => context.go('/home'),
                icon: const Icon(Icons.home),
                label: Text(l10n.backToHome),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
      ),
    );
  }
}

class _SeverityBanner extends StatelessWidget {
  final String severity;
  const _SeverityBanner({required this.severity});

  (Color, Color, IconData, String) _attrs(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final cs = Theme.of(context).colorScheme;
    return switch (severity) {
      'HIGH' => (
          Colors.red.shade700,
          Colors.white,
          Icons.warning_rounded,
          l10n.severityHigh
        ),
      'MODERATE' => (
          Colors.orange.shade700,
          Colors.white,
          Icons.warning_amber_rounded,
          l10n.severityModerate
        ),
      'LOW' => (
          Colors.green.shade700,
          Colors.white,
          Icons.check_circle_outline,
          l10n.severityLow
        ),
      'INFO' => (
          cs.primary,
          cs.onPrimary,
          Icons.info_outline,
          l10n.severityInfo
        ),
      _ => (
          cs.surfaceContainerHighest,
          cs.onSurface,
          Icons.check_circle_outline,
          l10n.severityNone
        ),
    };
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final (bg, fg, icon, label) = _attrs(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(icon, color: fg, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  severityChipLabel(l10n, severity),
                  style: TextStyle(
                    color: fg,
                    fontWeight: FontWeight.bold,
                    fontSize: 18,
                  ),
                ),
                Text(label, style: TextStyle(color: fg, fontSize: 13)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DrugCard extends StatelessWidget {
  final ResolvedDrug drug;
  const _DrugCard({required this.drug});

  String _tagLabel(AppLocalizations l10n) => switch (drug.tag) {
        'NEW' => l10n.tagNew,
        'EXISTING' => l10n.tagExisting,
        'UNRESOLVED' => l10n.tagUnresolved,
        _ => drug.tag,
      };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);
    final isNew = drug.tag == 'NEW';
    final isUnresolved = drug.tag == 'UNRESOLVED';

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          Icons.medication,
          color: isUnresolved
              ? theme.colorScheme.error
              : theme.colorScheme.primary,
        ),
        title: Text(drug.rawName,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: isUnresolved
            ? Text(l10n.couldNotResolve)
            : Text(drug.genericName),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: isUnresolved
                ? theme.colorScheme.errorContainer
                : isNew
                    ? theme.colorScheme.primaryContainer
                    : theme.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            _tagLabel(l10n),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: isUnresolved
                  ? theme.colorScheme.onErrorContainer
                  : isNew
                      ? theme.colorScheme.onPrimaryContainer
                      : theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }
}

class _InteractionCard extends StatelessWidget {
  final InteractionFinding interaction;
  final Map<String, String> brandLookup;
  const _InteractionCard({
    required this.interaction,
    required this.brandLookup,
  });

  Color _severityColor(String sev) => switch (sev) {
        'HIGH' => Colors.red.shade700,
        'MODERATE' => Colors.orange.shade700,
        'LOW' => Colors.green.shade700,
        _ => Colors.grey,
      };

  /// Returns "generic" or "generic (BRAND)" when the prescription brand
  /// differs from the generic — helps users match the row to what's
  /// written on their paper prescription.
  String _label(String generic) {
    final key = generic.toLowerCase().trim();
    final brand = brandLookup[key];
    if (brand == null || brand.isEmpty) return generic;
    if (brand.toLowerCase().trim() == key) return generic;
    return '$generic ($brand)';
  }

  String _chipLabel(AppLocalizations l10n) =>
      severityChipLabel(l10n, interaction.severity);

  String? _severityWord(AppLocalizations l10n, String sev) => switch (sev) {
        'high' || 'HIGH' => l10n.sevWordHigh,
        'moderate' || 'MODERATE' => l10n.sevWordModerate,
        'low' || 'LOW' => l10n.sevWordLow,
        _ => null,
      };

  /// Matches the deterministic backend template from
  /// `backend/tools/safety_check.py::_mechanism_text`:
  ///   "Dataset records a <severity> interaction between <a> and <b>.
  ///    Please discuss this with your doctor or pharmacist."
  static final RegExp _datasetMechanismRe = RegExp(
    r'^\s*Dataset records a (high|moderate|low) interaction between (.+?) and (.+?)\.\s*Please discuss this with your doctor or pharmacist\.?\s*$',
    caseSensitive: false,
  );

  String _localizedMechanism(BuildContext context, AppLocalizations l10n) {
    final raw = interaction.mechanism;
    if (Localizations.localeOf(context).languageCode == 'en') return raw;

    final match = _datasetMechanismRe.firstMatch(raw);
    if (match == null) return raw;

    final word = _severityWord(l10n, match.group(1) ?? '') ?? '';
    final a = _label(match.group(2) ?? '');
    final b = _label(match.group(3) ?? '');
    return l10n.mechanismDataset(word, a, b);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final color = _severityColor(interaction.severity);
    final pairLabel = '${_label(interaction.drugA)} + ${_label(interaction.drugB)}';

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.compare_arrows, color: color, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    pairLabel,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    _chipLabel(l10n),
                    style: TextStyle(
                      color: color,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              _localizedMechanism(context, l10n),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (interaction.source == 'cross_visit') ...[
              const SizedBox(height: 6),
              Row(
                children: [
                  Icon(Icons.history, size: 14,
                      color: Theme.of(context).colorScheme.onSurfaceVariant),
                  const SizedBox(width: 4),
                  Text(
                    l10n.crossVisitDetected,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color:
                              Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
