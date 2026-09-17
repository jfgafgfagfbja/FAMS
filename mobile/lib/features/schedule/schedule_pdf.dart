import 'package:flutter/services.dart' show rootBundle;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import '../../core/formatters.dart';
import '../../models/models.dart';

const shiftLabels = ['Sáng', 'Chiều', 'Tối'];

/// 0 = sang (truoc 12h), 1 = chieu (truoc 18h), 2 = toi.
int shiftOf(String startTime) {
  final hour = int.tryParse(startTime.split(':').first) ?? 0;
  return hour < 12 ? 0 : (hour < 18 ? 1 : 2);
}

/// Font co day du dau tieng Viet (Roboto, Apache 2.0 - assets/fonts). Font mac dinh
/// cua goi pdf (Helvetica) khong co glyph tieng Viet.
class PdfFonts {
  const PdfFonts(this.regular, this.bold);

  final pw.Font regular;
  final pw.Font bold;

  static Future<PdfFonts> load() async => PdfFonts(
        pw.Font.ttf(await rootBundle.load('assets/fonts/Roboto-Regular.ttf')),
        pw.Font.ttf(await rootBundle.load('assets/fonts/Roboto-Bold.ttf')),
      );
}

bool _sameDay(DateTime a, DateTime b) => a.year == b.year && a.month == b.month && a.day == b.day;

/// Thoi khoa bieu tuan dang luoi Sang/Chieu/Toi x Thu 2..CN (kho A4 ngang) de in.
Future<List<int>> buildWeekSchedulePdf({
  required List<WeekSlot> slots,
  required DateTime monday,
  required String owner,
  required PdfFonts fonts,
  PdfPageFormat format = PdfPageFormat.a4,
}) async {
  final days = List.generate(7, (i) => monday.add(Duration(days: i)));
  final doc = pw.Document(
    title: 'Lịch tuần ${fmtDate(days.first)}',
    author: 'FAMS',
    theme: pw.ThemeData.withFont(base: fonts.regular, bold: fonts.bold),
  );
  const brand = PdfColor.fromInt(0xFF8E1B2E);

  pw.Widget headerCell(String text) => pw.Padding(
        padding: const pw.EdgeInsets.all(4),
        child: pw.Text(text, textAlign: pw.TextAlign.center, style: pw.TextStyle(fontSize: 8.5, fontWeight: pw.FontWeight.bold)),
      );

  doc.addPage(pw.Page(
    pageFormat: format.landscape,
    margin: const pw.EdgeInsets.all(20),
    build: (context) => pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Text(
          'THỜI KHÓA BIỂU TUẦN ${fmtDate(days.first)} – ${fmtDate(days.last)}',
          style: pw.TextStyle(fontSize: 14, fontWeight: pw.FontWeight.bold, color: brand),
        ),
        pw.Text(owner, style: const pw.TextStyle(fontSize: 10)),
        pw.SizedBox(height: 10),
        pw.Table(
          border: pw.TableBorder.all(color: PdfColors.grey600, width: 0.5),
          columnWidths: const {0: pw.FixedColumnWidth(44)},
          defaultColumnWidth: const pw.FlexColumnWidth(),
          children: [
            pw.TableRow(
              decoration: const pw.BoxDecoration(color: PdfColors.grey200),
              children: [
                headerCell('Ca'),
                for (final day in days) headerCell('${weekdayLabel(day.weekday - 1)}\n${fmtDate(day)}'),
              ],
            ),
            for (var shift = 0; shift < shiftLabels.length; shift++)
              pw.TableRow(
                children: [
                  pw.Container(
                    height: 110,
                    alignment: pw.Alignment.center,
                    child: pw.Text(shiftLabels[shift], style: pw.TextStyle(fontSize: 9, fontWeight: pw.FontWeight.bold)),
                  ),
                  for (final day in days)
                    pw.Padding(
                      padding: const pw.EdgeInsets.all(3),
                      child: pw.Column(
                        crossAxisAlignment: pw.CrossAxisAlignment.start,
                        children: [
                          for (final slot in slots.where((s) => _sameDay(s.date, day) && shiftOf(s.startTime) == shift))
                            pw.Container(
                              margin: const pw.EdgeInsets.only(bottom: 4),
                              padding: const pw.EdgeInsets.only(left: 4),
                              decoration: const pw.BoxDecoration(
                                border: pw.Border(left: pw.BorderSide(color: brand, width: 2)),
                              ),
                              child: pw.Column(
                                crossAxisAlignment: pw.CrossAxisAlignment.start,
                                children: [
                                  pw.Text(slot.classCode, style: pw.TextStyle(fontSize: 8, fontWeight: pw.FontWeight.bold)),
                                  pw.Text(slot.subjectName, style: const pw.TextStyle(fontSize: 7.5)),
                                  pw.Text('${hhmm(slot.startTime)}–${hhmm(slot.endTime)} · Phòng ${slot.room}',
                                      style: const pw.TextStyle(fontSize: 7)),
                                ],
                              ),
                            ),
                        ],
                      ),
                    ),
                ],
              ),
          ],
        ),
        pw.SizedBox(height: 8),
        pw.Text('In từ FAMS lúc ${fmtDateTime(DateTime.now())}',
            style: const pw.TextStyle(fontSize: 7, color: PdfColors.grey700)),
      ],
    ),
  ));
  return doc.save();
}
