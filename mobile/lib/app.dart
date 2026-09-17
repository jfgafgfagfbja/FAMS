import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/auth_controller.dart';
import 'core/theme.dart';
import 'core/token_storage.dart';
import 'router.dart';

class FamsApp extends StatefulWidget {
  const FamsApp({super.key});

  @override
  State<FamsApp> createState() => _FamsAppState();
}

class _FamsAppState extends State<FamsApp> {
  final _storage = TokenStorage();
  late final ApiClient _api = ApiClient(storage: _storage);
  late final AuthController _auth = AuthController(_api);
  late final ThemeController _theme = ThemeController(_storage);
  late final GoRouter _router = buildRouter(_auth);

  @override
  void initState() {
    super.initState();
    _theme.load();
    _auth.bootstrap();
  }

  @override
  void dispose() {
    _router.dispose();
    _auth.dispose();
    _theme.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: _api),
        ChangeNotifierProvider<AuthController>.value(value: _auth),
        ChangeNotifierProvider<ThemeController>.value(value: _theme),
      ],
      child: Consumer<ThemeController>(
        builder: (context, theme, _) => MaterialApp.router(
          title: 'FAMS - Điểm danh khuôn mặt',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: theme.mode,
          routerConfig: _router,
          locale: const Locale('vi'),
          supportedLocales: const [Locale('vi'), Locale('en')],
          localizationsDelegates: GlobalMaterialLocalizations.delegates,
        ),
      ),
    );
  }
}
