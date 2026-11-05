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
import '../office/overview_page.dart';
import '../parent/children_page.dart';
import '../schedule/week_schedule_page.dart' show selfCheckinTitle;

/// Trang chu theo vai tro.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final role = context.watch<AuthController>().role;
    return switch (role) {
      Roles.student => const _StudentHome(),
      Roles.lecturer => const _LecturerHome(),
      Roles.parent => const ChildrenPage(),
      _ => const OverviewPage(),
    };
  }
}

// ---------------- Sinh vien ----------------

class _StudentHomeData {
  _StudentHomeData(this.week, this.today, this.attendance);

  final List<WeekSlot> week;
  final List<WeekSlot> today;
  final List<ClassAttendance> attendance;
}

/// Viec sinh vien can lam, xep tu quan trong nhat: (noi dung, trang xu ly).
List<(String, String)> studentReminders(Me me, List<ClassAttendance> attendance) {
  final warned = attendance.where((c) => c.warning).length;
  return [
    if (me.consentGiven != true)
      ('Chưa đồng ý sử dụng dữ liệu khuôn mặt', '/face')
    else if (me.consentOutdated)
      ('Nội dung đồng ý đã cập nhật, cần xác nhận lại', '/face'),
    if (me.consentGiven == true && me.faceStatus != 'approved')
      (
        switch (me.faceStatus) {
          'pending' => 'Ảnh khuôn mặt đang chờ duyệt',
          'rejected' => 'Ảnh khuôn mặt bị từ chối, cần đăng ký lại',
          _ => 'Chưa đăng ký khuôn mặt',
        },
        '/face',
      ),
    if (warned > 0) ('$warned lớp vượt ngưỡng vắng, nguy cơ cấm thi', '/my-attendance'),
  ];
}

class _StudentHome extends StatefulWidget {
  const _StudentHome();

  @override
  State<_StudentHome> createState() => _StudentHomeState();
}

class _StudentHomeState extends State<_StudentHome> {
  String? _semester;

  Future<_StudentHomeData> _load() async {
    final api = context.read<ApiClient>();
    final auth = context.read<AuthController>();
    final now = DateTime.now();
    final results = await Future.wait([
      api.get('/schedules/week', query: {'start': isoDate(now)}),
      api.get('/students/me/attendance'),
      auth.reloadMe(),
    ]);
    final week = (results[0] as List<dynamic>).map((e) => WeekSlot.fromJson(e as Json)).toList();
    final today = week.where((slot) => dateOnly(slot.date) == dateOnly(now)).toList();
    final attendance = (results[1] as List<dynamic>).map((e) => ClassAttendance.fromJson(e as Json)).toList();
    return _StudentHomeData(week, today, attendance);
  }

