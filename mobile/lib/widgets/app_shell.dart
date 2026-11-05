import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/auth_controller.dart';
import '../core/formatters.dart';
import '../core/roles.dart';
import '../core/theme.dart';
import '../features/auth/account_page.dart';
import 'common.dart';
import 'notification_bell.dart';

/// Tu be rong nay tro len dung bo cuc may tinh: thanh tren cung + menu truot o mep trai.
const kShellWide = 900.0;
const _topBarHeight = 57.0;
const _menuWidth = 250.0;

/// Le hai ben noi dung tren man hinh rong, chua cho nut menu dinh mep trai.
const _sideInset = 50.0;

class NavItem {
  const NavItem(this.path, this.label, this.icon);

  final String path;
  final String label;
  final IconData icon;
}

/// Mot nhom trong menu. [title] null: muc dung rieng o dau menu (trang chu).
class NavGroup {
  const NavGroup(this.title, this.items);

  final String? title;
  final List<NavItem> items;
}

const _account = NavItem('/account', 'Tài khoản', Icons.person_outline);
const _personal = NavGroup('Cá nhân', [_account]);

const _students = NavItem('/students', 'Sinh viên', Icons.school_outlined);
const _studentsExcuse = NavItem('/students', 'Sinh viên & duyệt phép', Icons.school_outlined);
const _lecturers = NavItem('/lecturers', 'Giảng viên', Icons.co_present_outlined);
const _parents = NavItem('/parents', 'Phụ huynh', Icons.family_restroom_outlined);
const _classes = NavItem('/classes', 'Lớp học phần', Icons.class_outlined);
const _classSchedules = NavItem('/class-schedules', 'Lịch học', Icons.calendar_month_outlined);
const _rooms = NavItem('/rooms', 'Phòng học', Icons.meeting_room_outlined);
const _locations = NavItem('/locations', 'Địa điểm điểm danh', Icons.place_outlined);
const _sessions = NavItem('/sessions', 'Phiên điểm danh', Icons.how_to_reg_outlined);
const _reports = NavItem('/reports', 'Báo cáo', Icons.bar_chart_outlined);
const _faceReview = NavItem('/face-review', 'Duyệt khuôn mặt', Icons.face_outlined);

