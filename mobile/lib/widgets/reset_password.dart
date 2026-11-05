import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import 'common.dart';
import 'form_dialog.dart';

/// Can bo dat lai mat khau cho nguoi khac qua endpoint [path]. Mat khau moi do can bo tu dat
/// roi bao cho nguoi do; he thong khong gui di dau va khong luu lai dang chu ro.
Future<bool> resetPassword(BuildContext context, {required String name, required String path}) async {
  final values = await showFormDialog(
    context,
    title: 'Đặt lại mật khẩu — $name',
    submitLabel: 'Đặt lại',
    fields: const [
      FieldSpec(
        'new_password',
        'Mật khẩu mới',
        kind: FieldKind.password,
        minLength: 8,
        helper: 'Người này sẽ bị đăng xuất khỏi mọi thiết bị',
      ),
      FieldSpec('confirm', 'Nhập lại mật khẩu mới', kind: FieldKind.password, sameAs: 'new_password'),
    ],
  );
  if (values == null || !context.mounted) return false;
  return runAction(
    context,
    () => context.read<ApiClient>().post(path, data: {'new_password': values['new_password']}),
    success: 'Đã đặt lại mật khẩu cho $name',
  );
}
