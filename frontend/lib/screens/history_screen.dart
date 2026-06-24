import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../l10n/app_localizations.dart';
import '../models/prescription_history_item.dart';
import '../services/api_service.dart';
import '../widgets/prescription_thumbnail.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  late Future<List<PrescriptionHistoryItem>> _itemsFuture;

  @override
  void initState() {
    super.initState();
    _itemsFuture = _load();
  }

  Future<List<PrescriptionHistoryItem>> _load() {
    return context.read<ApiService>().listPrescriptions();
  }

  Future<void> _refresh() async {
    final next = _load();
    setState(() => _itemsFuture = next);
    await next;
  }

  Future<void> _openItem(PrescriptionHistoryItem item) async {
    final api = context.read<ApiService>();
    final messenger = ScaffoldMessenger.of(context);
    final router = GoRouter.of(context);
    final l10n = AppLocalizations.of(context)!;

    if (item.isInProgress) {
      router.go('/jobs/${item.jobId}/wait');
      return;
    }

    if (item.status == 'failed') {
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.historyFailed)),
      );
      return;
    }

    try {
      final result = await api.getPrescriptionResult(item.jobId);
      if (!mounted) return;
      router.go('/result', extra: {'result': result, 'jobId': item.jobId});
    } on ApiException catch (e) {
      if (!mounted) return;
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.historyTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _refresh,
          child: FutureBuilder<List<PrescriptionHistoryItem>>(
            future: _itemsFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return _ErrorView(message: l10n.historyLoadError);
              }
              final items = snapshot.data ?? [];
              if (items.isEmpty) {
                return _EmptyView(message: l10n.historyEmpty);
              }
              return ListView.separated(
                padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (context, i) => _HistoryCard(
                  item: items[i],
                  onTap: () => _openItem(items[i]),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  final PrescriptionHistoryItem item;
  final VoidCallback onTap;

  const _HistoryCard({required this.item, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);
    final dateFormat = DateFormat.yMMMd(
      Localizations.localeOf(context).toLanguageTag(),
    ).add_jm();

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 72,
                height: 72,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: PrescriptionThumbnail(jobId: item.jobId),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      dateFormat.format(item.createdAt),
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      item.summaryOneLiner ?? _statusLabel(l10n, item),
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        _StatusChip(item: item),
                        if (item.drugCount != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            '${item.drugCount} ${l10n.medicationsFound(item.drugCount!).split('(').first.trim()}',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }

  String _statusLabel(AppLocalizations l10n, PrescriptionHistoryItem item) {
    switch (item.status) {
      case 'pending':
      case 'processing':
        return l10n.historyProcessing;
      case 'failed':
        return l10n.historyFailed;
      default:
        return l10n.prescriptionAnalysis;
    }
  }
}

class _StatusChip extends StatelessWidget {
  final PrescriptionHistoryItem item;
  const _StatusChip({required this.item});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);

    if (item.isInProgress) {
      return _chip(
        label: l10n.historyProcessing,
        bg: theme.colorScheme.secondaryContainer,
        fg: theme.colorScheme.onSecondaryContainer,
        icon: Icons.hourglass_top,
      );
    }
    if (item.status == 'failed') {
      return _chip(
        label: l10n.historyFailed,
        bg: theme.colorScheme.errorContainer,
        fg: theme.colorScheme.onErrorContainer,
        icon: Icons.error_outline,
      );
    }
    final sev = item.overallSeverity ?? 'NONE';
    final (bg, fg) = _severityColors(theme, sev);
    return _chip(
      label: sev,
      bg: bg,
      fg: fg,
      icon: _severityIcon(sev),
    );
  }

  Widget _chip({
    required String label,
    required Color bg,
    required Color fg,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: fg),
          const SizedBox(width: 4),
          Text(
            label,
            style: TextStyle(
              color: fg,
              fontSize: 11,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  (Color, Color) _severityColors(ThemeData theme, String sev) {
    switch (sev) {
      case 'HIGH':
        return (Colors.red.shade700, Colors.white);
      case 'MODERATE':
        return (Colors.orange.shade700, Colors.white);
      case 'LOW':
        return (Colors.green.shade700, Colors.white);
      case 'INFO':
        return (theme.colorScheme.primary, theme.colorScheme.onPrimary);
      default:
        return (
          theme.colorScheme.surfaceContainerHighest,
          theme.colorScheme.onSurfaceVariant,
        );
    }
  }

  IconData _severityIcon(String sev) {
    switch (sev) {
      case 'HIGH':
        return Icons.warning_rounded;
      case 'MODERATE':
        return Icons.warning_amber_rounded;
      case 'LOW':
      case 'INFO':
        return Icons.info_outline;
      default:
        return Icons.check_circle_outline;
    }
  }
}

class _EmptyView extends StatelessWidget {
  final String message;
  const _EmptyView({required this.message});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 80),
        Icon(
          Icons.inbox_outlined,
          size: 64,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  const _ErrorView({required this.message});

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 80),
        Icon(
          Icons.error_outline,
          size: 64,
          color: Theme.of(context).colorScheme.error,
        ),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Text(
            message,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }
}