/// Menu dieu huong theo vai tro, chia nhom theo tung mang viec (khop voi _routeRoles trong
/// router.dart va ma tran quyen o backend/app/core/authz.py).
List<NavGroup> navGroupsFor(String role) {
  switch (role) {
    case Roles.student:
      return const [
        NavGroup(null, [NavItem('/', 'Trang chủ', Icons.home_outlined)]),
        NavGroup('Học tập', [
          NavItem('/schedule', 'Lịch học', Icons.calendar_month_outlined),
          NavItem('/my-attendance', 'Chuyên cần', Icons.fact_check_outlined),
        ]),
        NavGroup('Cá nhân', [
          NavItem('/face', 'Khuôn mặt', Icons.face_retouching_natural_outlined),
          _account,
        ]),
      ];
    case Roles.parent:
      return const [
        NavGroup(null, [NavItem('/', 'Con em', Icons.family_restroom_outlined)]),
        NavGroup('Theo dõi', [NavItem('/notifications', 'Thông báo', Icons.notifications_outlined)]),
        _personal,
      ];
    case Roles.lecturer:
      return const [
        NavGroup(null, [NavItem('/', 'Trang chủ', Icons.home_outlined)]),
        NavGroup('Giảng dạy', [
          NavItem('/schedule', 'Lịch dạy', Icons.calendar_month_outlined),
          NavItem('/classes', 'Lớp của tôi', Icons.class_outlined),
        ]),
        NavGroup('Điểm danh', [_sessions, _reports]),
        _personal,
      ];
    case Roles.admin:
      return const [
        NavGroup(null, [NavItem('/', 'Tổng quan', Icons.dashboard_outlined)]),
        NavGroup('Đào tạo', [_classes, _classSchedules, _rooms, _locations]),
        NavGroup('Điểm danh', [_sessions, _reports]),
        NavGroup('Hồ sơ', [_students, _faceReview, _lecturers, _parents]),
        NavGroup('Hệ thống', [
          NavItem('/units', 'Đơn vị', Icons.apartment_outlined),
          NavItem('/staff', 'Cán bộ phòng ban', Icons.badge_outlined),
          NavItem('/audit-logs', 'Nhật ký hệ thống', Icons.history_outlined),
        ]),
        _personal,
      ];
    case Roles.training:
      // Phong Dao tao: to chuc dao tao toan truong.
      return const [
        NavGroup(null, [NavItem('/', 'Tổng quan', Icons.dashboard_outlined)]),
        NavGroup('Đào tạo', [_classes, _classSchedules, _rooms, _locations, _lecturers]),
        NavGroup('Điểm danh', [_sessions, _reports]),
        NavGroup('Hồ sơ', [_students, _parents]),
        _personal,
      ];
    case Roles.affairs:
      // Phong CTSV: ho so sinh vien, khuon mat, duyet vang co phep.
      return const [
        NavGroup(null, [NavItem('/', 'Tổng quan', Icons.dashboard_outlined)]),
        NavGroup('Hồ sơ', [_studentsExcuse, _faceReview, _parents]),
        NavGroup('Điểm danh', [_reports, _sessions]),
        NavGroup('Đào tạo', [_classes]),
        _personal,
      ];
    case Roles.faculty:
      // Van phong Khoa: nhap lieu cua Khoa.
      return const [
        NavGroup(null, [NavItem('/', 'Tổng quan Khoa', Icons.dashboard_outlined)]),
        NavGroup('Nhập liệu', [_classes, _classSchedules]),
        NavGroup('Theo dõi', [_students, _lecturers, _sessions, _reports]),
        _personal,
      ];
    case Roles.facultyLeader:
      // Lanh dao Khoa: giam sat + phe duyet, khong nhap lieu.
      return const [
        NavGroup(null, [NavItem('/', 'Tổng quan Khoa', Icons.dashboard_outlined)]),
        NavGroup('Giám sát', [
          NavItem('/reports', 'Báo cáo & cảnh báo', Icons.bar_chart_outlined),
          _studentsExcuse,
          _sessions,
        ]),
        NavGroup('Danh mục', [_classes, _lecturers]),
        NavGroup('Hệ thống', [NavItem('/audit-logs', 'Nhật ký Khoa', Icons.history_outlined)]),
        _personal,
      ];
    case Roles.board:
      return const [
        NavGroup(null, [NavItem('/', 'Thống kê tổng hợp', Icons.insights_outlined)]),
        _personal,
      ];
    default:
      return const [_personal];
  }
}

List<NavItem> navItemsFor(String role) => [for (final group in navGroupsFor(role)) ...group.items];

/// Cac o loi tat o trang chu: moi chuc nang, tru trang chu va tai khoan (da co o thanh tren).
List<NavItem> shortcutsFor(String role) =>
    navItemsFor(role).where((item) => item.path != '/' && item.path != '/account').toList();

int _selectedIndex(List<NavItem> items, String location) {
  var best = -1;
  var bestLength = -1;
  for (var i = 0; i < items.length; i++) {
    final path = items[i].path;
    final matches = path == '/' ? location == '/' : (location == path || location.startsWith('$path/'));
    if (matches && path.length > bestLength) {
      best = i;
      bestLength = path.length;
    }
  }
  return best;
}

