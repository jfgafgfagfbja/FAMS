import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/camera_capture.dart';
import '../../widgets/common.dart';

/// Can bo/giang vien dang ky khuon mat ho SV (vd SV khong tu thao tac duoc).
class EnrollForStudentPage extends StatefulWidget {
  const EnrollForStudentPage({super.key, required this.studentId});

  final int studentId;

  @override
  State<EnrollForStudentPage> createState() => _EnrollForStudentPageState();
}

class _EnrollForStudentPageState extends State<EnrollForStudentPage>
    with WidgetsBindingObserver, CameraLifecycleMixin {
  final _camera = CameraHandle();

  @override
  CameraHandle get camera => _camera;
  final List<Uint8List> _shots = [];
  bool _sending = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    _camera.start(preferFront: false).then((_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _camera.dispose();
    super.dispose();
  }

  Future<Student> _load() async =>
      Student.fromJson(await context.read<ApiClient>().get('/students/${widget.studentId}') as Json);

  Future<void> _send() async {
    setState(() {
      _sending = true;
      _message = null;
    });
    try {
      final data = await context.read<ApiClient>().postMultipart(
        '/faces/enroll/${widget.studentId}',
        files: [for (var i = 0; i < _shots.length; i++) UploadFile('images', _shots[i], 'pose_$i.jpg')],
      ) as Json;
      setState(() {
        _message = data['message'] as String?;
        if (data['ok'] == true) _shots.clear();
      });
    } catch (e) {
      setState(() => _message = errorText(e));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final perms = Perms(context.watch<AuthController>().role);
    return AsyncLoader<Student>(
      load: _load,
      builder: (context, student, reload) => PageBody(
        maxWidth: 720,
        children: [
          SectionCard(
            title: '${student.fullName} — ${student.studentCode}',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                StatusChip(label: faceStatusLabel(student.faceStatus), color: statusColor(student.faceStatus == 'none' ? null : student.faceStatus)),
                const SizedBox(height: 8),
                if (!student.consentGiven) ...[
                  const Text('Sinh viên chưa xác nhận đồng ý thu thập dữ liệu khuôn mặt.'),
                  const SizedBox(height: 8),
                  if (perms.manageStudents)
                    FilledButton(
                      onPressed: () async {
                        final ok = await runAction(context, () => context.read<ApiClient>().post('/students/${student.id}/consent'),
                            success: 'Đã xác nhận đồng ý (theo văn bản SV nộp)');
                        if (ok) reload();
                      },
                      child: const Text('Xác nhận đồng ý hộ'),
                    )
                  else
                    const Text('Giảng viên không thể xác nhận thay — cần SV tự xác nhận hoặc Phòng CTSV xác nhận hộ.'),
                ],
              ],
            ),
          ),
          if (student.consentGiven) ...[
            const SizedBox(height: 16),
            CameraPreviewBox(handle: _camera),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: _camera.isReady && _shots.length < 5
                      ? () async {
                          final bytes = await _camera.capture();
                          setState(() => _shots.add(bytes));
                        }
                      : null,
                  icon: const Icon(Icons.camera_alt),
                  label: Text('Chụp (${_shots.length}/5)'),
                ),
                OutlinedButton(onPressed: _shots.isEmpty || _sending ? null : _send, child: Text(_sending ? 'Đang gửi…' : 'Gửi đăng ký')),
                if (_camera.cameras.length > 1)
                  OutlinedButton.icon(
                    onPressed: () async {
                      await _camera.switchCamera();
                      if (mounted) setState(() {});
                    },
                    icon: const Icon(Icons.cameraswitch_outlined),
                    label: const Text('Đổi camera'),
                  ),
              ],
            ),
            if (_message != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(_message!)),
            if (_shots.isNotEmpty) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (var i = 0; i < _shots.length; i++)
                    Stack(
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.memory(_shots[i], width: 96, height: 96, fit: BoxFit.cover),
                        ),
                        Positioned(
                          right: 0,
                          top: 0,
                          child: IconButton(
                            visualDensity: VisualDensity.compact,
                            onPressed: () => setState(() => _shots.removeAt(i)),
                            icon: const Icon(Icons.close, color: Colors.white),
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ],
          ],
        ],
      ),
    );
  }
}
