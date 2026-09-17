import 'dart:async';

import 'package:flutter/material.dart';

import '../core/api_client.dart';
import 'common.dart';

/// Danh sach co o tim kiem + phan trang theo X-Total-Count - dung cho cac trang quan
/// ly (sinh vien, giang vien, lop, lich, phu huynh, can bo).
class PagedList<T> extends StatefulWidget {
  const PagedList({
    super.key,
    required this.fetch,
    required this.itemBuilder,
    this.searchHint = 'Tìm kiếm…',
    this.filters,
    this.actions,
    this.emptyMessage = 'Không có dữ liệu',
    this.emptyIcon = Icons.inbox_outlined,
    this.pageSize = 20,
    this.filterKey,
  });

  final Future<PageResult<T>> Function(String query, int offset, int limit) fetch;
  final Widget Function(BuildContext context, T item, VoidCallback reload) itemBuilder;
  final String searchHint;

  /// Widget bo loc them (dropdown khoa, hoc ky...) dat canh o tim kiem.
  final List<Widget>? filters;

  /// Nut thao tac (vd "Thêm") o dau danh sach; nhan ham reload de goi sau khi tao.
  final List<Widget> Function(VoidCallback reload)? actions;
  final String emptyMessage;
  final IconData emptyIcon;
  final int pageSize;

  /// Doi gia tri nay khi bo loc thay doi de tai lai tu trang dau.
  final Object? filterKey;

  @override
  State<PagedList<T>> createState() => _PagedListState<T>();
}

class _PagedListState<T> extends State<PagedList<T>> {
  final _search = TextEditingController();
  Timer? _debounce;
  List<T> _items = [];
  int _total = 0;
  int _page = 0;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant PagedList<T> oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.filterKey != widget.filterKey) {
      _page = 0;
      _load();
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await widget.fetch(_search.text.trim(), _page * widget.pageSize, widget.pageSize);
      if (!mounted) return;
      setState(() {
        _items = result.items;
        _total = result.total;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = errorText(e);
        _loading = false;
      });
    }
  }

  void _onSearchChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      _page = 0;
      _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final pageCount = (_total / widget.pageSize).ceil();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SizedBox(
              width: 320,
              child: TextField(
                controller: _search,
                onChanged: _onSearchChanged,
                decoration: InputDecoration(prefixIcon: const Icon(Icons.search), hintText: widget.searchHint),
              ),
            ),
            ...?widget.filters,
            ...?widget.actions?.call(_load),
          ],
        ),
        const SizedBox(height: 12),
        if (_loading) const LinearProgressIndicator(minHeight: 2) else const SizedBox(height: 2),
        if (_error != null)
          ErrorView(message: _error!, onRetry: _load)
        else if (!_loading && _items.isEmpty)
          EmptyView(icon: widget.emptyIcon, message: widget.emptyMessage)
        else
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              children: [
                for (var i = 0; i < _items.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  widget.itemBuilder(context, _items[i], _load),
                ],
              ],
            ),
          ),
        if (pageCount > 1)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Text('Tổng $_total · Trang ${_page + 1}/$pageCount'),
                IconButton(
                  onPressed: _page > 0 && !_loading
                      ? () {
                          _page--;
                          _load();
                        }
                      : null,
                  icon: const Icon(Icons.chevron_left),
                ),
                IconButton(
                  onPressed: _page + 1 < pageCount && !_loading
                      ? () {
                          _page++;
                          _load();
                        }
                      : null,
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
