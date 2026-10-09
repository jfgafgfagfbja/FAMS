import 'package:fams_app/core/api_client.dart';
import 'package:fams_app/core/token_storage.dart';
import 'package:fams_app/features/auth/account_page.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

void main() {
  Future<void> open(WidgetTester tester) async {
    await tester.pumpWidget(Provider<ApiClient>.value(
      value: ApiClient(storage: TokenStorage()),
      child: const MaterialApp(home: Scaffold(body: ChangePasswordDialog())),
    ));
  }

  Finder field(String label) => find.widgetWithText(TextFormField, label);
  Future<void> submit(WidgetTester tester) async {
    await tester.tap(find.widgetWithText(FilledButton, 'Đổi mật khẩu'));
    await tester.pump();
  }

  testWidgets('bao loi ngay khi bo trong, khong goi server', (tester) async {
    await open(tester);
    await submit(tester);

    expect(find.text('Nhập mật khẩu hiện tại'), findsOneWidget);
    expect(find.text('Mật khẩu mới phải có ít nhất 8 ký tự'), findsOneWidget);
  });

  testWidgets('hai lan nhap mat khau moi phai khop', (tester) async {
    await open(tester);
    await tester.enterText(field('Mật khẩu hiện tại'), 'matkhaucu');
    await tester.enterText(field('Mật khẩu mới'), 'MatKhauMoi#1');
    await tester.enterText(field('Nhập lại mật khẩu mới'), 'MatKhauMoi#2');
    await submit(tester);

    expect(find.text('Hai lần nhập không khớp'), findsOneWidget);
  });

  testWidgets('mat khau moi phai khac mat khau hien tai', (tester) async {
    await open(tester);
    await tester.enterText(field('Mật khẩu hiện tại'), 'GiongNhau#1');
    await tester.enterText(field('Mật khẩu mới'), 'GiongNhau#1');
    await tester.enterText(field('Nhập lại mật khẩu mới'), 'GiongNhau#1');
    await submit(tester);

    expect(find.text('Mật khẩu mới phải khác mật khẩu hiện tại'), findsOneWidget);
  });
}
