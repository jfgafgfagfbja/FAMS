import 'package:fams_app/core/api_client.dart';
import 'package:fams_app/core/auth_controller.dart';
import 'package:fams_app/core/roles.dart';
import 'package:fams_app/core/theme.dart';
import 'package:fams_app/core/token_storage.dart';
import 'package:fams_app/features/admin/audit_logs_page.dart';
import 'package:fams_app/features/auth/account_page.dart';
import 'package:fams_app/models/models.dart';
import 'package:fams_app/widgets/consent_form.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

/// API gia: tra du lieu dung khuon cua backend va ghi lai cac lan goi.
class _FakeApi extends ApiClient {
  _FakeApi() : super(storage: TokenStorage());

  final gets = <String>[];
  final posts = <(String, Object?)>[];
  final pageQueries = <Map<String, dynamic>?>[];
  Object? failNextPost;

  @override
  Future<dynamic> get(String path, {Map<String, dynamic>? query}) async {
    gets.add(path);
    if (path == '/students/consent-policy') {
      return {
        'version': '2026-10',
        'title': 'Đồng ý sử dụng dữ liệu khuôn mặt (sinh trắc học)',
        'items': ['Mục đích: chỉ dùng để điểm danh.', 'Bạn có quyền rút đồng ý bất kỳ lúc nào.'],
        'checkbox': 'Tôi đã đọc và tự nguyện đồng ý.',
      };
    }
    throw UnimplementedError(path);
  }

  @override
  Future<dynamic> post(String path, {Object? data}) async {
    final error = failNextPost;
    if (error != null) {
      failNextPost = null;
      throw error;
    }
    posts.add((path, data));
    return {'ok': true};
  }

  @override
  Future<PageResult<Map<String, dynamic>>> getPage(String path, {Map<String, dynamic>? query}) async {
    pageQueries.add(query);
    return const PageResult([
      {
        'id': 2,
        'created_at': '2026-10-16T08:00:00+07:00',
        'actor_email': 'khoa.cntt@fams.edu.vn',
        'actor_role': 'faculty_office',
        'action': 'class.update',
        'target_type': 'class',
        'target_id': 3,
        'target_label': 'INT3306.1',
        'success': true,
        'detail': '{"lecturer_id": [1, 2]}',
      },
      {
        'id': 1,
        'created_at': '2026-10-16T07:59:00+07:00',
        'actor_email': 'ai.do@fams.edu.vn',
        'action': 'auth.login_failed',
        'success': false,
      },
    ], 2);
  }
}

Widget _host(_FakeApi api, Widget child, {String role = Roles.student, bool scroll = false}) {
  final auth = AuthController(api)..me = Me.fromJson({'role': role, 'full_name': 'Nguoi Thu', 'classes': []});
  return MultiProvider(
    providers: [
      Provider<ApiClient>.value(value: api),
      ChangeNotifierProvider<AuthController>.value(value: auth),
      ChangeNotifierProvider<ThemeController>(create: (_) => ThemeController(TokenStorage())),
    ],
    // Trang dung PageBody (ListView) tu cuon; widget le thi boc them vung cuon.
    child: MaterialApp(home: Scaffold(body: scroll ? SingleChildScrollView(child: child) : child)),
  );
}

void main() {
  testWidgets('SV doc noi dung tu may chu, phai tick moi gui duoc, gui kem phien ban', (tester) async {
    final api = _FakeApi();
    var done = 0;
    await tester.pumpWidget(_host(api, ConsentForm(studentId: 7, onDone: () async => done++), scroll: true));
    await tester.pumpAndSettle();

    expect(find.text('Mục đích: chỉ dùng để điểm danh.'), findsOneWidget);
    expect(find.text('Phiên bản nội dung: 2026-10'), findsOneWidget);
    final button = find.widgetWithText(FilledButton, 'Đồng ý và tiếp tục');
    expect(tester.widget<FilledButton>(button).onPressed, isNull); // chua tick

    await tester.tap(find.text('Tôi đã đọc và tự nguyện đồng ý.'));
    await tester.pump();
    await tester.tap(button);
    await tester.pumpAndSettle();

    expect(api.posts.single.$1, '/students/7/consent');
    expect(api.posts.single.$2, {'agreed': true, 'version': '2026-10', 'method': 'self'});
    expect(done, 1);
  });

  testWidgets('can bo nhap ban giay: noi dung cam ket khac, gui method paper', (tester) async {
    final api = _FakeApi();
    await tester.pumpWidget(_host(api, ConsentForm(studentId: 7, paper: true, onDone: () async {}), role: Roles.affairs, scroll: true));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(CheckboxListTile));
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, 'Ghi nhận đồng ý (bản giấy)'));
    await tester.pumpAndSettle();

    expect((api.posts.single.$2 as Map)['method'], 'paper');
  });

  testWidgets('noi dung vua doi tren may chu (409): tai lai va bo tick', (tester) async {
    final api = _FakeApi()..failNextPost = ApiException('Noi dung da thay doi', statusCode: 409);
    var done = 0;
    await tester.pumpWidget(_host(api, ConsentForm(studentId: 7, onDone: () async => done++), scroll: true));
    await tester.pumpAndSettle();

    await tester.tap(find.byType(CheckboxListTile));
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, 'Đồng ý và tiếp tục'));
    await tester.pumpAndSettle();

    expect(done, 0);
    expect(api.gets.where((p) => p == '/students/consent-policy'), hasLength(2));
    expect(tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value, isFalse);
  });

  testWidgets('nhat ky: ten hanh dong de doc, loc theo nhom, xem chi tiet thay doi', (tester) async {
    final api = _FakeApi();
    tester.view.physicalSize = const Size(1400, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(_host(api, const AuditLogsPage(), role: Roles.facultyLeader));
    await tester.pumpAndSettle();

    expect(find.textContaining('dữ liệu của Khoa'), findsOneWidget);
    expect(find.text('Sửa lớp học phần · INT3306.1'), findsOneWidget);
    expect(find.text('Đăng nhập sai'), findsOneWidget);
    expect(find.textContaining('khoa.cntt@fams.edu.vn (Văn phòng Khoa)'), findsOneWidget);

    await tester.tap(find.text('Sửa lớp học phần · INT3306.1'));
    await tester.pumpAndSettle();
    expect(find.text('Giảng viên'), findsOneWidget);
    expect(find.text('1 → 2'), findsOneWidget);
    await tester.tap(find.text('Đóng'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Tất cả thao tác'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Đồng ý sinh trắc học').last);
    await tester.pumpAndSettle();
    expect(api.pageQueries.last?['action'], 'consent.');
  });

  test('ten hanh dong trong nhat ky', () {
    expect(auditActionLabel('consent.withdrawn'), 'Rút đồng ý sinh trắc học');
    expect(auditActionLabel('enrollment.delete'), 'Xóa ghi danh');
    expect(auditActionLabel('student.create'), 'Thêm sinh viên');
    expect(auditActionLabel('la.thuong'), 'la.thuong');
  });

  testWidgets('trang tai khoan liet ke chuc nang cua vai tro', (tester) async {
    final api = _FakeApi();
    await tester.pumpWidget(_host(api, const AccountPage(), role: Roles.facultyLeader));
    await tester.pump();
    expect(find.text('Chức năng của Lãnh đạo Khoa'), findsOneWidget);
    expect(find.text('Duyệt vắng có phép cho sinh viên trong Khoa'), findsOneWidget);
    expect(find.textContaining('Không nhập liệu'), findsOneWidget);
  });
}
