import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/app_shell.dart';
import '../../widgets/common.dart';
import '../../widgets/pickers.dart';

/// Thong ke chuyen can tong hop (chi so lieu): admin, P.DT, P.CTSV, Khoa (pham vi Khoa),
/// Ban nganh. Kem loi tat toi cac chuc nang theo vai tro.
class OverviewPage extends StatefulWidget {
  const OverviewPage({super.key, this.showAdminShortcuts = false});

  final bool showAdminShortcuts;

  @override
  State<OverviewPage> createState() => _OverviewPageState();
}

class _OverviewPageState extends State<OverviewPage> {
  String? _semester;

  Future<(Overview, int?)> _load() async {
    final api = context.read<ApiClient>();
    final role = context.read<AuthController>().role;
    final overview = Overview.fromJson(await api.get('/reports/overview', query: {'semester': _semester}) as Json);
    int? pendingFaces;
    if (Perms(role).reviewFaces) {
      pendingFaces = (await api.get('/faces/pending') as List<dynamic>).length;
    }
    return (overview, pendingFaces);
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final me = auth.me!;
    return AsyncLoader<(Overview, int?)>(
      loadKey: _semester,
      load: _load,
      builder: (context, data, reload) {
        final (overview, pendingFaces) = data;
        final t = overview.totals;
        final shortcuts = navItemsFor(auth.role).where((item) => item.path != '/' && item.path != '/account').toList();
        return PageBody(
          maxWidth: 1200,
          onRefresh: reload,
          children: [
            Wrap(
              spacing: 16,
              runSpacing: 12,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Xin chào, ${me.fullName}', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                    Text([Roles.label(me.role), me.unitName].whereType<String>().toSet().join(' · ')),
                  ],
                ),
                SemesterDropdown(value: _semester ?? overview.semester, options: overview.semesters, allowLatest: false, onChanged: (v) => setState(() => _semester = v)),
                StatusChip(icon: Icons.visibility_outlined, label: 'Phạm vi: ${overview.scopeName}', color: AppColors.accent),
              ],
            ),
            const SizedBox(height: 16),
            ResponsiveGrid(
              minItemWidth: 200,
              children: [
                StatCard(label: 'Lớp học phần', value: '${t.classes}', icon: Icons.class_outlined),
                StatCard(label: 'Sinh viên', value: '${t.students}', icon: Icons.school_outlined),
                StatCard(label: 'Giảng viên', value: '${t.lecturers}', icon: Icons.co_present_outlined),
                StatCard(label: 'Buổi đã điểm danh', value: '${t.closedSessions}', icon: Icons.event_available_outlined),
                StatCard(label: 'Tỉ lệ đi học', value: percent(t.attendanceRate), icon: Icons.trending_up, color: AppColors.success),
                StatCard(label: 'Tỉ lệ vắng', value: percent(t.absentRate), icon: Icons.trending_down, color: AppColors.danger),
                StatCard(
                  label: 'SV vượt ngưỡng vắng',
                  value: '${t.warnedStudents}',
                  icon: Icons.warning_amber_rounded,
                  color: t.warnedStudents > 0 ? AppColors.danger : AppColors.success,
                  onTap: Perms(auth.role).viewReports ? () => context.go('/reports') : null,
                ),
                if (pendingFaces != null)
                  StatCard(
                    label: 'Khuôn mặt chờ duyệt',
                    value: '$pendingFaces',
                    icon: Icons.face_outlined,
                    color: pendingFaces > 0 ? AppColors.warning : AppColors.success,
                    onTap: () => context.go('/face-review'),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            LayoutBuilder(builder: (context, constraints) {
              final wide = constraints.maxWidth >= 800;
              final pie = SectionCard(title: 'Phân bổ trạng thái điểm danh', child: _StatusPie(stats: t));
              final bars = SectionCard(title: 'Tỉ lệ đi học theo Khoa', child: _FacultyBars(rows: overview.byFaculty));
              return wide
                  ? Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Expanded(flex: 2, child: pie),
                      const SizedBox(width: 16),
                      Expanded(flex: 3, child: bars),
                    ])
                  : Column(children: [pie, const SizedBox(height: 16), bars]);
            }),
            const SizedBox(height: 16),
            SectionCard(
              title: 'Chi tiết theo Khoa',
              padding: const EdgeInsets.fromLTRB(0, 16, 0, 0),
              child: overview.byFaculty.isEmpty
                  ? const Padding(padding: EdgeInsets.all(16), child: Text('Chưa có lớp học phần trong học kỳ này.'))
                  : SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: DataTable(
                        columns: const [
                          DataColumn(label: Text('Khoa')),
                          DataColumn(label: Text('Lớp'), numeric: true),
                          DataColumn(label: Text('SV'), numeric: true),
                          DataColumn(label: Text('Buổi'), numeric: true),
                          DataColumn(label: Text('Đi học'), numeric: true),
                          DataColumn(label: Text('Vắng'), numeric: true),
                          DataColumn(label: Text('SV cảnh báo'), numeric: true),
                        ],
                        rows: [
                          for (final row in overview.byFaculty)
                            DataRow(cells: [
                              DataCell(Text(row.facultyName)),
                              DataCell(Text('${row.classes}')),
                              DataCell(Text('${row.students}')),
                              DataCell(Text('${row.closedSessions}')),
                              DataCell(Text(percent(row.attendanceRate))),
                              DataCell(Text(percent(row.absentRate))),
                              DataCell(Text('${row.warnedStudents}')),
                            ]),
                        ],
                      ),
                    ),
            ),
            if (shortcuts.isNotEmpty) ...[
              const SizedBox(height: 16),
              SectionCard(
                title: 'Chức năng',
                child: ResponsiveGrid(
                  minItemWidth: 180,
                  children: [
                    for (final item in shortcuts)
                      OutlinedButton.icon(
                        onPressed: () => context.go(item.path),
                        icon: Icon(item.icon),
                        label: Align(alignment: Alignment.centerLeft, child: Text(item.label)),
                      ),
                  ],
                ),
              ),
            ],
          ],
        );
      },
    );
  }
}