  Widget _todayCard(BuildContext context, List<WeekSlot> today) {
    return SectionCard(
      title: 'Hôm nay (${weekdayLabel(DateTime.now().weekday - 1)}, ${fmtDate(DateTime.now())})',
      trailing: TextButton(onPressed: () => context.go('/schedule'), child: const Text('Cả tuần')),
      child: today.isEmpty
          ? const EmptyView(icon: Icons.free_breakfast_outlined, message: 'Hôm nay bạn không có lịch học.')
          : Column(
              children: [
                for (final slot in today)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('${slot.classCode} — ${slot.subjectName}'),
                    subtitle: Text('${hhmm(slot.startTime)}–${hhmm(slot.endTime)} · ${roomLabel(slot.room)}'),
                    trailing: slot.myStatus != null
                        ? StatusChip.attendance(slot.myStatus)
                        : slot.sessionStatus == 'open'
                            ? FilledButton.icon(
                                onPressed: () => context.push('/self-checkin/${slot.sessionId}', extra: selfCheckinTitle(slot)),
                                icon: const Icon(Icons.camera_alt_outlined),
                                label: const Text('Tự điểm danh'),
                              )
                            : Text(slot.sessionStatus == 'closed' ? 'Đã đóng' : 'Chưa mở phiên'),
                  ),
              ],
            ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<_StudentHomeData>(
      load: _load,
      builder: (context, data, reload) {
        final me = context.watch<AuthController>().me!;
        final wide = isWideScreen(context);
        final semesters = {for (final c in data.attendance) c.semester}.toList()..sort((a, b) => b.compareTo(a));
        final semester = semesters.contains(_semester) ? _semester : (semesters.isEmpty ? null : semesters.first);
        final classes = data.attendance.where((c) => c.semester == semester).toList();
        final warned = classes.where((c) => c.warning).length;
        final reminders = studentReminders(me, data.attendance);

        final profile = ProfileCard(
          title: 'Thông tin sinh viên',
          name: me.fullName,
          onDetail: () => context.go('/account'),
          fields: [
            if (me.studentCode != null) ('MSSV', me.studentCode!),
            ('Họ tên', me.fullName),
            if (me.facultyName != null) ('Khoa', me.facultyName!),
            if (me.major != null && me.major!.isNotEmpty) ('Ngành', me.major!),
            if (me.cohort != null) ('Khoá', 'K${me.cohort}'),
            ('Email', me.email),
          ],
          footer: StatusChip(label: faceStatusLabel(me.faceStatus), color: statusColor(me.faceStatus == 'none' ? null : me.faceStatus)),
        );
        final tiles = TileColumn(
          top: DashTile(
            label: 'Nhắc nhở',
            value: '${reminders.length}',
            icon: Icons.notifications_none,
            note: reminders.isEmpty ? 'Không có việc cần xử lý' : reminders.first.$1,
            onTap: reminders.isEmpty ? null : () => context.go(reminders.first.$2),
          ),
          left: DashTile(
            label: 'Lịch học trong tuần',
            value: '${data.week.length}',
            icon: Icons.calendar_month_outlined,
            tone: TileTone.blue,
            onTap: () => context.go('/schedule'),
          ),
          right: DashTile(
            label: 'Lớp cảnh báo vắng',
            value: '$warned',
            icon: Icons.warning_amber_rounded,
            tone: TileTone.amber,
            onTap: () => context.go('/my-attendance'),
          ),
        );
        final today = _todayCard(context, data.today);
        final dropdown = semesters.length < 2
            ? null
            : SemesterDropdown(
                value: semester,
                options: semesters,
                allowLatest: false,
                width: 200,
                onChanged: (value) => setState(() => _semester = value),
              );
        final done = classes.fold<int>(0, (sum, c) => sum + c.totalSessions - c.absent);
        final total = classes.fold<int>(0, (sum, c) => sum + c.totalSessions);
        final charts = CardRow(
          flexes: const [5, 3, 4],
          children: [
            SectionCard(title: 'Chuyên cần theo lớp', trailing: dropdown, child: _ClassBars(classes: classes)),
            SectionCard(title: 'Tiến độ chuyên cần', child: Center(child: ProgressRing(done: done, total: total))),
            SectionCard(title: 'Lớp học phần', child: _ClassTable(classes: classes)),
          ],
        );
        const gap = SizedBox(height: kCardGap);

        // Dien thoai: "Hom nay" len tren vi tu diem danh la viec chinh; bo hang loi tat vi da
        // co thanh dieu huong duoi.
        return PageBody(
          onRefresh: reload,
          children: wide
              ? [
                  CardRow(flexes: const [7, 5], children: [profile, tiles]),
                  gap,
                  ShortcutGrid(items: shortcutsFor(me.role)),
                  gap,
                  today,
                  gap,
                  charts,
                ]
              : [profile, gap, today, gap, tiles, gap, charts],
        );
      },
    );
  }
}

/// Bieu do ti le di hoc cua tung lop; lop vuot nguong vang to do.
class _ClassBars extends StatelessWidget {
  const _ClassBars({required this.classes});

  final List<ClassAttendance> classes;

