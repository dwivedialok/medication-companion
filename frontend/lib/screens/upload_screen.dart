import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../l10n/app_localizations.dart';
import '../services/api_service.dart';

class UploadScreen extends StatefulWidget {
  final String language;

  const UploadScreen({super.key, required this.language});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  final _picker = ImagePicker();
  XFile? _pickedFile;
  bool _loading = false;
  int _stepIndex = 0;
  String? _statusMessage;
  String? _errorMessage;
  bool _retakeNeeded = false;

  List<String> _steps(AppLocalizations l10n) => [
        l10n.stepReading,
        l10n.stepChecking,
        l10n.stepGenerating,
      ];

  Map<String, String> _asyncStatusLabels(AppLocalizations l10n) => {
        'pending': l10n.statusPending,
        'processing': l10n.statusProcessing,
        'done': l10n.statusDone,
      };

  Future<void> _pickImage(ImageSource source) async {
    final l10n = AppLocalizations.of(context)!;
    try {
      final file = await _picker.pickImage(
        source: source,
        imageQuality: 90,
        maxWidth: 2048,
      );
      if (file != null) {
        setState(() {
          _pickedFile = file;
          _errorMessage = null;
          _retakeNeeded = false;
        });
      }
    } catch (e) {
      setState(() => _errorMessage = l10n.accessError(e.toString()));
    }
  }

  Future<void> _submit() async {
    if (_pickedFile == null) return;
    setState(() {
      _loading = true;
      _stepIndex = 0;
      _statusMessage = null;
      _errorMessage = null;
      _retakeNeeded = false;
    });

    final l10n = AppLocalizations.of(context)!;
    final steps = _steps(l10n);
    final asyncLabels = _asyncStatusLabels(l10n);

    final stepTimer = _runStepAnimation(steps.length);

    try {
      final imageBytes = await _pickedFile!.readAsBytes();
      final mimeType = _mimeType(_pickedFile!.name);

      final result = await context.read<ApiService>().analyzePrescription(
            imageBytes: imageBytes,
            mimeType: mimeType,
            language: widget.language,
            fileName: _pickedFile!.name,
            onJobStatus: (status) {
              if (!mounted) return;
              setState(() {
                _statusMessage = asyncLabels[status];
                if (status == 'processing') {
                  _stepIndex = 1;
                }
              });
            },
          );

      stepTimer.cancel();
      if (mounted) {
        context.go('/result', extra: result);
      }
    } on RetakeRequiredException catch (e) {
      stepTimer.cancel();
      setState(() {
        _loading = false;
        _retakeNeeded = true;
        _errorMessage = e.message;
      });
    } catch (e) {
      stepTimer.cancel();
      setState(() {
        _loading = false;
        _errorMessage = e.toString().replaceFirst('ApiException(\\d+): ', '');
      });
    }
  }

  _Cancellable _runStepAnimation(int stepCount) {
    var cancelled = false;
    Future<void> advance() async {
      for (var i = 1; i < stepCount; i++) {
        await Future.delayed(const Duration(seconds: 6));
        if (cancelled || !mounted) return;
        setState(() => _stepIndex = i);
      }
    }

    advance();
    return _Cancellable(() => cancelled = true);
  }

  String _mimeType(String fileName) {
    final ext = fileName.toLowerCase().split('.').last;
    return switch (ext) {
      'png' => 'image/png',
      'webp' => 'image/webp',
      'heic' => 'image/heic',
      _ => 'image/jpeg',
    };
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.scanPrescription),
        leading: _loading
            ? null
            : IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => context.go('/home'),
              ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: _loading ? _buildLoading(theme, l10n) : _buildPicker(theme, l10n),
        ),
      ),
    );
  }

  Widget _buildPicker(ThemeData theme, AppLocalizations l10n) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: GestureDetector(
            onTap: () => _pickImage(ImageSource.gallery),
            child: Container(
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: _retakeNeeded
                      ? theme.colorScheme.error
                      : theme.colorScheme.outlineVariant,
                  width: _retakeNeeded ? 2 : 1,
                ),
              ),
              child: _pickedFile != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(15),
                      child: FutureBuilder<Uint8List?>(
                        future: _pickedFile!.readAsBytes().then(Uint8List.fromList),
                        builder: (context, snap) {
                          if (!snap.hasData) {
                            return const Center(child: CircularProgressIndicator());
                          }
                          return Image.memory(snap.data!, fit: BoxFit.contain);
                        },
                      ),
                    )
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.add_photo_alternate_outlined,
                          size: 64,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          l10n.tapGallery,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
            ),
          ),
        ),

        if (_errorMessage != null) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: theme.colorScheme.errorContainer,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                Icon(Icons.warning_amber, color: theme.colorScheme.onErrorContainer),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: theme.colorScheme.onErrorContainer),
                  ),
                ),
              ],
            ),
          ),
        ],

        const SizedBox(height: 20),

        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _pickImage(ImageSource.camera),
                icon: const Icon(Icons.camera_alt),
                label: Text(l10n.camera),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _pickImage(ImageSource.gallery),
                icon: const Icon(Icons.photo_library),
                label: Text(l10n.gallery),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        FilledButton.icon(
          onPressed: _pickedFile == null ? null : _submit,
          icon: Icon(_retakeNeeded ? Icons.refresh : Icons.send),
          label: Text(_retakeNeeded ? l10n.retakePhoto : l10n.analysePrescription),
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ],
    );
  }

  Widget _buildLoading(ThemeData theme, AppLocalizations l10n) {
    final steps = _steps(l10n);
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const CircularProgressIndicator(),
        const SizedBox(height: 32),
        Text(
          _statusMessage ?? steps[_stepIndex],
          style: theme.textTheme.titleMedium,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(steps.length, (i) {
            final active = i <= _stepIndex;
            return AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              margin: const EdgeInsets.symmetric(horizontal: 4),
              width: active ? 24 : 8,
              height: 8,
              decoration: BoxDecoration(
                color: active
                    ? theme.colorScheme.primary
                    : theme.colorScheme.outlineVariant,
                borderRadius: BorderRadius.circular(4),
              ),
            );
          }),
        ),
        const SizedBox(height: 24),
        Text(
          l10n.loadingHint,
          textAlign: TextAlign.center,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

class _Cancellable {
  final VoidCallback _cancel;
  _Cancellable(this._cancel);
  void cancel() => _cancel();
}
