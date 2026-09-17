import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/api_client.dart';
import '../../core/formatters.dart';
import '../../models/models.dart';
import '../../widgets/common.dart';
import '../../widgets/form_dialog.dart';
import '../../widgets/pickers.dart';

/// Quan ly don vi (Khoa, Phong Dao tao, Phong CTSV, Ban nganh) - chi admin.
class UnitsPage extends StatelessWidget {
  const UnitsPage({super.key});

  Future<bool> _edit(BuildContext context, {Unit? unit}) async {
    final api = context.read<ApiClient>();
    final creating = unit == null;
    final values = await showFormDialog(
      context,
      title: creating ? 'Thêm đơn vị' : 'Sửa đơn vị',
      fields: [
        const FieldSpec('code', 'Mã đơn vị', helper: 'VD: K-CNTT, P-DT'),
        const FieldSpec('name', 'Tên đơn vị'),
        if (creating)
          FieldSpec('type', 'Loại đơn vị', kind: FieldKind.dropdown,
              helper: 'Quyết định vai trò của cán bộ thuộc đơn vị, không đổi được sau khi tạo',
              options: [for (final t in unitTypes) (t, unitTypeLabel(t))]),
      ],
      initial: unit == null ? const {'type': 'faculty'} : {'code': unit.code, 'name': unit.name},
    );
    if (values == null || !context.mounted) return false;
    final ok = await runAction(
      context,
      () => creating ? api.post('/units', data: values) : api.patch('/units/${unit.id}', data: values),
      success: creating ? 'Đã thêm đơn vị' : 'Đã cập nhật đơn vị',
    );
    if (ok) UnitCache.invalidate();
    return ok;
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<ApiClient>();
    return AsyncLoader<List<Unit>>(
      load: () => UnitCache.load(api, force: true),
      builder: (context, units, reload) => PageBody(
        maxWidth: 900,
        onRefresh: reload,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: () async {
                if (await _edit(context)) reload();
              },
              icon: const Icon(Icons.add),
              label: const Text('Thêm đơn vị'),
            ),
          ),
          const SizedBox(height: 12),
          for (final type in unitTypes) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
              child: Text(unitTypeLabel(type), style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
            Card(
              clipBehavior: Clip.antiAlias,
              child: Column(
                children: [
                  if (!units.any((u) => u.type == type))
                    const ListTile(title: Text('Chưa có đơn vị')),
                  for (final unit in units.where((u) => u.type == type))
                    ListTile(
                      leading: const Icon(Icons.apartment_outlined),
                      title: Text(unit.name),
                      subtitle: Text(unit.code),
                      trailing: Wrap(children: [
                        IconButton(
                          tooltip: 'Sửa',
                          onPressed: () async {
                            if (await _edit(context, unit: unit)) reload();
                          },
                          icon: const Icon(Icons.edit_outlined),
                        ),
                        IconButton(
                          tooltip: 'Xóa',
                          onPressed: () async {
                            final ok = await confirmDialog(context,
                                title: 'Xóa đơn vị?',
                                message: 'Chỉ xóa được khi đơn vị chưa có cán bộ, SV, GV hoặc lớp học phần.',
                                confirmLabel: 'Xóa',
                                destructive: true);
                            if (ok && context.mounted && await runAction(context, () => api.delete('/units/${unit.id}'), success: 'Đã xóa')) {
                              UnitCache.invalidate();
                              reload();
                            }
                          },
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ]),
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
