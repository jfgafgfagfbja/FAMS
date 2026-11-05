import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/auth_controller.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/paged_list.dart';

/// Nhom thao tac de loc (tien to cua cot action o backend/app/services/audit.py).
const _groups = <(String?, String)>[
  (null, 'Tất cả thao tác'),
  ('auth.', 'Đăng nhập / đăng xuất'),
  ('user.', 'Tài khoản, mật khẩu'),
  ('consent.', 'Đồng ý sinh trắc học'),
  ('face.', 'Khuôn mặt'),
  ('student.', 'Hồ sơ sinh viên'),
  ('class.', 'Lớp học phần'),
  ('enrollment.', 'Ghi danh'),
  ('schedule.', 'Lịch học'),
  ('session.', 'Phiên điểm danh'),
  ('attendance.', 'Sửa kết quả điểm danh'),
  ('report.', 'Xuất báo cáo'),
  ('lecturer.', 'Giảng viên'),
  ('parent', 'Phụ huynh'),
  ('staff.', 'Cán bộ phòng ban'),
];

const _kinds = {
  'user': 'tài khoản',
  'unit': 'đơn vị',
  'staff': 'cán bộ',
  'student': 'sinh viên',
  'lecturer': 'giảng viên',
  'parent': 'phụ huynh',
  'parent_link': 'liên kết phụ huynh',
  'class': 'lớp học phần',
  'enrollment': 'ghi danh',
  'schedule': 'lịch học',
  'room': 'phòng học',
  'location': 'địa điểm',
  'face': 'khuôn mặt',
  'session': 'phiên điểm danh',
  'attendance': 'kết quả điểm danh',
};

/// Ten hanh dong de doc.
String auditActionLabel(String action) {
  const named = {
    'auth.login': 'Đăng nhập',
    'auth.login_failed': 'Đăng nhập sai',
    'auth.login_locked': 'Đăng nhập khi đang bị khóa',
    'auth.logout': 'Đăng xuất',
    'user.password_changed': 'Đổi mật khẩu',
    'consent.given': 'Đồng ý sinh trắc học',
    'consent.withdrawn': 'Rút đồng ý sinh trắc học',
    'face.approved': 'Duyệt khuôn mặt',
    'face.rejected': 'Từ chối khuôn mặt',
    'session.opened': 'Mở phiên điểm danh',
    'session.closed': 'Đóng phiên điểm danh',
    'report.exported': 'Xuất báo cáo Excel',
  };
  final name = named[action];
  if (name != null) return name;
  final dot = action.indexOf('.');
  if (dot < 0) return action;
  final kind = _kinds[action.substring(0, dot)] ?? action.substring(0, dot);
  return switch (action.substring(dot + 1)) {
    'create' => 'Thêm $kind',
    'update' => 'Sửa $kind',
    'delete' => 'Xóa $kind',
    _ => action,
  };
}

const _fields = {
  'full_name': 'Họ tên',
  'email': 'Email',
  'password_hash': 'Mật khẩu',
  'status': 'Trạng thái',
  'reason': 'Lý do',
  'note': 'Ghi chú',
  'consent_given': 'Đồng ý sinh trắc',
  'consent_at': 'Thời điểm đồng ý',
  'consent_version': 'Phiên bản điều khoản',
  'consent_method': 'Cách đồng ý',
  'consent_recorded_by': 'Người ghi nhận',
  'lecturer_id': 'Giảng viên',
  'faculty_id': 'Khoa',
  'unit_id': 'Đơn vị',
  'room_id': 'Phòng',
  'semester': 'Học kỳ',
  'role': 'Vai trò',
  'is_active': 'Đang hoạt động',
};

/// Nhat ky he thong: admin xem toan truong, Lanh dao Khoa chi thay thao tac lien quan Khoa minh.
class AuditLogsPage extends StatefulWidget {
  const AuditLogsPage({super.key});

  @override
  State<AuditLogsPage> createState() => _AuditLogsPageState();
}