/// Khung chung sau dang nhap, theo bo cuc cong sinh vien cua truong.
/// Man hinh rong: thanh tren cung + nut menu dinh mep trai, bam moi truot menu ra de nhuong
/// toan bo chieu ngang cho noi dung. Man hinh hep: thanh duoi (<= 5 muc) hoac ngan keo.
class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  bool _menuOpen = false;

  @override
  void didUpdateWidget(covariant AppShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.location != widget.location) _menuOpen = false;
  }

  void _back(BuildContext context, List<NavItem> items, int selected) {
    final router = GoRouter.of(context);
    if (router.canPop()) {
      router.pop();
    } else {
      context.go(selected >= 0 ? items[selected].path : '/');
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final items = navItemsFor(auth.role);
    final selected = _selectedIndex(items, widget.location);
    final isTopLevel = items.any((item) => item.path == widget.location);
    final title = selected >= 0 ? items[selected].label : 'FAMS';
    final wide = MediaQuery.sizeOf(context).width >= kShellWide;

    if (wide) {
      return Scaffold(
        body: Stack(
          children: [
            Positioned.fill(
              top: _topBarHeight,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: _sideInset),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // Trang chu tu co the thong tin o dau, khong can dong tieu de.
                    if (widget.location != '/')
                      _PageHeading(title: title, onBack: isTopLevel ? null : () => _back(context, items, selected)),
                    Expanded(child: widget.child),
                  ],
                ),
              ),
            ),
            if (_menuOpen)
              Positioned.fill(
                top: _topBarHeight,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTap: () => setState(() => _menuOpen = false),
                  child: const ColoredBox(color: Color(0x14000000)),
                ),
              ),
            AnimatedPositioned(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              top: _topBarHeight + 25,
              bottom: 16,
              left: _menuOpen ? 0 : -_menuWidth,
              width: _menuWidth + 50,
              child: _SlideMenu(
                groups: navGroupsFor(auth.role),
                location: widget.location,
                open: _menuOpen,
                onToggle: () => setState(() => _menuOpen = !_menuOpen),
              ),
            ),
            Positioned(top: 0, left: 0, right: 0, height: _topBarHeight, child: _TopBar(auth: auth, items: items)),
          ],
        ),
      );
    }

    void go(int index) => context.go(items[index].path);

    // Trang con (chi tiet lop, phien...) luon co nut quay lai. Khong dua vao canPop() luc
    // build: shell duoc build TRUOC khi navigator long ben trong cap nhat trang moi nen
    // doc ra trang thai cu; tai lai trang web o trang con cung khong co lich su de pop.
    final appBar = AppBar(
      leading: isTopLevel
          ? null
          : IconButton(tooltip: 'Quay lại', icon: const BackButtonIcon(), onPressed: () => _back(context, items, selected)),
      title: Text(title, overflow: TextOverflow.ellipsis),
      actions: [
        NotificationBell(role: auth.role),
        const SizedBox(width: 4),
        _AccountMenu(auth: auth),
        const SizedBox(width: 8),
      ],
    );

    final useBottomBar = items.length <= 5;
    return Scaffold(
      appBar: appBar,
      drawer: useBottomBar
          ? null
          : NavigationDrawer(
              selectedIndex: selected >= 0 ? selected : null,
              onDestinationSelected: (index) {
                Navigator.pop(context);
                go(index);
              },
              children: [
                const Padding(padding: EdgeInsets.fromLTRB(24, 20, 16, 12), child: _Logo()),
                for (final group in navGroupsFor(auth.role)) ...[
                  if (group.title != null) _GroupTitle(group.title!, padding: const EdgeInsets.fromLTRB(28, 16, 16, 8)),
                  for (final item in group.items)
                    NavigationDrawerDestination(icon: Icon(item.icon), label: Text(item.label)),
                ],
              ],
            ),
      body: widget.child,
      bottomNavigationBar: useBottomBar && items.length >= 2
          ? NavigationBar(
              selectedIndex: selected >= 0 ? selected : 0,
              onDestinationSelected: go,
              labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
              destinations: [
                for (final item in items) NavigationDestination(icon: Icon(item.icon), label: item.label),
              ],
            )
          : null,
    );
  }
}

/// Dong tieu de trang tren man hinh rong, can le theo vung noi dung.
class _PageHeading extends StatelessWidget {
  const _PageHeading({required this.title, this.onBack});

