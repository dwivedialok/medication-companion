import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

/// Loads a signed GCS read URL for the prescription image of [jobId] and
/// displays it via `cached_network_image`. Falls back to a placeholder icon
/// when the URL cannot be resolved.
class PrescriptionThumbnail extends StatefulWidget {
  final String jobId;
  final BoxFit fit;

  const PrescriptionThumbnail({
    super.key,
    required this.jobId,
    this.fit = BoxFit.cover,
  });

  @override
  State<PrescriptionThumbnail> createState() => _PrescriptionThumbnailState();
}

class _PrescriptionThumbnailState extends State<PrescriptionThumbnail> {
  late Future<String> _urlFuture;

  @override
  void initState() {
    super.initState();
    _urlFuture = context.read<ApiService>().getPrescriptionImageUrl(widget.jobId);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return FutureBuilder<String>(
      future: _urlFuture,
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.waiting) {
          return Container(
            color: cs.surfaceContainerHighest,
            child: const Center(
              child: SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          );
        }
        if (!snap.hasData || snap.data!.isEmpty) {
          return Container(
            color: cs.surfaceContainerHighest,
            child: Icon(Icons.image_not_supported,
                color: cs.onSurfaceVariant, size: 20),
          );
        }
        return CachedNetworkImage(
          imageUrl: snap.data!,
          fit: widget.fit,
          placeholder: (_, __) => Container(
            color: cs.surfaceContainerHighest,
            child: const Center(
              child: SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          ),
          errorWidget: (_, __, ___) => Container(
            color: cs.surfaceContainerHighest,
            child: Icon(Icons.broken_image,
                color: cs.onSurfaceVariant, size: 20),
          ),
        );
      },
    );
  }
}
