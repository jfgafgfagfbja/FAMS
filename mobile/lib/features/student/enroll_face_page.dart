import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/camera_capture.dart';
import '../../widgets/common.dart';
import '../../widgets/consent_form.dart';

const _poses = [
  ('front', 'Chụp thẳng', 'Nhìn thẳng vào camera, giữ khuôn mặt trong khung bầu dục.'),
  ('left', 'Nghiêng trái', 'Nghiêng đầu nhẹ sang trái, vẫn giữ mặt trong khung.'),
  ('right', 'Nghiêng phải', 'Nghiêng đầu nhẹ sang phải, vẫn giữ mặt trong khung.'),
];

/// SV tu dang ky khuon mat (BAT BUOC dong y truoc -> 3 tu the) va quan ly du lieu cua minh:
/// xem trang thai, rut dong y (xoa ngay toan bo du lieu khuon mat).
class EnrollFacePage extends StatefulWidget {
  const EnrollFacePage({super.key});

  @override
  State<EnrollFacePage> createState() => _EnrollFacePageState();
}

class _EnrollFacePageState extends State<EnrollFacePage> {
  List<FaceMine> _faces = const [];
  bool _loading = true;
  String? _error;
  bool _wizard = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final auth = context.read<AuthController>();
      final results = await Future.wait([
        context.read<ApiClient>().get('/faces/mine'),
        auth.reloadMe(),
      ]);
      _faces = (results[0] as List<dynamic>).map((e) => FaceMine.fromJson(e as Json)).toList();
    } catch (e) {
      _error = errorText(e);
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _withdraw(int studentId) async {
    final ok = await confirmDialog(
      context,
      title: 'Rút đồng ý sử dụng dữ liệu khuôn mặt?',
      message: 'Toàn bộ ảnh và đặc trưng khuôn mặt của bạn sẽ bị xóa ngay. Bạn sẽ KHÔNG điểm danh '
          'bằng khuôn mặt được cho tới khi đồng ý và đăng ký lại; giảng viên vẫn có thể xác nhận '
          'có mặt cho bạn trực tiếp.',
      confirmLabel: 'Rút đồng ý',
      destructive: true,
    );
    if (!ok || !mounted) return;
    final done = await runAction(context, () => context.read<ApiClient>().post('/students/$studentId/consent/withdraw'),
        success: 'Đã rút đồng ý và xóa dữ liệu khuôn mặt');
    if (done) _load();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return ErrorView(message: _error!, onRetry: _load);
    final me = context.watch<AuthController>().me!;

    // Noi dung dong y da doi phien ban: doc va xac nhan lai (khong phai chup lai anh).
    if (me.consentGiven == true && me.consentOutdated && !_wizard) {
      return PageBody(
        maxWidth: 640,
        children: [
          ConsentForm(
            studentId: me.studentId!,
            notice: 'Nội dung đồng ý sử dụng dữ liệu khuôn mặt đã được cập nhật. '
                'Vui lòng đọc lại và xác nhận, hoặc rút đồng ý nếu bạn không còn đồng ý.',
            onDone: _load,
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => _withdraw(me.studentId!),
            style: TextButton.styleFrom(foregroundColor: AppColors.danger),
            child: const Text('Không đồng ý — rút đồng ý và xóa dữ liệu khuôn mặt'),
          ),
        ],
      );
    }

    if (_wizard || me.consentGiven != true) {
      return _EnrollWizard(
        studentId: me.studentId!,
        consentGiven: me.consentGiven == true,
        onFinished: () {
          setState(() => _wizard = false);
          _load();
        },
      );
    }

    return PageBody(
      maxWidth: 640,
      onRefresh: _load,
      children: [
        SectionCard(
          title: 'Trạng thái khuôn mặt',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              StatusChip(label: faceStatusLabel(me.faceStatus), color: statusColor(me.faceStatus == 'none' ? null : me.faceStatus)),
              const SizedBox(height: 8),
              Text(switch (me.faceStatus) {
                'approved' => 'Bạn đã có thể điểm danh bằng khuôn mặt.',
                'pending' => 'Ảnh đang chờ cán bộ duyệt. Sau khi được duyệt bạn mới điểm danh bằng khuôn mặt được.',
                'rejected' => 'Ảnh bị từ chối, hãy xem lý do bên dưới và đăng ký lại.',
                _ => 'Bạn chưa đăng ký khuôn mặt.',
              }),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () => setState(() => _wizard = true),
                icon: const Icon(Icons.add_a_photo_outlined),
                label: Text(_faces.isEmpty ? 'Đăng ký khuôn mặt' : 'Đăng ký thêm ảnh'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Đồng ý sử dụng dữ liệu khuôn mặt',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Bạn đã đồng ý cho FAMS dùng dữ liệu khuôn mặt để điểm danh. Bạn có thể rút '
                  'đồng ý bất kỳ lúc nào — toàn bộ ảnh và đặc trưng khuôn mặt sẽ bị xóa ngay.'),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton.icon(
                  onPressed: () => _withdraw(me.studentId!),
                  style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
                  icon: const Icon(Icons.no_accounts_outlined),
                  label: const Text('Rút đồng ý & xóa dữ liệu'),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Dữ liệu của tôi',
          child: _faces.isEmpty
              ? const Text('Chưa có ảnh khuôn mặt nào.')
              : Column(
                  children: [
                    for (final face in _faces)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.face_outlined),
                        title: Text('Đăng ký lúc ${fmtDateTime(face.createdAt)}'),
                        subtitle: face.rejectReason.isEmpty ? null : Text('Lý do từ chối: ${face.rejectReason}'),
                        trailing: StatusChip(
                          label: switch (face.status) { 'approved' => 'Đã duyệt', 'rejected' => 'Từ chối', _ => 'Chờ duyệt' },
                          color: statusColor(face.status),
                        ),
                      ),
                  ],
                ),
        ),
      ],
    );
  }
}

