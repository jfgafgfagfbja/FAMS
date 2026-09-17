import 'dart:io';
import 'dart:typed_data';

import 'package:fams_app/features/schedule/schedule_pdf.dart';
import 'package:fams_app/models/models.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pdf/widgets.dart' as pw;

pw.Font _font(String file) => pw.Font.ttf(ByteData.sublistView(File('assets/fonts/$file').readAsBytesSync()));

void main() {
  test('shiftOf splits morning, afternoon, evening', () {
    expect(shiftOf('07:00:00'), 0);
    expect(shiftOf('12:30:00'), 1);
    expect(shiftOf('18:00:00'), 2);
  });

  test('week schedule PDF renders with Vietnamese text', () async {
    final slot = WeekSlot.fromJson({
      'date': '2026-09-17', 'weekday': 3, 'schedule_id': 1, 'class_id': 1,
      'class_code': 'KTPM2026.1', 'subject_name': 'Kiểm thử phần mềm', 'room': 'B204',
      'start_time': '13:30:00', 'end_time': '15:30:00',
    });
    final bytes = await buildWeekSchedulePdf(
      slots: [slot],
      monday: DateTime(2026, 9, 14),
      owner: 'Giảng viên: Nguyễn Văn Giảng (GV01)',
      fonts: PdfFonts(_font('Roboto-Regular.ttf'), _font('Roboto-Bold.ttf')),
    );
    expect(String.fromCharCodes(bytes.take(5)), '%PDF-');
    expect(bytes.length, greaterThan(2000));
  });
}
