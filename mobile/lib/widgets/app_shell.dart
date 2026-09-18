import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/auth_controller.dart';
import '../core/roles.dart';
import '../core/theme.dart';
import 'common.dart';
import 'notification_bell.dart';

class NavItem {
  const NavItem(this.path, this.label, this.icon);

  final String path;
  final String label;
  final IconData icon;
}

/// Menu dieu huong theo vai tro (khop voi _routeRoles trong router.dart).
List<NavItem> navItemsFor(String role) {
  switch (role) {
    case Roles.student:
      return const [
        NavItem('/', 'Trang chủ', Icons.home_outlined),
        NavItem('/schedule', 'Lịch học', Icons.calendar_month_outlined),
        NavItem('/my-attendance', 'Chuyên cần', Icons.fact_check_outlined),
        NavItem('/face', 'Khuôn mặt', Icons.face_retouching_natural_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    case Roles.parent:
      return const [
        NavItem('/', 'Con em', Icons.family_restroom_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    case Roles.lecturer:
      return const [
        NavItem('/', 'Trang chủ', Icons.home_outlined),
        NavItem('/schedule', 'Lịch dạy', Icons.calendar_month_outlined),
        NavItem('/classes', 'Lớp của tôi', Icons.class_outlined),
        NavItem('/sessions', 'Phiên điểm danh', Icons.how_to_reg_outlined),
        NavItem('/reports', 'Báo cáo', Icons.bar_chart_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    case Roles.admin:
      return const [
        NavItem('/', 'Tổng quan', Icons.dashboard_outlined),
        NavItem('/students', 'Sinh viên', Icons.school_outlined),
        NavItem('/lecturers', 'Giảng viên', Icons.co_present_outlined),
        NavItem('/classes', 'Lớp học phần', Icons.class_outlined),
        NavItem('/class-schedules', 'Lịch học', Icons.calendar_month_outlined),
        NavItem('/locations', 'Địa điểm điểm danh', Icons.place_outlined),
        NavItem('/sessions', 'Phiên điểm danh', Icons.how_to_reg_outlined),
        NavItem('/reports', 'Báo cáo', Icons.bar_chart_outlined),
        NavItem('/face-review', 'Duyệt khuôn mặt', Icons.face_outlined),
        NavItem('/parents', 'Phụ huynh', Icons.family_restroom_outlined),
        NavItem('/units', 'Đơn vị', Icons.apartment_outlined),
        NavItem('/staff', 'Cán bộ phòng ban', Icons.badge_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    case Roles.training:
      return const [
        NavItem('/', 'Tổng quan', Icons.dashboard_outlined),
        NavItem('/classes', 'Lớp học phần', Icons.class_outlined),
        NavItem('/class-schedules', 'Lịch học', Icons.calendar_month_outlined),
        NavItem('/locations', 'Địa điểm điểm danh', Icons.place_outlined),
        NavItem('/lecturers', 'Giảng viên', Icons.co_present_outlined),
        NavItem('/students', 'Sinh viên', Icons.school_outlined),
        NavItem('/sessions', 'Phiên điểm danh', Icons.how_to_reg_outlined),
        NavItem('/reports', 'Báo cáo', Icons.bar_chart_outlined),
        NavItem('/parents', 'Phụ huynh', Icons.family_restroom_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    case Roles.affairs:
      return const [
        NavItem('/', 'Tổng quan', Icons.dashboard_outlined),
        NavItem('/students', 'Sinh viên & duyệt phép', Icons.school_outlined),
        NavItem('/face-review', 'Duyệt khuôn mặt', Icons.face_outlined),
        NavItem('/parents', 'Phụ huynh', Icons.family_restroom_outlined),
        NavItem('/classes', 'Lớp học phần', Icons.class_outlined),
        NavItem('/sessions', 'Phiên điểm danh', Icons.how_to_reg_outlined),
        NavItem('/reports', 'Báo cáo', Icons.bar_chart_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    case Roles.faculty:
      return const [
        NavItem('/', 'Tổng quan Khoa', Icons.dashboard_outlined),
        NavItem('/students', 'Sinh viên & duyệt phép', Icons.school_outlined),
        NavItem('/lecturers', 'Giảng viên', Icons.co_present_outlined),
        NavItem('/classes', 'Lớp học phần', Icons.class_outlined),
        NavItem('/sessions', 'Phiên điểm danh', Icons.how_to_reg_outlined),
        NavItem('/reports', 'Báo cáo', Icons.bar_chart_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    case Roles.board:
      return const [
        NavItem('/', 'Thống kê tổng hợp', Icons.insights_outlined),
        NavItem('/account', 'Tài khoản', Icons.person_outline),
      ];
    default:
      return const [NavItem('/account', 'Tài khoản', Icons.person_outline)];
  }
}

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

/// Khung chung sau dang nhap: man hinh rong -> thanh dieu huong ben trai; man hinh
/// hep -> thanh duoi (<= 5 muc) hoac ngan keo.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final items = navItemsFor(auth.role);
    final selected = _selectedIndex(items, location);
    final isTopLevel = items.any((item) => item.path == location);
    final width = MediaQuery.sizeOf(context).width;
    final wide = width >= 900;
    final title = selected >= 0 ? items[selected].label : 'FAMS';

    void go(int index) => context.go(items[index].path);

    // Trang con (chi tiet lop, phien...) luon co nut quay lai. Khong dua vao canPop() luc
    // build: shell duoc build TRUOC khi navigator long ben trong cap nhat trang moi nen
    // doc ra trang thai cu; tai lai trang web o trang con cung khong co lich su de pop.
    final appBar = AppBar(
      automaticallyImplyLeading: !wide,
      leading: isTopLevel
          ? null
          : IconButton(
              tooltip: 'Quay lại',
              icon: const BackButtonIcon(),
              onPressed: () {
                final router = GoRouter.of(context);
                if (router.canPop()) {
                  router.pop();
                } else {
                  context.go(selected >= 0 ? items[selected].path : '/');
                }
              },
            ),
      title: Row(
        children: [
          if (wide) ...[
            const _Logo(),
            const SizedBox(width: 12),
          ],
          Flexible(child: Text(title, overflow: TextOverflow.ellipsis)),
        ],
      ),
      actions: [
        NotificationBell(role: auth.role),
        const SizedBox(width: 4),
        _AccountMenu(auth: auth),
        const SizedBox(width: 8),
      ],
    );

    if (wide) {
      return Scaffold(
        appBar: appBar,
        body: Row(
          children: [
            SingleChildScrollView(
              child: ConstrainedBox(
                constraints: BoxConstraints(minHeight: MediaQuery.sizeOf(context).height - kToolbarHeight),
                child: IntrinsicHeight(
                  child: NavigationRail(
                    extended: width >= 1200,
                    minExtendedWidth: 230,
                    selectedIndex: selected >= 0 ? selected : null,
                    onDestinationSelected: go,
                    labelType: width >= 1200 ? NavigationRailLabelType.none : NavigationRailLabelType.all,
                    destinations: [
                      for (final item in items)
                        NavigationRailDestination(icon: Icon(item.icon), label: Text(item.label)),
                    ],
                  ),
                ),
              ),
            ),
            const VerticalDivider(width: 1),
            Expanded(child: child),
          ],
        ),
      );
    }

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
                for (final item in items)
                  NavigationDrawerDestination(icon: Icon(item.icon), label: Text(item.label)),
              ],
            ),
      body: child,
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
  const _AccountMenu({required this.auth});

  final AuthController auth;

  @override
  Widget build(BuildContext context) {
    final me = auth.me;
    final initials = (me?.fullName.trim().isNotEmpty ?? false)
        ? me!.fullName.trim().split(RegExp(r'\s+')).last.characters.first.toUpperCase()
        : '?';
    return PopupMenuButton<String>(
      tooltip: 'Tài khoản',
      onSelected: (value) async {
        if (value == 'account') {
          context.go('/account');
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
        const PopupMenuItem(value: 'account', child: ListTile(leading: Icon(Icons.person_outline), title: Text('Tài khoản'))),
        const PopupMenuItem(value: 'logout', child: ListTile(leading: Icon(Icons.logout), title: Text('Đăng xuất'))),
      ],
      child: CircleAvatar(
        radius: 17,
        backgroundColor: Theme.of(context).colorScheme.primaryContainer,
        child: Text(initials, style: TextStyle(color: Theme.of(context).colorScheme.onPrimaryContainer)),
      ),
    );
  }
}
