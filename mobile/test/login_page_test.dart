import 'package:fams_app/core/api_client.dart';
import 'package:fams_app/core/auth_controller.dart';
import 'package:fams_app/core/token_storage.dart';
import 'package:fams_app/features/auth/login_page.dart';
import 'package:fams_app/widgets/common.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

void main() {
  Widget wrap(Widget child) {
    final api = ApiClient(storage: TokenStorage());
    return MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider(create: (_) => AuthController(api)),
      ],
      child: MaterialApp(home: child),
    );
  }

  testWidgets('login form validates email and password before calling API', (tester) async {
    await tester.pumpWidget(wrap(const LoginPage()));

    expect(find.text('FAMS'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Đăng nhập'));
    await tester.pump();

    expect(find.text('Nhập email hợp lệ'), findsOneWidget);
    expect(find.text('Nhập mật khẩu'), findsOneWidget);
  });

  testWidgets('StatusChip shows Vietnamese attendance labels', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: Column(children: [StatusChip.attendance('late'), StatusChip.attendance(null)])),
    ));
    expect(find.text('Muộn'), findsOneWidget);
    expect(find.text('Chưa điểm danh'), findsOneWidget);
  });
}
