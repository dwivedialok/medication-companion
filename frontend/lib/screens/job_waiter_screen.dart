import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../l10n/app_localizations.dart';
import '../services/api_service.dart';

/// Lightweight screen for a job that's still in progress when reached from
/// History. Polls /jobs/{id} via `ApiService.waitForPrescriptionResult` and
/// auto-routes to ResultScreen on completion.
class JobWaiterScreen extends StatefulWidget {
  final String jobId;
  const JobWaiterScreen({super.key, required this.jobId});

  @override
  State<JobWaiterScreen> createState() => _JobWaiterScreenState();
}

class _JobWaiterScreenState extends State<JobWaiterScreen> {
  String _status = 'pending';
  String? _errorMessage;
  bool _waiting = true;

  @override
  void initState() {
    super.initState();
    _startWaiting();
  }

  Future<void> _startWaiting() async {
    final api = context.read<ApiService>();
    final router = GoRouter.of(context);
    try {
      final result = await api.waitForPrescriptionResult(
        widget.jobId,
        onStatus: (s) {
          if (mounted) setState(() => _status = s);
        },
      );
      if (!mounted) return;
      router.go('/result', extra: {'result': result, 'jobId': widget.jobId});
    } on RetakeRequiredException catch (e) {
      if (!mounted) return;
      setState(() {
        _waiting = false;
        _errorMessage = e.message;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _waiting = false;
        _errorMessage = e.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);

    final statusLabel = switch (_status) {
      'processing' => l10n.statusProcessing,
      'done' => l10n.statusDone,
      _ => l10n.statusPending,
    };

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.prescriptionAnalysis),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/history'),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (_waiting) ...[
                  const CircularProgressIndicator(),
                  const SizedBox(height: 32),
                  Text(statusLabel,
                      style: theme.textTheme.titleMedium,
                      textAlign: TextAlign.center),
                  const SizedBox(height: 12),
                  Text(
                    l10n.loadingHint,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ] else ...[
                  Icon(Icons.error_outline,
                      size: 64, color: theme.colorScheme.error),
                  const SizedBox(height: 16),
                  Text(
                    _errorMessage ?? l10n.analysisNotReady,
                    style: theme.textTheme.bodyMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  OutlinedButton.icon(
                    onPressed: () => context.go('/history'),
                    icon: const Icon(Icons.arrow_back),
                    label: Text(l10n.backToHome),
                  ),
                ]
              ],
            ),
          ),
        ),
      ),
    );
  }
}