  @override
  Widget build(BuildContext context) {
    if (classes.isEmpty) return const SizedBox(height: 230, child: Center(child: Text('Chưa có dữ liệu')));
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    return SizedBox(
      height: 230,
      child: BarChart(BarChartData(
        maxY: 100,
        minY: 0,
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipItem: (group, groupIndex, rod, rodIndex) => BarTooltipItem(
              '${classes[group.x].subjectName}\n${rod.toY.toStringAsFixed(0)}% đi học',
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
              getTitlesWidget: (value, meta) => SideTitleWidget(
                meta: meta,
                child: Text(classes[value.toInt()].classCode, style: TextStyle(fontSize: 11, color: muted), overflow: TextOverflow.ellipsis),
              ),
            ),
          ),
        ),
        barGroups: [
          for (var i = 0; i < classes.length; i++)
            BarChartGroupData(x: i, barRods: [
              BarChartRodData(
                toY: (1 - classes[i].absentRatio) * 100,
                width: 20,
                color: classes[i].warning ? AppColors.danger : AppColors.success,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
              ),
            ]),
        ],
      )),
    );
  }
}

class _ClassTable extends StatelessWidget {
  const _ClassTable({required this.classes});

  final List<ClassAttendance> classes;

  @override
  Widget build(BuildContext context) {
    if (classes.isEmpty) return const Text('Chưa có lớp học phần.');
    final muted = Theme.of(context).colorScheme.onSurfaceVariant;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(children: [
            Expanded(child: Text('Môn học/học phần', style: TextStyle(color: muted, fontSize: 13))),
            Text('Vắng', style: TextStyle(color: muted, fontSize: 13)),
          ]),
        ),
        for (final c in classes)
          InkWell(
            onTap: () => context.go('/my-attendance'),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 7),
              decoration: BoxDecoration(border: Border(top: BorderSide(color: Theme.of(context).colorScheme.outlineVariant))),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(c.classCode, style: const TextStyle(color: AppColors.link, fontSize: 13)),
                        Text(c.subjectName, style: const TextStyle(fontSize: 13)),
                      ],
                    ),
                  ),
                  Text('${c.absent}/${c.totalSessions}', style: TextStyle(fontSize: 13, color: c.warning ? AppColors.danger : null)),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

// ---------------- Giang vien ----------------

class _LecturerHomeData {
  _LecturerHomeData(this.today, this.openSessions, this.warnedStudents);

  final List<TodaySchedule> today;
  final List<SessionDetail> openSessions;
  final int warnedStudents;
}

class _LecturerHome extends StatefulWidget {
  const _LecturerHome();

  @override
  State<_LecturerHome> createState() => _LecturerHomeState();
}

class _LecturerHomeState extends State<_LecturerHome> {
  int? _opening;

  Future<_LecturerHomeData> _load() async {
    final api = context.read<ApiClient>();
    final auth = context.read<AuthController>();
    await auth.reloadMe();
    final results = await Future.wait([
      api.get('/lecturers/me/today-schedules'),
      api.get('/sessions', query: {'status': 'open'}),
    ]);
    final warned = <int>{};
    for (final c in auth.me?.classes ?? const <ClassBrief>[]) {
      try {
        final rows = await api.get('/reports/attendance/warnings', query: {'class_id': c.id}) as List<dynamic>;
        warned.addAll(rows.map((r) => (r as Json)['student_id'] as int));
      } catch (_) {}
    }
    return _LecturerHomeData(
      (results[0] as List<dynamic>).map((e) => TodaySchedule.fromJson(e as Json)).toList(),
      (results[1] as List<dynamic>).map((e) => SessionDetail.fromJson(e as Json)).toList(),
      warned.length,
    );
  }