class _StatusPie extends StatelessWidget {
  const _StatusPie({required this.stats});

  final OverviewStats stats;

  @override
  Widget build(BuildContext context) {
    final parts = [
      ('Có mặt', stats.present + stats.manual, AppColors.success),
      ('Muộn', stats.late, AppColors.warning),
      ('Vắng', stats.absent, AppColors.danger),
      ('Có phép', stats.excused, AppColors.accent),
    ].where((p) => p.$2 > 0).toList();
    if (parts.isEmpty) return const SizedBox(height: 200, child: Center(child: Text('Chưa có dữ liệu')));
    final total = parts.fold<int>(0, (sum, p) => sum + p.$2);
    return Row(
      children: [
        SizedBox(
          width: 180,
          height: 180,
          child: PieChart(PieChartData(
            sectionsSpace: 2,
            centerSpaceRadius: 36,
            sections: [
              for (final p in parts)
                PieChartSectionData(
                  value: p.$2.toDouble(),
                  color: p.$3,
                  radius: 50,
                  title: '${(p.$2 * 100 / total).round()}%',
                  titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12),
                ),
            ],
          )),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (final p in parts)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(children: [
                    Icon(Icons.circle, size: 12, color: p.$3),
                    const SizedBox(width: 6),
                    Text('${p.$1}: ${p.$2}'),
                  ]),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _FacultyBars extends StatelessWidget {
  const _FacultyBars({required this.rows});

  final List<OverviewFacultyRow> rows;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const SizedBox(height: 200, child: Center(child: Text('Chưa có dữ liệu')));
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    return SizedBox(
      height: 220,
      child: BarChart(BarChartData(
        maxY: 100,
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (group, groupIndex, rod, rodIndex) => BarTooltipItem(
              '${rows[group.x].facultyName}\n${rod.toY.toStringAsFixed(1)}%',
              const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
            ),
          ),
        ),
        gridData: const FlGridData(drawVerticalLine: false, horizontalInterval: 25),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              interval: 25,
              getTitlesWidget: (value, meta) => SideTitleWidget(meta: meta, child: Text('${value.toInt()}%', style: TextStyle(fontSize: 11, color: muted))),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 30,
              getTitlesWidget: (value, meta) {
                final row = rows[value.toInt()];
                return SideTitleWidget(
                  meta: meta,
                  child: Text(row.facultyCode ?? row.facultyName, style: TextStyle(fontSize: 11, color: muted), overflow: TextOverflow.ellipsis),
                );
              },
            ),
          ),
        ),
        barGroups: [
          for (var i = 0; i < rows.length; i++)
            BarChartGroupData(x: i, barRods: [
              BarChartRodData(
                toY: rows[i].attendanceRate * 100,
                width: 22,
                color: rows[i].warnedStudents > 0 ? AppColors.warning : AppColors.success,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
              ),
            ]),
        ],
      )),
    );
  }
}
