import 'package:fams_app/models/models.dart';
import 'package:fams_app/widgets/qr_scanner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('CheckinCode doc du truong tu backend', () {
    final code = CheckinCode.fromJson(const {
      'session_id': 7,
      'qr_payload': 'FAMS:7:58123:ab12cd34ef56',
      'digits': '048217',
      'rotate_seconds': 30,
      'expires_in_seconds': 12,
    });

    expect(code.sessionId, 7);
    expect(code.qrPayload, 'FAMS:7:58123:ab12cd34ef56');
    expect(code.digits, '048217');
    expect(code.rotateSeconds, 30);
    expect(code.expiresInSeconds, 12);
  });

  test('ket qua diem danh phan biet loi ma QR voi loi vi tri', () {
    SelfCheckinResult of(String status) => SelfCheckinResult.fromJson({'status': status});

    expect(of('qr_required').isQrProblem, isTrue);
    expect(of('qr_invalid').isQrProblem, isTrue);
    expect(of('out_of_range').isQrProblem, isFalse);
    expect(of('out_of_range').isLocationProblem, isTrue);
    expect(of('recognized').isQrProblem, isFalse);
    expect(of('qr_required').isLocationProblem, isFalse);
  });

  testWidgets('bang bao ma doi chu theo viec da quet hay chua', (tester) async {
    var scans = 0;
    Widget banner(bool hasCode) => MaterialApp(
          home: Scaffold(
            body: CheckinCodeBanner(hasCode: hasCode, onScan: () => scans++),
          ),
        );

    await tester.pumpWidget(banner(false));
    expect(find.text('Buổi này cần quét mã QR đang chiếu trong phòng'), findsOneWidget);
    await tester.tap(find.text('Quét mã QR'));
    expect(scans, 1);

    await tester.pumpWidget(banner(true));
    expect(find.text('Đã có mã điểm danh của buổi này'), findsOneWidget);
    expect(find.text('Quét lại mã'), findsOneWidget);
  });
}
