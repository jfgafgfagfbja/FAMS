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
import '../../widgets/qr_scanner.dart';

/// SV tu chup selfie diem danh: xin vi tri (co the tu choi), chup, gui len backend -
/// backend chi so khop voi khuon mat cua CHINH SV dang dang nhap.
class SelfCheckinPage extends StatefulWidget {
  const SelfCheckinPage({super.key, required this.sessionId, this.title, this.initialCode});

  final int sessionId;
  final String? title;

  /// Ma lay san tu link trong anh QR.
  final String? initialCode;

  @override
  State<SelfCheckinPage> createState() => _SelfCheckinPageState();
}

/// `denied`: tu choi mot lan, hoi lai duoc. `blocked`: tu choi vinh vien, chi con
/// duong vao cai dat he thong. `unavailable`: may da tat dinh vi hoac khong ho tro.
enum _GeoState { loading, ok, denied, blocked, unavailable }

class _SelfCheckinPageState extends State<SelfCheckinPage>
    with WidgetsBindingObserver, CameraLifecycleMixin {
  final _camera = CameraHandle();

  @override
  CameraHandle get camera => _camera;
  _GeoState _geoState = _GeoState.loading;
  Position? _position;
  /// Buoi nay co bat buoc quet ma QR khong (hoi backend luc mo man hinh).
  late bool _requireQr = widget.initialCode != null;
  late String? _scannedCode = widget.initialCode;
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
    _loadCheckinInfo();
  }

  Future<void> _loadCheckinInfo() async {
    try {
      final data = await context.read<ApiClient>().get(
          '/sessions/${widget.sessionId}/checkin-info') as Json;
      if (mounted) setState(() => _requireQr = data['require_qr'] == true);
    } catch (_) {
      // Khong lay duoc thi cu de SV chup binh thuong; backend van chan neu thieu ma.
    }
  }

  Future<void> _scanCode() async {
    // Dien thoai thuong khong mo duoc hai camera cung luc: nha camera chup mat cho may quet ma.
    await _camera.suspend();
    if (!mounted) return;
    final code = await scanCheckinCode(context);
    await _camera.resume();
    if (!mounted) return;
    setState(() {
      if (code != null) _scannedCode = code;
    });
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
      if (permission == LocationPermission.deniedForever) {
        if (mounted) setState(() => _geoState = _GeoState.blocked);
        return;
      }
      if (permission == LocationPermission.denied) {
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
          if (_scannedCode != null) 'checkin_code': _scannedCode,
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
    final badCode = _result?.isQrProblem ?? false;
    setState(() {
      _shot = null;
      _result = null;
      if (relocate) _geoState = _GeoState.loading;
      if (badCode) {
        // Ma het han hoac sai buoi: bo ma cu di de SV quet lai ma dang chieu.
        _scannedCode = null;
        _requireQr = true;
      }
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
      _GeoState.blocked => (
          Icons.location_off,
          'Quyền vị trí đang bị chặn — mở cài đặt ứng dụng để bật lại, lớp có đối chiếu GPS sẽ không nhận điểm danh',
          AppColors.warning,
        ),
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
        if (_geoState == _GeoState.denied || _geoState == _GeoState.blocked || _geoState == _GeoState.unavailable)
          Wrap(
            alignment: WrapAlignment.center,
            children: [
              TextButton.icon(
                onPressed: () {
                  setState(() => _geoState = _GeoState.loading);
                  _locate();
                },
                icon: const Icon(Icons.my_location),
                label: const Text('Thử lấy lại vị trí'),
              ),
              // Tu choi vinh vien thi hoi lai khong hien hop thoai nua, phai vao cai dat.
              if (!kIsWeb && _geoState == _GeoState.blocked)
                TextButton.icon(
                  onPressed: Geolocator.openAppSettings,
                  icon: const Icon(Icons.settings_outlined),
                  label: const Text('Mở cài đặt ứng dụng'),
                ),
              if (!kIsWeb && _geoState == _GeoState.unavailable)
                TextButton.icon(
                  onPressed: Geolocator.openLocationSettings,
                  icon: const Icon(Icons.settings_outlined),
                  label: const Text('Mở cài đặt định vị'),
                ),
            ],
          ),
        const SizedBox(height: 12),
        if (result == null) ...[
          if (_requireQr) ...[
            CheckinCodeBanner(hasCode: _scannedCode != null, onScan: _scanCode),
            const SizedBox(height: 8),
          ],
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
                    onPressed: _submitting ||
                            _geoState == _GeoState.loading ||
                            (_requireQr && _scannedCode == null)
                        ? null
                        : _submit,
                    child: Text(_submitting
                        ? 'Đang gửi…'
                        : (_requireQr && _scannedCode == null) ? 'Cần quét mã QR' : 'Gửi điểm danh'),
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
      'qr_required' => (Icons.qr_code_2, 'Buổi này cần quét mã QR trong phòng', AppColors.warning),
      'qr_invalid' => (Icons.qr_code_scanner, 'Mã QR đã hết hạn hoặc không đúng buổi', AppColors.warning),
      'consent_required' => (Icons.privacy_tip_outlined, 'Bạn chưa đồng ý sử dụng dữ liệu khuôn mặt', AppColors.warning),
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
              // Chua dong y thi thu lai cung vo ich: dua toi muc Khuon mat de doc va dong y.
              if (result.status == 'consent_required')
                FilledButton(onPressed: () => context.go('/face'), child: const Text('Đọc và đồng ý'))
              else if (!success)
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
