import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/roles.dart';
import '../models/models.dart';

/// Trang xu ly canh bao khi bam chuong, theo vai tro (null = khong hien chuong).
String? alertTargetFor(String role) => switch (role) {
      Roles.admin || Roles.affairs => '/face-review',
      Roles.lecturer || Roles.training || Roles.faculty => '/reports',
      Roles.student => '/my-attendance',
      Roles.board => '/',
      Roles.parent => '/notifications',
      _ => null,
    };

String alertLabelFor(String role) => switch (role) {
      Roles.admin || Roles.affairs => 'khuôn mặt chờ duyệt',
      Roles.student => 'lớp vượt ngưỡng vắng',
      Roles.parent => 'thông báo mới',
      _ => 'sinh viên vượt ngưỡng vắng',
    };

/// So muc can chu y, lay tu du lieu that: admin/P.CTSV -> khuon mat cho duyet; GV -> SV
/// vuot nguong vang o lop minh day; P.DT/Khoa/Ban -> SV vuot nguong trong pham vi;
/// SV -> so lop minh vuot nguong; phu huynh -> so thong bao diem danh cua con chua doc.
Future<int> countAlerts(ApiClient api, String role) async {
  switch (role) {
    case Roles.admin || Roles.affairs:
      return (await api.get('/faces/pending') as List<dynamic>).length;
    case Roles.lecturer:
      final me = Me.fromJson(await api.get('/auth/me') as Json);
      final warned = <int>{};
      for (final clazz in me.classes) {
        final rows = await api.get('/reports/attendance/warnings', query: {'class_id': clazz.id}) as List<dynamic>;
        warned.addAll(rows.map((row) => (row as Json)['student_id'] as int));
      }
      return warned.length;
    case Roles.training || Roles.faculty || Roles.board:
      final overview = Overview.fromJson(await api.get('/reports/overview') as Json);
      return overview.totals.warnedStudents;
    case Roles.student:
      final classes = await api.get('/students/me/attendance') as List<dynamic>;
      return classes.map((e) => ClassAttendance.fromJson(e as Json)).where((c) => c.warning).length;
    case Roles.parent:
      // Phu huynh: so thong bao diem danh cua con chua doc (hop thu trong app).
      final data = await api.get('/notifications/unread-count') as Json;
      return data['count'] as int;
    default:
      return 0;
  }
}

/// Chuong canh bao tren thanh tieu de, tu cap nhat moi 2 phut.
class NotificationBell extends StatefulWidget {
  const NotificationBell({super.key, required this.role});

  final String role;

  @override
  State<NotificationBell> createState() => _NotificationBellState();
}

class _NotificationBellState extends State<NotificationBell> {
  static const _refreshEvery = Duration(minutes: 2);
  Timer? _timer;
  int _count = 0;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(_refreshEvery, (_) => _refresh());
  }

  @override
  void didUpdateWidget(covariant NotificationBell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.role != widget.role) _refresh();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    try {
      final count = await countAlerts(context.read<ApiClient>(), widget.role);
      if (mounted) setState(() => _count = count);
    } catch (_) {
      // Loi mang/het phien: giu so cu, lan sau thu lai (khong lam phien nguoi dung).
    }
  }

  @override
  Widget build(BuildContext context) {
    final target = alertTargetFor(widget.role);
    if (target == null) return const SizedBox.shrink();
    return IconButton(
      tooltip: _count > 0 ? '$_count ${alertLabelFor(widget.role)}' : 'Không có cảnh báo mới',
      onPressed: () {
        context.go(target);
        _refresh();
      },
      icon: Badge(
        isLabelVisible: _count > 0,
        label: Text(_count > 99 ? '99+' : '$_count'),
        child: Icon(_count > 0 ? Icons.notifications_active_outlined : Icons.notifications_outlined),
      ),
    );
  }
}