class _EnrollWizard extends StatefulWidget {
  const _EnrollWizard({required this.studentId, required this.consentGiven, required this.onFinished});

  final int studentId;
  final bool consentGiven;
  final VoidCallback onFinished;

  @override
  State<_EnrollWizard> createState() => _EnrollWizardState();
}

class _EnrollWizardState extends State<_EnrollWizard>
    with WidgetsBindingObserver, CameraLifecycleMixin {
  final _camera = CameraHandle();

  @override
  CameraHandle get camera => _camera;
  late int _step = widget.consentGiven ? 1 : 0; // 0 = dong y, 1..3 = tu the, 4 = xong
  bool _busy = false;
  Uint8List? _shot;
  String? _stepError;
  bool _stepDone = false;
  int _saved = 0;

  @override
  void initState() {
    super.initState();
    if (_step >= 1) _startCamera();
  }

  @override
  void dispose() {
    _camera.dispose();
    super.dispose();
  }

  Future<void> _startCamera() async {
    await _camera.start();
    if (mounted) setState(() {});
  }

  Future<void> _consented() async {
    await context.read<AuthController>().reloadMe();
    if (!mounted) return;
    setState(() => _step = 1);
    _startCamera();
  }

  Future<void> _captureAndSend() async {
    if (!_camera.isReady) return;
    setState(() {
      _busy = true;
      _stepError = null;
    });
    final api = context.read<ApiClient>();
    try {
      final bytes = await _camera.capture();
      setState(() => _shot = bytes);
      final pose = _poses[_step - 1].$1;
      final data = await api.postMultipart(
        '/faces/enroll/${widget.studentId}',
        files: [UploadFile('images', bytes, '$pose.jpg')],
      ) as Json;
      if (data['ok'] == true) {
        _stepDone = true;
        _saved++;
      } else {
        _stepError = (data['message'] as String? ?? '').replaceFirst(RegExp(r'^[^:]+: '), '');
      }
    } catch (e) {
      _stepError = errorText(e);
    }
    if (mounted) setState(() => _busy = false);
  }

  void _next() => setState(() {
        _step++;
        _shot = null;
        _stepDone = false;
        _stepError = null;
      });

  @override
  Widget build(BuildContext context) {
    return PageBody(
      maxWidth: 560,
      children: [
        Row(
          children: [
            for (var i = 0; i < 4; i++) ...[
              CircleAvatar(
                radius: 14,
                backgroundColor: i < _step ? AppColors.success : (i == _step ? AppColors.brand : Colors.grey.shade400),
                child: i < _step
                    ? const Icon(Icons.check, size: 16, color: Colors.white)
                    : Text('${i + 1}', style: const TextStyle(color: Colors.white, fontSize: 12)),
              ),
              if (i < 3) Expanded(child: Divider(color: i < _step ? AppColors.success : null)),
            ],
          ],
        ),
        const SizedBox(height: 16),
        if (_step == 0)
          ConsentForm(studentId: widget.studentId, onDone: _consented)
        else if (_step <= 3) ...[
          Text(_poses[_step - 1].$2, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          Text(_poses[_step - 1].$3),
          const SizedBox(height: 12),
          if (_shot != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Transform.flip(flipX: _camera.isFront && !kIsWeb, child: Image.memory(_shot!)),
            )
          else
            CameraPreviewBox(handle: _camera),
          if (_busy) const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator()),
          if (_stepError != null)
            Padding(padding: const EdgeInsets.only(top: 8), child: Text(_stepError!, style: const TextStyle(color: AppColors.danger))),
          const SizedBox(height: 12),
          if (_stepDone)
            FilledButton(onPressed: _next, child: Text(_step < 3 ? 'Tiếp theo' : 'Hoàn tất'))
          else if (_shot != null && !_busy)
            OutlinedButton(onPressed: () => setState(() => _shot = null), child: const Text('Chụp lại'))
          else
            FilledButton.icon(
              onPressed: _busy || !_camera.isReady ? null : _captureAndSend,
              icon: const Icon(Icons.camera_alt),
              label: const Text('Chụp'),
            ),
        ] else
          SectionCard(
            child: Column(
              children: [
                const Icon(Icons.hourglass_top, size: 48, color: AppColors.warning),
                const SizedBox(height: 8),
                Text('Đã lưu $_saved/3 ảnh — đang chờ duyệt', style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 8),
                const Text('Cán bộ sẽ duyệt sớm. Bạn điểm danh bằng khuôn mặt được sau khi ảnh được duyệt.', textAlign: TextAlign.center),
                const SizedBox(height: 16),
                FilledButton(onPressed: widget.onFinished, child: const Text('Xong')),
              ],
            ),
          ),
      ],
    );
  }
}
