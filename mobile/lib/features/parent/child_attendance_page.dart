import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../models/models.dart';
import '../../widgets/attendance_views.dart';
import '../../widgets/common.dart';
import '../../widgets/pickers.dart';

class ChildAttendancePage extends StatefulWidget {
  const ChildAttendancePage({super.key, required this.studentId});

  final int studentId;

  @override
  State<ChildAttendancePage> createState() => _ChildAttendancePageState();
}

class _ChildAttendancePageState extends State<ChildAttendancePage> {
  String? _semester;
  Student? _child;

  Future<List<ClassAttendance>> _load() async {
    final api = context.read<ApiClient>();
    if (_child == null) {
      final children = await api.get('/parents/me/children') as List<dynamic>;
      final match = children.map((e) => Student.fromJson(e as Json)).where((s) => s.id == widget.studentId);
      _child = match.isEmpty ? null : match.first;
    }
    final data = await api.get('/parents/me/children/${widget.studentId}/attendance', query: {'semester': _semester}) as List<dynamic>;
    return data.map((e) => ClassAttendance.fromJson(e as Json)).toList();
  }

  @override
  Widget build(BuildContext context) {
    return AsyncLoader<List<ClassAttendance>>(
      loadKey: _semester,
      load: _load,
      builder: (context, classes, reload) {
        final child = _child;
        final semesters = {for (final c in child?.classes ?? const <ClassBrief>[]) c.semester}.toList();
        return PageBody(
          onRefresh: reload,
          children: [
            if (child != null)
              Text('${child.fullName} — ${child.studentCode}', style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: SemesterDropdown(value: _semester, options: semesters, onChanged: (v) => setState(() => _semester = v)),
            ),
            const SizedBox(height: 16),
            ClassAttendanceList(classes: classes),
          ],
        );
      },
    );
  }
}
