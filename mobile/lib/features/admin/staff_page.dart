import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../core/roles.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/form_dialog.dart';
import '../../widgets/paged_list.dart';
import '../../widgets/pickers.dart';

/// Tai khoan can bo Phong Dao tao, Phong CTSV, Khoa (Van phong / Lanh dao), Ban nganh - chi admin.
class StaffPage extends StatefulWidget {
  const StaffPage({super.key});

  @override
  State<StaffPage> createState() => _StaffPageState();
}

class _StaffPageState extends State<StaffPage> {
  int? _unitId;

  Future<bool> _edit(BuildContext context, {StaffMember? staff}) async {
    final api = context.read<ApiClient>();
    final units = await UnitCache.load(api);
    if (!context.mounted) return false;
    if (units.isEmpty) {
      showSnack(context, 'Cần tạo đơn vị trước khi thêm cán bộ', error: true);
      return false;
    }
    final creating = staff == null;
    final values = await showFormDialog(
      context,
      title: creating ? 'Thêm cán bộ' : 'Sửa cán bộ',
      fields: [
        if (creating) ...[
          const FieldSpec('email', 'Email', kind: FieldKind.email),
          const FieldSpec('password', 'Mật khẩu ban đầu', kind: FieldKind.password, minLength: 8),
        ],
        const FieldSpec('full_name', 'Họ tên'),
        FieldSpec('unit_id', 'Đơn vị', kind: FieldKind.dropdown,
            helper: 'Vai trò suy ra từ loại đơn vị (Khoa: chọn nhóm bên dưới)',
            options: [for (final u in units) (u.id, '${u.name} (${unitTypeLabel(u.type)})')]),
        const FieldSpec('faculty_leader', 'Nhóm cán bộ trong Khoa', kind: FieldKind.dropdown,
            helper: 'Chỉ áp dụng khi đơn vị là Khoa',
            options: [
              (false, 'Văn phòng Khoa — nhập liệu lớp, lịch, ghi danh'),
              (true, 'Lãnh đạo Khoa — giám sát, duyệt phép, xem nhật ký'),
            ]),
        const FieldSpec('position', 'Chức vụ', required: false),
      ],
      initial: staff == null
          ? const {'faculty_leader': false}
          : {
              'full_name': staff.fullName,
              'unit_id': staff.unitId,
              'faculty_leader': staff.role == Roles.facultyLeader,
              'position': staff.position,
            },
    );
    if (values == null || !context.mounted) return false;
    return runAction(
      context,
      () => creating ? api.post('/staff', data: values) : api.patch('/staff/${staff.id}', data: values),
      success: creating ? 'Đã thêm cán bộ' : 'Đã cập nhật cán bộ',
    );
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return PageBody(
      children: [
        PagedList<StaffMember>(
          filterKey: _unitId,
          searchHint: 'Tìm theo tên hoặc email',
          emptyMessage: 'Chưa có tài khoản cán bộ phòng ban.',
          emptyIcon: Icons.badge_outlined,
          fetch: (q, offset, limit) async {
            final page = await api.getPage('/staff', query: {'q': q, 'unit_id': _unitId, 'offset': offset, 'limit': limit});
            return PageResult(page.items.map(StaffMember.fromJson).toList(), page.total);
          },
          filters: [
            UnitDropdown(value: _unitId, facultiesOnly: false, label: 'Đơn vị', width: 280, onChanged: (v) => setState(() => _unitId = v)),
          ],
          actions: (reload) => [
            FilledButton.icon(
              onPressed: () async {
                if (await _edit(context)) reload();
              },
              icon: const Icon(Icons.person_add_alt),
              label: const Text('Thêm cán bộ'),
            ),
          ],
          itemBuilder: (context, s, reload) => ListTile(
            leading: const CircleAvatar(child: Icon(Icons.badge_outlined)),
            title: Text(s.fullName),
            subtitle: Text([s.email, s.unitName, Roles.label(s.role), if (s.position.isNotEmpty) s.position].join(' · ')),
            trailing: PopupMenuButton<String>(
              onSelected: (value) async {
                if (value == 'edit') {
                  if (await _edit(context, staff: s)) reload();
                } else {
                  final ok = await confirmDialog(context, title: 'Xóa cán bộ?', message: 'Xóa tài khoản ${s.fullName}?', confirmLabel: 'Xóa', destructive: true);
                  if (ok && context.mounted && await runAction(context, () => api.delete('/staff/${s.id}'), success: 'Đã xóa')) {
                    reload();
                  }
                }
              },
              itemBuilder: (context) => const [
                PopupMenuItem(value: 'edit', child: Text('Sửa')),
                PopupMenuItem(value: 'delete', child: Text('Xóa')),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
