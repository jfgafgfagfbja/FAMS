import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';

/// Bao cao chuyen can theo lop: thong ke tung SV, loc SV canh bao, xuat Excel.
class ReportsPage extends StatefulWidget {
  const ReportsPage({super.key, this.initialClassId});

  final int? initialClassId;

  @override
  State<ReportsPage> createState() => _ReportsPageState();
}

class _ReportsPageState extends State<ReportsPage> {
  late int? _classId = widget.initialClassId;
  bool _onlyWarnings = false;
  bool _exporting = false;

  Future<List<ClassInfo>> _loadClasses() async {
    final page = await context.read<ApiClient>().getPage('/classes');
    final classes = page.items.map(ClassInfo.fromJson).toList();
    if (_classId == null && classes.isNotEmpty) _classId = classes.first.id;
    return classes;
  }

  Future<void> _export(ClassInfo clazz) async {
    setState(() => _exporting = true);
    try {
      final bytes = await context.read<ApiClient>().getBytes('/reports/attendance/export', query: {
        'class_id': clazz.id,
        'semester': clazz.semester,
      });
      final filename = 'diemdanh_${clazz.classCode}_${clazz.semester}.xlsx';
      await SharePlus.instance.share(ShareParams(
        files: [XFile.fromData(bytes, name: filename, mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')],
        fileNameOverrides: [filename],
        subject: 'Báo cáo điểm danh ${clazz.classCode}',
      ));
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<List<ClassInfo>>(
      load: _loadClasses,
      builder: (context, classes, _) {
        if (classes.isEmpty) {
          return const EmptyView(icon: Icons.class_outlined, message: 'Không có lớp học phần nào trong phạm vi của bạn.');
        }
        final clazz = classes.firstWhere((c) => c.id == _classId, orElse: () => classes.first);
        return PageBody(
          maxWidth: 1100,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                SizedBox(
                  width: 380,
                  child: DropdownButtonFormField<int>(
                    initialValue: clazz.id,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Lớp học phần'),
                    items: [
                      for (final c in classes)
                        DropdownMenuItem(value: c.id, child: Text('${c.classCode} — ${c.subjectName} (${formatSemester(c.semester)})', overflow: TextOverflow.ellipsis)),
                    ],
                    onChanged: (v) => setState(() => _classId = v),
                  ),
                ),
                FilterChip(label: const Text('Chỉ SV cảnh báo'), selected: _onlyWarnings, onSelected: (v) => setState(() => _onlyWarnings = v)),
                FilledButton.icon(
                  onPressed: _exporting ? null : () => _export(clazz),
                  icon: const Icon(Icons.file_download_outlined),
                  label: Text(_exporting ? 'Đang xuất…' : 'Xuất Excel'),
                ),
                OutlinedButton.icon(
                  onPressed: () => context.push('/classes/${clazz.id}'),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('Chi tiết lớp'),
                ),
              ],
            ),
            const SizedBox(height: 16),
            AsyncLoader<List<ClassStatRow>>(
              loadKey: clazz.id,
              load: () async {
                final data = await context.read<ApiClient>().get('/reports/attendance/${clazz.id}') as List<dynamic>;
                return data.map((e) => ClassStatRow.fromJson(e as Json)).toList();
              },
              builder: (context, rows, _) {
                final visible = _onlyWarnings ? rows.where((r) => r.warning).toList() : rows;
                if (visible.isEmpty) {
                  return EmptyView(
                    icon: Icons.insights_outlined,
                    message: rows.isEmpty ? 'Lớp chưa có buổi điểm danh nào đã đóng.' : 'Không có sinh viên vượt ngưỡng vắng.',
                  );
                }
                return Card(
                  clipBehavior: Clip.antiAlias,
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('MSSV')),
                        DataColumn(label: Text('Họ tên')),
                        DataColumn(label: Text('Có mặt'), numeric: true),
                        DataColumn(label: Text('Muộn'), numeric: true),
                        DataColumn(label: Text('Vắng'), numeric: true),
                        DataColumn(label: Text('Có phép'), numeric: true),
                        DataColumn(label: Text('% vắng'), numeric: true),
                      ],
                      rows: [
                        for (final r in visible)
                          DataRow(
                            color: r.warning ? WidgetStatePropertyAll(AppColors.danger.withValues(alpha: 0.08)) : null,
                            cells: [
                              DataCell(Text(r.studentCode)),
                              DataCell(Text(r.fullName)),
                              DataCell(Text('${r.present + r.manual}')),
                              DataCell(Text('${r.late}')),
                              DataCell(Text('${r.absent}')),
                              DataCell(Text('${r.excused}')),
                              DataCell(Text(percent(r.absentRatio), style: TextStyle(color: r.warning ? AppColors.danger : null, fontWeight: FontWeight.w600))),
                            ],
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ],
        );
      },
    );
  }
}