  final String title;
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: kContentMaxWidth + 32),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
          child: Row(
            children: [
              if (onBack != null) ...[
                IconButton(tooltip: 'Quay lại', icon: const BackButtonIcon(), onPressed: onBack, visualDensity: VisualDensity.compact),
                const SizedBox(width: 4),
              ],
              Flexible(
                child: Text(
                  title,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: 20, fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GroupTitle extends StatelessWidget {
  const _GroupTitle(this.title, {required this.padding});

  final String title;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding,
      child: Text(
        title.toUpperCase(),
        style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant, fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.4),
      ),
    );
  }
}

/// Menu truot: khi dong chi con nut luoi dinh o mep trai man hinh.
class _SlideMenu extends StatelessWidget {
  const _SlideMenu({required this.groups, required this.location, required this.open, required this.onToggle});

  final List<NavGroup> groups;
  final String location;
  final bool open;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final items = [for (final group in groups) ...group.items];
    final selected = _selectedIndex(items, location);
    final current = selected >= 0 ? items[selected] : null;
    const shadow = [BoxShadow(color: Color(0x1A000000), offset: Offset(3, 3), blurRadius: 3, spreadRadius: -2)];
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: _menuWidth,
          child: ExcludeFocus(
            excluding: !open,
            child: Container(
              decoration: BoxDecoration(color: colors.surface, boxShadow: open ? shadow : null),
              child: Material(
                type: MaterialType.transparency,
                child: ListView(
                  shrinkWrap: true,
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  children: [
                    for (final group in groups) ...[
                      if (group.title != null) _GroupTitle(group.title!, padding: const EdgeInsets.fromLTRB(16, 14, 16, 6)),
                      for (final item in group.items)
                        ListTile(
                          dense: true,
                          selected: identical(item, current),
                          selectedColor: colors.primary,
                          selectedTileColor: colors.primary.withValues(alpha: 0.08),
                          leading: Icon(item.icon, size: 20),
                          minLeadingWidth: 24,
                          title: Text(item.label, style: const TextStyle(fontSize: 14)),
                          onTap: () {
                            if (location == item.path) {
                              onToggle();
                            } else {
                              context.go(item.path);
                            }
                          },
                        ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
        Container(
          width: 50,
          height: 45,
          decoration: BoxDecoration(color: colors.surface, boxShadow: shadow),
          child: IconButton(
            tooltip: open ? 'Đóng menu' : 'Mở menu',
            icon: Icon(open ? Icons.close : Icons.apps, color: colors.onSurfaceVariant),
            onPressed: onToggle,
          ),
        ),
      ],
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.auth, required this.items});

  final AuthController auth;
  final List<NavItem> items;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      decoration: BoxDecoration(
        color: colors.surface,
        boxShadow: const [BoxShadow(color: Color(0x33000000), offset: Offset(0, 1), blurRadius: 4)],
      ),
      padding: const EdgeInsets.symmetric(horizontal: _sideInset + 16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: kContentMaxWidth),
          child: Row(
            children: [
              InkWell(onTap: () => context.go('/'), child: const _Logo()),
              const SizedBox(width: 24),
              Expanded(child: Align(alignment: Alignment.centerLeft, child: _MenuSearch(items: items))),
              const SizedBox(width: 16),
              TextButton.icon(
                onPressed: () => context.go('/'),
                style: TextButton.styleFrom(foregroundColor: colors.onSurfaceVariant),
                icon: const Icon(Icons.home_outlined, size: 18),
                label: const Text('Trang chủ'),
              ),
              const SizedBox(width: 4),
              NotificationBell(role: auth.role),
              const SizedBox(width: 8),
              _AccountMenu(auth: auth, showName: true),
            ],
          ),
        ),
      ),
    );
  }
}

/// O tim kiem tren thanh tren cung: tim nhanh chuc nang trong menu cua vai tro, go khong dau
/// cung duoc.
class _MenuSearch extends StatefulWidget {
  const _MenuSearch({required this.items});

  final List<NavItem> items;

  @override
  State<_MenuSearch> createState() => _MenuSearchState();
}

class _MenuSearchState extends State<_MenuSearch> {
  final _controller = TextEditingController();
  final _focus = FocusNode();

  @override
  void dispose() {
    _controller.dispose();
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final border = OutlineInputBorder(
      borderRadius: BorderRadius.circular(20),
      borderSide: BorderSide(color: colors.outlineVariant),
    );
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 280),
      child: Autocomplete<NavItem>(
        textEditingController: _controller,
        focusNode: _focus,
        displayStringForOption: (item) => item.label,
        optionsBuilder: (value) {
          final query = plainText(value.text.trim());
          if (query.isEmpty) return const Iterable<NavItem>.empty();
          return widget.items.where((item) => plainText(item.label).contains(query));
        },
        onSelected: (item) {
          _controller.clear();
          _focus.unfocus();
          context.go(item.path);
        },
        fieldViewBuilder: (context, controller, focusNode, onSubmit) => TextField(
          controller: controller,
          focusNode: focusNode,
          onSubmitted: (_) => onSubmit(),
          style: const TextStyle(fontSize: 14),
          decoration: InputDecoration(
            hintText: 'Tìm chức năng…',
            isDense: true,
            contentPadding: const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
            suffixIcon: const Icon(Icons.search, size: 20),
            border: border,
            enabledBorder: border,
          ),
        ),
      ),
    );
  }
}

