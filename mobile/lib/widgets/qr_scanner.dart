import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../core/theme.dart';
import 'common.dart';

/// Mo man quet ma diem danh. Tra ve chuoi ma SV quet duoc hoac go tay, null neu huy.
///
/// Luon kem duong go tay 6 chu so: giang duong lon, ngoi cuoi phong hoac may chieu
/// nhoe thi quet khong an, nhung van doc duoc so.
Future<String?> scanCheckinCode(BuildContext context) {
  return showDialog<String>(
    context: context,
    builder: (context) => const _ScanDialog(),
  );
}

class _ScanDialog extends StatefulWidget {
  const _ScanDialog();

  @override
  State<_ScanDialog> createState() => _ScanDialogState();
}

class _ScanDialogState extends State<_ScanDialog> {
  final _controller = MobileScannerController(detectionSpeed: DetectionSpeed.noDuplicates);
  final _manual = TextEditingController();
  bool _handled = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    _manual.dispose();
    super.dispose();
  }

  void _accept(String value) {
    if (_handled) return;
    _handled = true;
    Navigator.pop(context, value);
  }

  void _onDetect(BarcodeCapture capture) {
    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue;
      if (value != null && value.trim().isNotEmpty) {
        _accept(value.trim());
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Quét mã điểm danh'),
      content: SizedBox(
        width: 420,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Hướng camera vào mã QR đang chiếu trong phòng.'),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: SizedBox(
                  height: 240,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      MobileScanner(
                        controller: _controller,
                        onDetect: _onDetect,
                        errorBuilder: (context, error) => Container(
                          color: Colors.black87,
                          padding: const EdgeInsets.all(20),
                          alignment: Alignment.center,
                          child: Text(
                            'Không mở được camera: ${error.errorCode.name}.\n'
                            'Bạn vẫn có thể nhập 6 chữ số hiện dưới mã QR.',
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.white70),
                          ),
                        ),
                      ),
                      // Khung ngam giua man hinh cho de canh.
                      Center(
                        child: FractionallySizedBox(
                          widthFactor: 0.6,
                          heightFactor: 0.75,
                          child: DecoratedBox(
                            decoration: BoxDecoration(
                              border: Border.all(color: Colors.white70, width: 2),
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Row(
                children: [
                  Expanded(child: Divider()),
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: 8),
                    child: Text('hoặc nhập mã', style: TextStyle(color: AppColors.neutral)),
                  ),
                  Expanded(child: Divider()),
                ],
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _manual,
                keyboardType: TextInputType.number,
                maxLength: 6,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 24, letterSpacing: 8),
                decoration: InputDecoration(
                  hintText: '000000',
                  counterText: '',
                  errorText: _error,
                ),
                onSubmitted: (_) => _submitManual(),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Hủy')),
        FilledButton(onPressed: _submitManual, child: const Text('Dùng mã đã nhập')),
      ],
    );
  }

  void _submitManual() {
    final value = _manual.text.trim();
    if (value.length != 6 || int.tryParse(value) == null) {
      setState(() => _error = 'Mã gồm 6 chữ số');
      return;
    }
    _accept(value);
  }
}

/// Dong trang thai cho biet SV da co ma hay chua, kem nut quet.
class CheckinCodeBanner extends StatelessWidget {
  const CheckinCodeBanner({super.key, required this.hasCode, required this.onScan});

  final bool hasCode;
  final VoidCallback onScan;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Align(
          child: StatusChip(
            icon: hasCode ? Icons.qr_code_scanner : Icons.qr_code_2,
            label: hasCode
                ? 'Đã có mã điểm danh của buổi này'
                : 'Buổi này cần quét mã QR đang chiếu trong phòng',
            color: hasCode ? AppColors.success : AppColors.warning,
          ),
        ),
        TextButton.icon(
          onPressed: onScan,
          icon: const Icon(Icons.qr_code_scanner),
          label: Text(hasCode ? 'Quét lại mã' : 'Quét mã QR'),
        ),
      ],
    );
  }
}
