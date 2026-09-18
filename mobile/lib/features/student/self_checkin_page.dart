import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:geolocator/geolocator.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/camera_capture.dart';
import '../../widgets/common.dart';

/// SV tu chup selfie diem danh: xin vi tri (co the tu choi), chup, gui len backend -
/// backend chi so khop voi khuon mat cua CHINH SV dang dang nhap.
class SelfCheckinPage extends StatefulWidget {
  const SelfCheckinPage({super.key, required this.sessionId, this.title});

  final int sessionId;
  final String? title;

  @override
  State<SelfCheckinPage> createState() => _SelfCheckinPageState();
}

enum _GeoState { loading, ok, denied, unavailable }

class _SelfCheckinPageState extends State<SelfCheckinPage> {
  final _camera = CameraHandle();
  _GeoState _geoState = _GeoState.loading;
  Position? _position;
  Uint8List? _shot;
  bool _submitting = false;
  SelfCheckinResult? _result;

  @override
  void initState() {
    super.initState();
    _camera.start().then((_) {
      if (mounted) setState(() {});
    });
    _locate();
  }

  @override
  void dispose() {
    _camera.dispose();
    super.dispose();
  }

  Future<void> _locate() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        setState(() => _geoState = _GeoState.unavailable);
        return;
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        if (mounted) setState(() => _geoState = _GeoState.denied);
        return;
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 15)),
      );
      if (mounted) {
        setState(() {
          _position = position;
          _geoState = _GeoState.ok;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _geoState = _GeoState.unavailable);
    }
  }

  Future<void> _capture() async {
    if (!_camera.isReady) return;
    try {
      final bytes = await _camera.capture();
      setState(() => _shot = bytes);
    } catch (e) {
      if (mounted) showSnack(context, 'Không chụp được ảnh: $e', error: true);
    }
  }

  Future<void> _submit() async {
    final shot = _shot;
    if (shot == null) return;
    setState(() => _submitting = true);
    try {
      final data = await context.read<ApiClient>().postMultipart(
        '/sessions/${widget.sessionId}/self-checkin',
        fields: {
          'latitude': _position?.latitude,
          'longitude': _position?.longitude,
          'accuracy': _position?.accuracy,
          'is_mocked': _position?.isMocked ?? false,
        },
        files: [UploadFile('frame', shot, 'selfie.jpg')],
      ) as Json;
      setState(() => _result = SelfCheckinResult.fromJson(data));
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _retake() {
    final relocate = _result?.isLocationProblem ?? false;
    setState(() {
      _shot = null;
      _result = null;
      if (relocate) _geoState = _GeoState.loading;
    });
    if (relocate) _locate();
  }

  Widget _geoBanner() {
    final (icon, text, color) = switch (_geoState) {
      _GeoState.loading => (Icons.location_searching, 'Đang lấy vị trí…', AppColors.neutral),
      _GeoState.ok => (
          Icons.location_on,
          'Đã lấy vị trí (sai số ~${_position!.accuracy.round()}m)${_position!.isMocked ? ' — cảnh báo: vị trí giả lập' : ''}',
          _position!.isMocked ? AppColors.warning : AppColors.success,
        ),
      _GeoState.denied => (Icons.location_off, 'Chưa cấp quyền vị trí — lớp có đối chiếu GPS sẽ không nhận điểm danh', AppColors.warning),
      _GeoState.unavailable => (Icons.location_disabled, 'Không lấy được vị trí (tắt định vị hoặc không hỗ trợ)', AppColors.warning),
    };
    return StatusChip(icon: icon, label: text, color: color);
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return PageBody(
      maxWidth: 520,
      children: [
        if (widget.title != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(widget.title!, textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleMedium),
          ),
        Align(child: _geoBanner()),
        if (_geoState == _GeoState.denied || _geoState == _GeoState.unavailable)
          TextButton.icon(
            onPressed: () {
              setState(() => _geoState = _GeoState.loading);
              _locate();
            },
            icon: const Icon(Icons.my_location),
            label: const Text('Thử lấy lại vị trí'),
          ),
        const SizedBox(height: 12),
        if (result == null) ...[
          if (_shot != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Transform.flip(flipX: _camera.isFront && !kIsWeb, child: Image.memory(_shot!, fit: BoxFit.cover)),
            )
          else
            CameraPreviewBox(handle: _camera),
          const SizedBox(height: 16),
          if (_shot == null)
            FilledButton.icon(
              onPressed: _camera.isReady ? _capture : null,
              icon: const Icon(Icons.camera_alt),
              label: const Text('Chụp ảnh'),
            )
          else
            Row(
              children: [
                Expanded(child: OutlinedButton(onPressed: _submitting ? null : _retake, child: const Text('Chụp lại'))),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: _submitting || _geoState == _GeoState.loading ? null : _submit,
                    child: Text(_submitting ? 'Đang gửi…' : 'Gửi điểm danh'),
                  ),
                ),
              ],
            ),
          if (_camera.cameras.length > 1 && _shot == null)
            TextButton.icon(
              onPressed: () async {
                await _camera.switchCamera();
                if (mounted) setState(() {});
              },
              icon: const Icon(Icons.cameraswitch_outlined),
              label: const Text('Đổi camera'),
            ),
        ] else
          _ResultCard(result: result, onRetry: _retake),
      ],
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({required this.result, required this.onRetry});

  final SelfCheckinResult result;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final success = result.status == 'recognized' || result.status == 'already_checked';
    final (icon, title, color) = switch (result.status) {
      'recognized' => (Icons.check_circle, 'Điểm danh thành công', AppColors.success),
      'already_checked' => (Icons.check_circle_outline, 'Bạn đã điểm danh buổi này', AppColors.success),
      'not_matched' => (Icons.cancel, 'Khuôn mặt không khớp', AppColors.danger),
      'spoof' => (Icons.gpp_bad, 'Ảnh nghi giả mạo', AppColors.danger),
      'out_of_range' => (Icons.wrong_location_outlined, 'Bạn đang ở ngoài khu vực điểm danh', AppColors.danger),
      'location_required' => (Icons.location_off, 'Cần bật định vị để điểm danh', AppColors.warning),
      'location_inaccurate' => (Icons.gps_not_fixed, 'Vị trí chưa đủ chính xác', AppColors.warning),
      'location_mocked' => (Icons.gpp_bad, 'Phát hiện vị trí giả lập', AppColors.danger),
      _ => (Icons.warning_amber_rounded, 'Chưa nhận diện được', AppColors.warning),
    };
    return SectionCard(
      child: Column(
        children: [
          Icon(icon, size: 56, color: color),
          const SizedBox(height: 8),
          Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)),
          if (result.recordStatus != null) ...[
            const SizedBox(height: 8),
            StatusChip.attendance(result.recordStatus),
          ],
          if (result.message.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(result.message, textAlign: TextAlign.center),
          ],
          if (result.confidence > 0) Text('Độ khớp: ${result.confidence.toStringAsFixed(2)}'),
          if (result.distanceM != null)
            Text('Khoảng cách tới địa điểm: ${distanceLabel(result.distanceM)}'
                '${result.allowedRadiusM != null ? ' (cho phép ${distanceLabel(result.allowedRadiusM)})' : ''}'),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            children: [
              if (!success)
                FilledButton(
                  onPressed: onRetry,
                  child: Text(result.isLocationProblem ? 'Lấy lại vị trí và thử lại' : 'Thử lại'),
                ),
              OutlinedButton(onPressed: () => context.go('/schedule'), child: const Text('Về lịch học')),
            ],
          ),
        ],
      ),
    );
  }
}
