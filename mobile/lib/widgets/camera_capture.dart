import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

/// Khoi tao camera (uu tien camera truoc), xu ly quyen/loi, cho phep doi camera.
/// Dung chung cho tu diem danh, dang ky khuon mat va quet ca lop.
class CameraHandle {
  CameraController? controller;
  List<CameraDescription> cameras = const [];
  String? error;

  bool get isReady => controller?.value.isInitialized ?? false;

  bool get isFront => controller?.description.lensDirection == CameraLensDirection.front;

  Future<void> start({bool preferFront = true, ResolutionPreset preset = ResolutionPreset.medium}) async {
    error = null;
    try {
      cameras = await availableCameras();
      if (cameras.isEmpty) {
        error = 'Không tìm thấy camera trên thiết bị.';
        return;
      }
      final wanted = preferFront ? CameraLensDirection.front : CameraLensDirection.back;
      final description = cameras.firstWhere((c) => c.lensDirection == wanted, orElse: () => cameras.first);
      await _open(description, preset);
    } on CameraException catch (e) {
      error = _describe(e);
    } catch (e) {
      error = 'Không mở được camera: $e';
    }
  }

  Future<void> _open(CameraDescription description, ResolutionPreset preset) async {
    final old = controller;
    controller = null;
    await old?.dispose();
    final next = CameraController(description, preset, enableAudio: false, imageFormatGroup: ImageFormatGroup.jpeg);
    await next.initialize();
    controller = next;
  }

  Future<void> switchCamera() async {
    final current = controller?.description;
    if (current == null || cameras.length < 2) return;
    final index = cameras.indexOf(current);
    final next = cameras[(index + 1) % cameras.length];
    try {
      await _open(next, controller?.resolutionPreset ?? ResolutionPreset.medium);
    } on CameraException catch (e) {
      error = _describe(e);
    }
  }

  Future<Uint8List> capture() async {
    final file = await controller!.takePicture();
    return file.readAsBytes();
  }

  Future<void> dispose() async {
    final old = controller;
    controller = null;
    await old?.dispose();
  }

  static String _describe(CameraException e) => switch (e.code) {
        'CameraAccessDenied' || 'CameraAccessDeniedWithoutPrompt' || 'CameraAccessRestricted' =>
          'Chưa cấp quyền camera. Hãy cho phép ứng dụng dùng camera trong cài đặt rồi thử lại.',
        'cameraNotFound' || 'cameraNotReadable' => 'Camera đang bận hoặc không khả dụng.',
        _ => 'Lỗi camera: ${e.description ?? e.code}',
      };
}

/// Khung xem truoc camera co ti le dung, co huong dan dat mat.
class CameraPreviewBox extends StatelessWidget {
  const CameraPreviewBox({super.key, required this.handle, this.showFaceGuide = true, this.overlay});

  final CameraHandle handle;
  final bool showFaceGuide;
  final Widget? overlay;

  @override
  Widget build(BuildContext context) {
    final controller = handle.controller;
    if (handle.error != null) {
      return _Placeholder(icon: Icons.videocam_off_outlined, text: handle.error!);
    }
    if (controller == null || !controller.value.isInitialized) {
      return const _Placeholder(icon: Icons.videocam_outlined, text: 'Đang mở camera…', loading: true);
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: CameraPreview(
        controller,
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (showFaceGuide)
              Center(
                child: FractionallySizedBox(
                  widthFactor: 0.55,
                  heightFactor: 0.7,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.white.withValues(alpha: 0.8), width: 2),
                      borderRadius: const BorderRadius.all(Radius.elliptical(200, 260)),
                    ),
                  ),
                ),
              ),
            ?overlay,
          ],
        ),
      ),
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.icon, required this.text, this.loading = false});

  final IconData icon;
  final String text;
  final bool loading;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 3 / 4,
      child: Container(
        decoration: BoxDecoration(color: Colors.black87, borderRadius: BorderRadius.circular(14)),
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (loading) const CircularProgressIndicator(color: Colors.white) else Icon(icon, color: Colors.white70, size: 40),
            const SizedBox(height: 12),
            Text(text, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70)),
          ],
        ),
      ),
    );
  }
}
