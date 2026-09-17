import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';

/// Anh bang chung/anh doi chieu (URL co chu ky tu API). Cham de phong to.
class EvidenceImage extends StatelessWidget {
  const EvidenceImage({super.key, required this.path, this.size = 48, this.radius = 8});

  final String? path;
  final double size;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final url = context.read<ApiClient>().mediaUrl(path);
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    if (url.isEmpty) {
      return SizedBox(width: size, height: size, child: Icon(Icons.image_not_supported_outlined, color: muted));
    }
    return InkWell(
      borderRadius: BorderRadius.circular(radius),
      onTap: () => showDialog<void>(
        context: context,
        builder: (context) => Dialog(
          clipBehavior: Clip.antiAlias,
          child: Stack(
            children: [
              InteractiveViewer(child: Image.network(url, fit: BoxFit.contain, errorBuilder: _broken)),
              Positioned(
                right: 4,
                top: 4,
                child: IconButton.filledTonal(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
              ),
            ],
          ),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: Image.network(url, width: size, height: size, fit: BoxFit.cover, errorBuilder: _broken),
      ),
    );
  }

  static Widget _broken(BuildContext context, Object error, StackTrace? stack) =>
      const Center(child: Icon(Icons.broken_image_outlined));
}