class _AuditLogsPageState extends State<AuditLogsPage> {
  String? _group;
  bool? _success;
  int? _days;

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    final role = context.watch<AuthController>().role;
    final from = _days == null ? null : isoDate(DateTime.now().subtract(Duration(days: _days! - 1)));
    return PageBody(
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(role == Roles.facultyLeader
              ? 'Các thao tác trên dữ liệu của Khoa: ai làm, lúc nào, thay đổi gì.'
              : 'Mọi thao tác quản lý và đăng nhập trên hệ thống: ai làm, lúc nào, thay đổi gì.'),
        ),
        PagedList<AuditLogEntry>(
          filterKey: (_group, _success, _days),
          searchHint: 'Tìm theo email người thao tác hoặc đối tượng',
          emptyMessage: 'Không có thao tác nào khớp bộ lọc.',
          emptyIcon: Icons.history_outlined,
          fetch: (q, offset, limit) async {
            final page = await api.getPage('/audit-logs', query: {
              'q': q,
              'action': _group,
              'success': _success,
              'date_from': from,
              'offset': offset,
              'limit': limit,
            });
            return PageResult(page.items.map(AuditLogEntry.fromJson).toList(), page.total);
          },
          filters: [
            _Choice<String?>(
              label: 'Nhóm thao tác',
              width: 240,
              value: _group,
              options: _groups,
              onChanged: (v) => setState(() => _group = v),
            ),
            _Choice<bool?>(
              label: 'Kết quả',
              width: 160,
              value: _success,
              options: const [(null, 'Tất cả'), (true, 'Thành công'), (false, 'Thất bại')],
              onChanged: (v) => setState(() => _success = v),
            ),
            _Choice<int?>(
              label: 'Thời gian',
              width: 160,
              value: _days,
              options: const [(null, 'Mọi lúc'), (1, 'Hôm nay'), (7, '7 ngày qua'), (30, '30 ngày qua')],
              onChanged: (v) => setState(() => _days = v),
            ),
          ],
          itemBuilder: (context, e, reload) => ListTile(
            onTap: () => _showDetail(context, e),
            leading: CircleAvatar(
              backgroundColor: (e.success ? AppColors.success : AppColors.danger).withValues(alpha: 0.12),
              child: Icon(e.success ? Icons.check : Icons.block,
                  color: e.success ? AppColors.success : AppColors.danger, size: 20),
            ),
            title: Text([auditActionLabel(e.action), if (e.targetLabel != null) e.targetLabel!].join(' · ')),
            subtitle: Text([
              fmtDateTime(e.createdAt),
              _actor(e),
            ].join(' · ')),
            trailing: const Icon(Icons.chevron_right),
          ),
        ),
      ],
    );
  }
}

String _actor(AuditLogEntry e) {
  final role = e.actorRole;
  if (role == null || role == 'system') return e.actorEmail ?? 'Hệ thống';
  return '${e.actorEmail ?? '?'} (${Roles.label(role)})';
}

String _value(Object? v) => switch (v) {
      null => '(trống)',
      true => 'Có',
      false => 'Không',
      _ => v.toString(),
    };

Future<void> _showDetail(BuildContext context, AuditLogEntry e) {
  // detail: {truong: [cu, moi]} khi sua du lieu; {khoa: gia tri} voi su kien khac.
  Map<String, dynamic> detail = const {};
  if (e.detail != null) {
    try {
      detail = (jsonDecode(e.detail!) as Map).cast<String, dynamic>();
    } catch (_) {
      detail = {'chi tiết': e.detail};
    }
  }
  return showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(auditActionLabel(e.action)),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _KV('Thời điểm', fmtDateTime(e.createdAt)),
              _KV('Người thao tác', _actor(e)),
              if (e.targetLabel != null) _KV('Đối tượng', e.targetLabel!),
              _KV('Kết quả', e.success ? 'Thành công' : 'Thất bại'),
              if (e.ip != null) _KV('Địa chỉ IP', e.ip!),
              if (detail.isNotEmpty) ...[
                const Divider(height: 24),
                Text(e.action.endsWith('.update') || detail.values.any((v) => v is List) ? 'Thay đổi' : 'Chi tiết',
                    style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                for (final entry in detail.entries)
                  _KV(
                    _fields[entry.key] ?? entry.key,
                    entry.value is List && (entry.value as List).length == 2
                        ? '${_value((entry.value as List)[0])} → ${_value((entry.value as List)[1])}'
                        : _value(entry.value),
                  ),
              ],
            ],
          ),
        ),
      ),
      actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('Đóng'))],
    ),
  );
}

class _Choice<T> extends StatelessWidget {
  const _Choice({required this.label, required this.width, required this.value, required this.options, required this.onChanged});

  final String label;
  final double width;
  final T value;
  final List<(T, String)> options;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: DropdownButtonFormField<T>(
        initialValue: value,
        isExpanded: true,
        decoration: InputDecoration(labelText: label),
        items: [for (final (v, text) in options) DropdownMenuItem<T>(value: v, child: Text(text, overflow: TextOverflow.ellipsis))],
        onChanged: (v) => onChanged(v as T),
      ),
    );
  }
}

class _KV extends StatelessWidget {
  const _KV(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(label, style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ),
          Expanded(child: SelectableText(value)),
        ],
      ),
    );
  }
}