  Future<void> _openSession(TodaySchedule schedule) async {
    setState(() => _opening = schedule.scheduleId);
    try {
      final data = await context.read<ApiClient>().post('/sessions', data: {
        'schedule_id': schedule.scheduleId,
        'session_date': isoDate(DateTime.now()),
      }) as Json;
      if (mounted) context.push('/sessions/${data['id']}/scan');
    } catch (e) {
      if (mounted) showSnack(context, errorText(e), error: true);
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  Widget _action(TodaySchedule s) {
    if (s.sessionId != null) {
      return s.sessionStatus == 'open'
          ? FilledButton.icon(
              onPressed: () => context.push('/sessions/${s.sessionId}/scan'),
              icon: const Icon(Icons.videocam_outlined),
              label: const Text('Vào điểm danh'),
            )
          : OutlinedButton(onPressed: () => context.push('/sessions/${s.sessionId}'), child: const Text('Xem kết quả'));
    }
    if (nowWithin(s.openFrom, s.endTime)) {
      return FilledButton(
        onPressed: _opening == s.scheduleId ? null : () => _openSession(s),
        child: Text(_opening == s.scheduleId ? 'Đang mở…' : 'Mở phiên'),
      );
    }
    return Text(nowAfter(s.endTime) ? 'Đã kết thúc' : 'Mở từ ${hhmm(s.openFrom)}');
  }

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<_LecturerHomeData>(
      load: _load,
      builder: (context, data, reload) {
        final me = context.watch<AuthController>().me!;
        final wide = isWideScreen(context);
        final profile = ProfileCard(
          title: 'Thông tin giảng viên',
          name: me.fullName,
          onDetail: () => context.go('/account'),
          fields: [
            if (me.lecturerCode != null) ('Mã giảng viên', me.lecturerCode!),
            ('Họ tên', me.fullName),
            if (me.facultyName != null) ('Khoa', me.facultyName!),
            if (me.department != null && me.department!.isNotEmpty) ('Bộ môn', me.department!),
            ('Email', me.email),
          ],
        );
        final tiles = TileColumn(
          top: DashTile(
            label: 'Phiên đang mở',
            value: '${data.openSessions.length}',
            icon: Icons.how_to_reg_outlined,
            onTap: () => context.go('/sessions'),
          ),
          left: DashTile(
            label: 'Buổi dạy hôm nay',
            value: '${data.today.length}',
            icon: Icons.event_available_outlined,
            tone: TileTone.blue,
            onTap: () => context.go('/schedule'),
          ),
          right: DashTile(
            label: 'SV vượt ngưỡng vắng',
            value: '${data.warnedStudents}',
            icon: Icons.warning_amber_rounded,
            tone: TileTone.amber,
            onTap: () => context.go('/reports'),
          ),
        );
        final today = SectionCard(
          title: 'Lịch dạy hôm nay',
          child: data.today.isEmpty
              ? const EmptyView(icon: Icons.free_breakfast_outlined, message: 'Hôm nay không có lịch dạy.')
              : Column(
                  children: [
                    for (final s in data.today)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text('${s.classCode} — ${s.subjectName}'),
                        subtitle: Text('${hhmm(s.startTime)}–${hhmm(s.endTime)} · ${roomLabel(s.room)}'),
                        trailing: _action(s),
                      ),
                  ],
                ),
        );
        final classes = SectionCard(
          title: 'Lớp học phần',
          child: me.classes.isEmpty
              ? const Text('Chưa được phân công lớp nào.')
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final c in me.classes)
                      InkWell(
                        onTap: () => context.push('/classes/${c.id}'),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 7),
                          decoration: BoxDecoration(border: Border(top: BorderSide(color: Theme.of(context).colorScheme.outlineVariant))),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(c.classCode, style: const TextStyle(color: AppColors.link, fontSize: 13)),
                              Text(c.subjectName, style: const TextStyle(fontSize: 13)),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
        );
        const gap = SizedBox(height: kCardGap);
        return PageBody(
          onRefresh: reload,
          children: wide
              ? [
                  CardRow(flexes: const [7, 5], children: [profile, tiles]),
                  gap,
                  ShortcutGrid(items: shortcutsFor(me.role)),
                  gap,
                  CardRow(flexes: const [7, 5], children: [today, classes]),
                ]
              : [profile, gap, today, gap, tiles, gap, classes],
        );
      },
    );
  }
}
