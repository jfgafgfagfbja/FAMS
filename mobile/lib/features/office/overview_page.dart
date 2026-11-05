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
import '../../widgets/dashboard.dart';
import '../../widgets/pickers.dart';

/// Trang chu cua can bo: thong ke chuyen can tong hop (chi so lieu) cho admin, P.DT, P.CTSV,
/// Khoa (pham vi Khoa), Ban nganh, kem loi tat toi cac chuc nang theo vai tro.
class OverviewPage extends StatefulWidget {
  const OverviewPage({super.key});

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
        final wide = isWideScreen(context);
        final perms = Perms(auth.role);
        final shortcuts = shortcutsFor(auth.role);
        final warnedOnTap = perms.viewReports ? () => context.go('/reports') : null;

        final profile = ProfileCard(
          title: 'Thông tin cán bộ',
          name: me.fullName,
          onDetail: () => context.go('/account'),
          trailing: SemesterDropdown(
            value: _semester ?? overview.semester,
            options: overview.semesters,
            allowLatest: false,
            width: 200,
            onChanged: (v) => setState(() => _semester = v),
          ),
          fields: [
            ('Họ tên', me.fullName),
            ('Email', me.email),
            ('Vai trò', Roles.label(me.role)),
            if (me.unitName != null) ('Đơn vị', me.unitName!),
            if (me.position != null && me.position!.isNotEmpty) ('Chức vụ', me.position!),
            ('Phạm vi', overview.scopeName),
          ],
        );
        // O tren cung la viec dang cho xu ly: khuon mat cho duyet neu vai tro duoc duyet,
        // con lai la sinh vien vuot nguong vang.
        final tiles = TileColumn(
          top: pendingFaces != null
              ? DashTile(
                  label: 'Khuôn mặt chờ duyệt',
                  value: '$pendingFaces',
                  icon: Icons.face_outlined,
                  onTap: () => context.go('/face-review'),
                )
              : DashTile(
                  label: 'Sinh viên vượt ngưỡng vắng',
                  value: '${t.warnedStudents}',
                  icon: Icons.warning_amber_rounded,
                  onTap: warnedOnTap,
                ),
          left: DashTile(label: 'Tỉ lệ đi học', value: percent(t.attendanceRate), icon: Icons.trending_up, tone: TileTone.blue),
          right: pendingFaces != null
              ? DashTile(
                  label: 'SV vượt ngưỡng vắng',
                  value: '${t.warnedStudents}',
                  icon: Icons.warning_amber_rounded,
                  tone: TileTone.amber,
                  onTap: warnedOnTap,
                )
              : DashTile(label: 'Tỉ lệ vắng', value: percent(t.absentRate), icon: Icons.trending_down, tone: TileTone.amber),
        );
        final stats = ResponsiveGrid(
          minItemWidth: 200,
          maxColumns: 4,
          spacing: kCardGap,
          children: [
            StatCard(label: 'Lớp học phần', value: '${t.classes}', icon: Icons.class_outlined),
            StatCard(label: 'Sinh viên', value: '${t.students}', icon: Icons.school_outlined),
            StatCard(label: 'Giảng viên', value: '${t.lecturers}', icon: Icons.co_present_outlined),
            StatCard(label: 'Buổi đã điểm danh', value: '${t.closedSessions}', icon: Icons.event_available_outlined),
          ],
        );
        final charts = CardRow(
          flexes: const [3, 2],
          children: [
            SectionCard(title: 'Tỉ lệ đi học theo Khoa', child: _FacultyBars(rows: overview.byFaculty)),
            SectionCard(title: 'Phân bổ trạng thái điểm danh', child: _StatusPie(stats: t)),
          ],
        );
        final table = SectionCard(
          title: 'Chi tiết theo Khoa',
          child: overview.byFaculty.isEmpty
              ? const Text('Chưa có lớp học phần trong học kỳ này.')
              : LayoutBuilder(
                  builder: (context, constraints) => SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: ConstrainedBox(
                      constraints: BoxConstraints(minWidth: constraints.maxWidth),
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
                ),
        );
        const gap = SizedBox(height: kCardGap);
        final grid = shortcuts.isEmpty ? null : ShortcutGrid(items: shortcuts);
        return PageBody(
          onRefresh: reload,
          children: [
            CardRow(flexes: const [7, 5], children: [profile, tiles]),
            gap,
            // Man hinh rong: loi tat ngay duoi the thong tin. Dien thoai da co ngan keo nen
            // day xuong cuoi, de so lieu len tren.
            if (wide && grid != null) ...[grid, gap],
            stats,
            gap,
            charts,
            gap,
            table,
            if (!wide && grid != null) ...[gap, grid],
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
                    Flexible(child: Text('${p.$1}: ${p.$2}')),
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