class _Logo extends StatelessWidget {
  const _Logo();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 32,
          height: 32,
          alignment: Alignment.center,
          decoration: BoxDecoration(color: AppColors.brand, borderRadius: BorderRadius.circular(8)),
          child: const Text('FA', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
        ),
        const SizedBox(width: 8),
        const Text('FAMS', style: TextStyle(fontWeight: FontWeight.w800)),
      ],
    );
  }
}

class _AccountMenu extends StatelessWidget {
  const _AccountMenu({required this.auth, this.showName = false});

  final AuthController auth;
  final bool showName;

  @override
  Widget build(BuildContext context) {
    final me = auth.me;
    final initials = (me?.fullName.trim().isNotEmpty ?? false)
        ? me!.fullName.trim().split(RegExp(r'\s+')).last.characters.first.toUpperCase()
        : '?';
    final colors = Theme.of(context).colorScheme;
    return PopupMenuButton<String>(
      tooltip: 'Tài khoản',
      onSelected: (value) async {
        if (value == 'account') {
          context.go('/account');
        } else if (value == 'password') {
          await showDialog<void>(context: context, builder: (_) => const ChangePasswordDialog());
        } else if (value == 'logout') {
          final ok = await confirmDialog(context, title: 'Đăng xuất', message: 'Bạn muốn đăng xuất khỏi FAMS?', confirmLabel: 'Đăng xuất');
          if (ok) await auth.logout();
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem<String>(
          enabled: false,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(me?.fullName ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(Roles.label(auth.role), style: const TextStyle(fontSize: 12)),
            ],
          ),
        ),
        const PopupMenuDivider(),
        const PopupMenuItem(value: 'account', child: ListTile(leading: Icon(Icons.person_outline), title: Text('Thông tin cá nhân'))),
        const PopupMenuItem(value: 'password', child: ListTile(leading: Icon(Icons.lock_reset), title: Text('Đổi mật khẩu'))),
        const PopupMenuItem(value: 'logout', child: ListTile(leading: Icon(Icons.logout), title: Text('Đăng xuất'))),
      ],
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(
            radius: 17,
            backgroundColor: colors.primaryContainer,
            child: Text(initials, style: TextStyle(color: colors.onPrimaryContainer)),
          ),
          if (showName) ...[
            const SizedBox(width: 8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 180),
              child: Text(me?.fullName ?? '', overflow: TextOverflow.ellipsis, style: TextStyle(color: colors.onSurfaceVariant, fontSize: 14)),
            ),
            Icon(Icons.arrow_drop_down, color: colors.onSurfaceVariant),
          ],
        ],
      ),
    );
  }
}
