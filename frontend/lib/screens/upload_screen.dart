import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

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
  String? _errorMessage;
  bool _retakeNeeded = false;

  static const _steps = [
    'Reading prescription...',
    'Checking interactions...',
    'Generating explanation...',
  ];

  Future<void> _pickImage(ImageSource source) async {
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
      setState(() => _errorMessage = 'Could not access camera/gallery: $e');
    }
  }

  Future<void> _submit() async {
    if (_pickedFile == null) return;
    setState(() {
      _loading = true;
      _stepIndex = 0;
      _errorMessage = null;
      _retakeNeeded = false;
    });

    // Advance step indicator every ~5 seconds while the pipeline runs
    final stepTimer = _runStepAnimation();

    try {
      final imageBytes = await _pickedFile!.readAsBytes();
      final mimeType = _mimeType(_pickedFile!.name);

      final result = await context.read<ApiService>().analyzePrescription(
            imageBytes: imageBytes,
            mimeType: mimeType,
            language: widget.language,
            fileName: _pickedFile!.name,
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

  _Cancellable _runStepAnimation() {
    var cancelled = false;
    Future<void> advance() async {
      for (var i = 1; i < _steps.length; i++) {
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
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan prescription'),
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
          child: _loading ? _buildLoading(theme) : _buildPicker(theme),
        ),
      ),
    );
  }

  Widget _buildPicker(ThemeData theme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Image preview / placeholder
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
                        // ignore: deprecated_member_use
                        future: _pickedFile!.readAsBytes().then((b) => Uint8List.fromList(b)),
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
                          'Tap to select from gallery',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
            ),
          ),
        ),

        // Error / retake message
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

        // Camera / Gallery buttons
        Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _pickImage(ImageSource.camera),
                icon: const Icon(Icons.camera_alt),
                label: const Text('Camera'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _pickImage(ImageSource.gallery),
                icon: const Icon(Icons.photo_library),
                label: const Text('Gallery'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Submit / Retake button
        FilledButton.icon(
          onPressed: _pickedFile == null ? null : _submit,
          icon: Icon(_retakeNeeded ? Icons.refresh : Icons.send),
          label: Text(_retakeNeeded ? 'Retake photo' : 'Analyse prescription'),
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ],
    );
  }

  Widget _buildLoading(ThemeData theme) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const CircularProgressIndicator(),
        const SizedBox(height: 32),
        Text(
          _steps[_stepIndex],
          style: theme.textTheme.titleMedium,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        // Step dots
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(_steps.length, (i) {
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
          'This takes about 20-40 seconds.\nPlease keep this screen open.',
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
