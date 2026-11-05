import 'dart:math' as math;

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/theme.dart';
import 'app_shell.dart';
import 'common.dart';

/// Cac khoi dung trang chu theo bo cuc cong sinh vien: the thong tin ca nhan, o so, hang loi
/// tat, vong tien do. Dung chung cho trang chu cua moi vai tro.
///
/// Rong/hep xet theo be rong man hinh chu khong dung LayoutBuilder: cac khoi nay nam trong
/// IntrinsicHeight (de the cung hang cao bang nhau) ma LayoutBuilder khong chay duoc o do.
bool isWideScreen(BuildContext context) => MediaQuery.sizeOf(context).width >= kShellWide;

/// Mot hang the cao bang nhau; man hinh hep thi xep doc.
class CardRow extends StatelessWidget {
  const CardRow({super.key, required this.children, this.flexes});

  final List<Widget> children;

  /// Ti le chieu rong tung the, mac dinh chia deu.
  final List<int>? flexes;

  @override
  Widget build(BuildContext context) {
    if (!isWideScreen(context)) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < children.length; i++) ...[
            if (i > 0) const SizedBox(height: kCardGap),
            children[i],
          ],
        ],
      );
    }
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < children.length; i++) ...[
            if (i > 0) const SizedBox(width: kCardGap),
            Expanded(flex: flexes?[i] ?? 1, child: children[i]),
          ],
        ],
      ),
    );
  }
}

/// The thong tin nguoi dung: anh dai dien ben trai, cac cap nhan - gia tri chia hai cot.
class ProfileCard extends StatelessWidget {
  const ProfileCard({
    super.key,
    required this.title,
    required this.name,
    required this.fields,
    this.onDetail,
    this.trailing,
    this.footer,
  });

  final String title;
  final String name;
  final List<(String, String)> fields;
  final VoidCallback? onDetail;
  final Widget? trailing;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    final initial = name.trim().isEmpty ? '?' : name.trim().split(RegExp(r'\s+')).last.characters.first.toUpperCase();
    final colors = Theme.of(context).colorScheme;
    // Duoi 1100 px the chi rong chung 450 px: chia hai cot thi chu bi xuong dong lien tuc.
    final twoColumns = MediaQuery.sizeOf(context).width >= 1100;
    final half = (fields.length / 2).ceil();
    return SectionCard(
      title: title,
      trailing: trailing,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: twoColumns ? 112 : 76,
            child: Column(
              children: [
                CircleAvatar(
                  radius: twoColumns ? 46 : 32,
                  backgroundColor: colors.primaryContainer,
                  foregroundColor: colors.onPrimaryContainer,
                  child: Text(initial, style: TextStyle(fontSize: twoColumns ? 34 : 24, fontWeight: FontWeight.w600)),
                ),
                if (onDetail != null) ...[const SizedBox(height: 6), DetailLink(onTap: onDetail!)],
              ],
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (twoColumns)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: _Fields(fields.take(half).toList())),
                      const SizedBox(width: 12),
                      Expanded(child: _Fields(fields.skip(half).toList())),
                    ],
                  )
                else
                  _Fields(fields),
                if (footer != null) ...[const SizedBox(height: 10), footer!],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Fields extends StatelessWidget {
  const _Fields(this.fields);

  final List<(String, String)> fields;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final (label, value) in fields)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: Text.rich(
              TextSpan(
                style: TextStyle(color: colors.onSurfaceVariant, fontSize: 13.5),
                children: [
                  TextSpan(text: '$label: '),
                  TextSpan(text: value, style: TextStyle(color: colors.onSurface, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ),
      ],
    );
  }
}

/// Lien ket "Xem chi tiet" mau xanh.
class DetailLink extends StatelessWidget {
  const DetailLink({super.key, required this.onTap, this.label = 'Xem chi tiết', this.color});

  final VoidCallback onTap;
  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Text(label, style: TextStyle(color: color ?? AppColors.link, fontSize: 13)),
      ),
    );
  }
}

enum TileTone { plain, blue, amber }

/// O so: nhan, con so lon, lien ket chi tiet va bieu tuong tron ben phai.
class DashTile extends StatelessWidget {
  const DashTile({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    this.tone = TileTone.plain,
    this.note,
    this.onTap,
  });

  final String label;
  final String value;
  final IconData icon;
  final TileTone tone;

