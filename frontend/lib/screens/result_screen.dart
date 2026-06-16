import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../models/prescription_result.dart';

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
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Prescription Analysis'),
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

              // Drug cards
              if (_r.resolvedDrugs.isNotEmpty) ...[
                _SectionHeader('Medications found (${_r.resolvedDrugs.length})'),
                ..._r.resolvedDrugs.map((d) => _DrugCard(drug: d)),
                const SizedBox(height: 16),
              ],

              // Interaction cards
              if (_r.interactions.isNotEmpty) ...[
                _SectionHeader('Interactions (${_r.interactions.length})'),
                ..._r.interactions.map((ix) => _InteractionCard(interaction: ix)),
                const SizedBox(height: 16),
              ],

              // Explanation
              _SectionHeader('Summary'),
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

              // Audio player
              if (_r.audioUrl.isNotEmpty) ...[
                _SectionHeader('Audio explanation'),
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
                                ? 'Playing...'
                                : 'Tap to play audio explanation',
                            style: theme.textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Doctor questions
              if (_r.doctorQuestions.isNotEmpty) ...[
                _SectionHeader('Questions for your doctor'),
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

              // Disclaimer
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
                        _r.disclaimer,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Back to home
              OutlinedButton.icon(
                onPressed: () => context.go('/home'),
                icon: const Icon(Icons.home),
                label: const Text('Back to home'),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Supporting widgets ────────────────────────────────────────────────────────

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
    final cs = Theme.of(context).colorScheme;
    return switch (severity) {
      'HIGH' => (
          Colors.red.shade700,
          Colors.white,
          Icons.warning_rounded,
          'High severity — review urgently with your doctor'
        ),
      'MODERATE' => (
          Colors.orange.shade700,
          Colors.white,
          Icons.warning_amber_rounded,
          'Moderate severity — discuss with your doctor'
        ),
      'LOW' => (
          Colors.green.shade700,
          Colors.white,
          Icons.check_circle_outline,
          'Low severity — informational'
        ),
      'INFO' => (
          cs.primary,
          cs.onPrimary,
          Icons.info_outline,
          'No interactions found'
        ),
      _ => (
          cs.surfaceContainerHighest,
          cs.onSurface,
          Icons.check_circle_outline,
          'No concerns identified'
        ),
    };
  }

  @override
  Widget build(BuildContext context) {
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
                  severity,
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

  @override
  Widget build(BuildContext context) {
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
            ? const Text('Could not be resolved')
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
            drug.tag,
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
  const _InteractionCard({required this.interaction});

  Color _severityColor(String sev) => switch (sev) {
        'HIGH' => Colors.red.shade700,
        'MODERATE' => Colors.orange.shade700,
        'LOW' => Colors.green.shade700,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context) {
    final color = _severityColor(interaction.severity);

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
                    '${interaction.drugA} + ${interaction.drugB}',
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
                    interaction.severity,
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
              interaction.mechanism,
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
                    'Detected from your medication history',
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
