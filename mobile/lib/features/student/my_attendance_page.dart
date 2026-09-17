import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../models/models.dart';
import '../../widgets/attendance_views.dart';
import '../../widgets/common.dart';
import '../../widgets/pickers.dart';

class MyAttendancePage extends StatefulWidget {
  const MyAttendancePage({super.key});

  @override
  State<MyAttendancePage> createState() => _MyAttendancePageState();
}

class _MyAttendancePageState extends State<MyAttendancePage> {
  String? _semester;

  Future<List<ClassAttendance>> _load() async {
    final data = await context.read<ApiClient>().get('/students/me/attendance', query: {'semester': _semester}) as List<dynamic>;
    return data.map((e) => ClassAttendance.fromJson(e as Json)).toList();
  }

  @override
  Widget build(BuildContext context) {
    final semesters = context.watch<AuthController>().me?.semesters ?? const <String>[];
    return AsyncLoader<List<ClassAttendance>>(
      loadKey: _semester,
      load: _load,
      builder: (context, classes, reload) => PageBody(
        onRefresh: reload,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: SemesterDropdown(value: _semester, options: semesters, onChanged: (v) => setState(() => _semester = v)),
          ),
          const SizedBox(height: 16),
          ClassAttendanceList(classes: classes),
        ],
      ),
    );
  }
}