  /// Dong phu giai thich con so (vd noi dung nhac nho dau tien).
  final String? note;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = Theme.of(context).colorScheme;
    final (Color accent, Color background) = switch (tone) {
      TileTone.blue => (AppColors.tileBlue, isDark ? AppColors.tileBlue.withValues(alpha: 0.16) : AppColors.tileBlueBackground),
      TileTone.amber => (AppColors.tileAmber, isDark ? AppColors.tileAmber.withValues(alpha: 0.16) : AppColors.tileAmberBackground),
      TileTone.plain => (colors.onSurfaceVariant, colors.surface),
    };
    return Container(
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(4),
        boxShadow: const [BoxShadow(color: Color(0x1A000000), offset: Offset(-1, 1), blurRadius: 6)],
      ),
      padding: const EdgeInsets.all(15),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(label, style: TextStyle(color: accent, fontSize: 13)),
                const SizedBox(height: 4),
                Text(value, style: TextStyle(color: tone == TileTone.plain ? colors.onSurface : accent, fontSize: 28, height: 1.15)),
                if (note != null) ...[
                  const SizedBox(height: 2),
                  Text(note!, maxLines: 2, overflow: TextOverflow.ellipsis, style: TextStyle(color: colors.onSurfaceVariant, fontSize: 12.5)),
                ],
                if (onTap != null) ...[
                  const SizedBox(height: 6),
                  DetailLink(onTap: onTap!, color: tone == TileTone.amber ? AppColors.tileAmber : AppColors.link),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: accent)),
            child: Icon(icon, size: 17, color: accent),
          ),
        ],
      ),
    );
  }
}

/// Mot o nhac nho o tren va hai o so o duoi - cot phai cua tang dau trang chu.
class TileColumn extends StatelessWidget {
  const TileColumn({super.key, required this.top, required this.left, required this.right});

  final Widget top;
  final Widget left;
  final Widget right;

  @override
  Widget build(BuildContext context) {
    final pair = Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(child: left),
        const SizedBox(width: kCardGap),
        Expanded(child: right),
      ],
    );
    // Man hinh rong: chia deu chieu cao cua hang. Man hinh hep: nam trong danh sach cuon, chieu
    // cao khong gioi han nen khong dung Expanded duoc.
    if (!isWideScreen(context)) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [top, const SizedBox(height: kCardGap), IntrinsicHeight(child: pair)],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(child: top),
        const SizedBox(height: kCardGap),
        Expanded(child: pair),
      ],
    );
  }
}

/// Hang loi tat: moi o gom bieu tuong va nhan, toi da 8 o mot hang. It muc thi gian deu cho
/// kin hang, khong de trong mot nua ben phai.
class ShortcutGrid extends StatelessWidget {
  const ShortcutGrid({super.key, required this.items});

  final List<NavItem> items;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return LayoutBuilder(builder: (context, constraints) {
      final fit = ((constraints.maxWidth + kCardGap) / (120 + kCardGap)).floor();
      final columns = math.max(math.min(fit, math.min(items.length, 8)), 1);
      final width = (constraints.maxWidth - kCardGap * (columns - 1)) / columns;
      return Wrap(
        spacing: kCardGap,
        runSpacing: kCardGap,
        children: [
          for (final item in items)
            SizedBox(
              width: width,
              height: 112,
              child: Card(
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => context.go(item.path),
                  child: Padding(
                    padding: const EdgeInsets.all(8),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(item.icon, size: 30, color: AppColors.link),
                        const SizedBox(height: 12),
                        Text(
                          item.label,
                          textAlign: TextAlign.center,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: colors.onSurfaceVariant, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      );
    });
  }
}

/// Vong tien do kem so "da dat/tong" o duoi.
class ProgressRing extends StatelessWidget {
  const ProgressRing({super.key, required this.done, required this.total, this.color = AppColors.success});

  final int done;
  final int total;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final rest = math.max(total - done, 0);
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          height: 190,
          child: PieChart(PieChartData(
            startDegreeOffset: -90,
            sectionsSpace: 0,
            centerSpaceRadius: 62,
            sections: [
              if (done > 0) PieChartSectionData(value: done.toDouble(), color: color, radius: 22, showTitle: false),
              if (rest > 0 || total == 0)
                PieChartSectionData(value: total == 0 ? 1 : rest.toDouble(), color: AppColors.tileBlue, radius: 22, showTitle: false),
            ],
          )),
        ),
        const SizedBox(height: 12),
        Text('$done/$total', style: const TextStyle(fontWeight: FontWeight.w700)),
      ],
    );
  }
}
