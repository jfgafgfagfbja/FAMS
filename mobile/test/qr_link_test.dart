import 'package:fams_app/core/api_client.dart';
import 'package:fams_app/core/auth_controller.dart';
import 'package:fams_app/core/roles.dart';
import 'package:fams_app/core/theme.dart';
import 'package:fams_app/core/token_storage.dart';
import 'package:fams_app/features/auth/login_page.dart';
import 'package:fams_app/features/student/self_checkin_page.dart';
import 'package:fams_app/models/models.dart';
import 'package:fams_app/router.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'support/fake_portal.dart';

const _link = '/self-checkin/33?code=FAMS:33:59433:abcdef123456';

void main() {
  /// Dung router that o trang thai [status], tra ve de test dieu huong.
  Future<(GoRouter, AuthController, FakeApi)> start(WidgetTester tester, AuthStatus status) async {
    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final api = FakeApi(Roles.student);
    final auth = AuthController(api)..status = status;
    if (status == AuthStatus.authenticated) auth.me = Me.fromJson(api.me);
    final router = buildRouter(auth);
    addTearDown(router.dispose);
    await tester.pumpWidget(MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<AuthController>.value(value: auth),
        ChangeNotifierProvider<ThemeController>(create: (_) => ThemeController(TokenStorage())),
      ],
      child: MaterialApp.router(routerConfig: router),
    ));
    await tester.pump();
    return (router, auth, api);
  }

  String location(GoRouter router) => router.routerDelegate.currentConfiguration.uri.toString();

  testWidgets('da dang nhap: mo link QR vao thang trang tu diem danh, kem san ma', (tester) async {
    final (router, _, _) = await start(tester, AuthStatus.authenticated);
    router.go(_link);
    await tester.pump();
    await tester.pump();

    final page = tester.widget<SelfCheckinPage>(find.byType(SelfCheckinPage));
    expect(page.sessionId, 33);
    expect(page.initialCode, 'FAMS:33:59433:abcdef123456');
  });

  testWidgets('chua dang nhap: dang nhap xong quay lai dung link QR', (tester) async {
    final (router, auth, api) = await start(tester, AuthStatus.unauthenticated);
    router.go(_link);
    await tester.pump();
    await tester.pump();
    expect(find.byType(LoginPage), findsOneWidget);
    expect(Uri.parse(location(router)).queryParameters['from'], _link);

    auth
      ..me = Me.fromJson(api.me)
      ..status = AuthStatus.authenticated
      ..notifyListeners();
    await tester.pump();
    await tester.pump();

    expect(tester.widget<SelfCheckinPage>(find.byType(SelfCheckinPage)).initialCode, 'FAMS:33:59433:abcdef123456');
  });

  testWidgets('dang mo app chua xac dinh dang nhap: khong mat link QR', (tester) async {
    final (router, auth, _) = await start(tester, AuthStatus.unknown);
    router.go(_link);
    await tester.pump();
    await tester.pump();

    auth
      ..status = AuthStatus.unauthenticated
      ..notifyListeners();
    await tester.pump();
    await tester.pump();

    expect(find.byType(LoginPage), findsOneWidget);
    expect(Uri.parse(location(router)).queryParameters['from'], _link);
  });

  testWidgets('trang dang nhap thuong khong kem tham so, vao xong ve trang chu', (tester) async {
    final (router, auth, api) = await start(tester, AuthStatus.unauthenticated);
    await tester.pump();
    expect(location(router), '/login');

    auth
      ..me = Me.fromJson(api.me)
      ..status = AuthStatus.authenticated
      ..notifyListeners();
    await tester.pumpAndSettle();
    expect(location(router), '/');
  });

  testWidgets('khong quay lai duong dan ngoai qua tham so from', (tester) async {
    final (router, _, _) = await start(tester, AuthStatus.authenticated);
    router.go('/login?from=//trang-la.example');
    await tester.pumpAndSettle();
    expect(location(router), '/');
  });
}
