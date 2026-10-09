import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Man hinh giang vien chieu len may chieu/TV trong phong. Ma tu doi sau moi chu ky
/// nen anh chup man hinh gui ra ngoai chi dung duoc trong giay lat.
class CheckinQrPage extends StatefulWidget {
  const CheckinQrPage({super.key, required this.sessionId});

  final int sessionId;

  @override
  State<CheckinQrPage> createState() => _CheckinQrPageState();
}

class _CheckinQrPageState extends State<CheckinQrPage> {
  CheckinCode? _code;
  String? _error;
  int _remaining = 0;
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _load();
    // Dem lui tung giay; het gio thi lay ma moi.
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      if (_remaining <= 1) {
        _load();
      } else {
        setState(() => _remaining--);
      }
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data = await context.read<ApiClient>().get('/sessions/${widget.sessionId}/checkin-code');
      if (!mounted) return;
      final code = CheckinCode.fromJson(data as Json);
      setState(() {
        _code = code;
        _error = null;
        // Lay them 1 giay de khong nhap nhay dung luc giao giua hai chu ky.
        _remaining = code.expiresInSeconds + 1;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = errorText(e);
        _remaining = 5; // thu lai sau vai giay
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final code = _code;
    if (_error != null && code == null) {
      return PageBody(children: [ErrorView(message: _error!, onRetry: _load)]);
    }
    if (code == null) {
      return const PageBody(children: [Center(child: CircularProgressIndicator())]);
    }

    final progress = code.rotateSeconds == 0 ? 0.0 : _remaining / code.rotateSeconds;
    return PageBody(
      maxWidth: 560,
      children: [
        const Text(
          'Chiếu màn hình này lên máy chiếu trong phòng. Sinh viên mở mục Tự điểm danh, '
          'quét mã rồi chụp ảnh khuôn mặt.',
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        Center(
          child: Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
            ),
            child: QrImageView(
              data: code.qrPayload,
              size: 260,
              backgroundColor: Colors.white,
              // Mo rong vung sua loi: may chieu mo hoac anh sang chenh van quet duoc.
              errorCorrectionLevel: QrErrorCorrectLevel.Q,
            ),
          ),
        ),
        const SizedBox(height: 20),
        Center(
          child: Column(
            children: [
              const Text('Hoặc nhập mã', style: TextStyle(color: AppColors.neutral)),
              const SizedBox(height: 4),
              Text(
                // Tach 3-3 cho de doc tu xa.
                '${code.digits.substring(0, 3)} ${code.digits.substring(3)}',
                style: const TextStyle(fontSize: 44, fontWeight: FontWeight.bold, letterSpacing: 6),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        LinearProgressIndicator(value: progress.clamp(0, 1)),
        const SizedBox(height: 6),
        Center(
          child: Text(
            _error != null ? 'Mất kết nối, đang thử lại…' : 'Mã tự đổi sau $_remaining giây',
            style: TextStyle(color: _error != null ? AppColors.danger : AppColors.neutral),
          ),
        ),
      ],
    );
  }
}
