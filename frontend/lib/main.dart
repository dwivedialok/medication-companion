import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'auth/firebase_auth_service.dart';
import 'config.dart';
import 'firebase_options.dart';
import 'l10n/app_localizations.dart';
import 'models/prescription_result.dart';
import 'providers/locale_provider.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/result_screen.dart';
import 'screens/upload_screen.dart';
import 'services/api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase is only needed in production. Local dev uses DEV_PATIENT_ID bypass.
  if (!AppConfig.isLocal) {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  }

  runApp(const MedicationCompanionApp());
}

class MedicationCompanionApp extends StatelessWidget {
  const MedicationCompanionApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => LocaleProvider()),
        ChangeNotifierProvider(create: (_) => FirebaseAuthService()),
        ProxyProvider<FirebaseAuthService, ApiService>(
          update: (_, auth, __) => ApiService(auth),
        ),
      ],
      child: Builder(
        builder: (context) {
          final auth = context.watch<FirebaseAuthService>();
          final locale = context.watch<LocaleProvider>().locale;
          final router = _buildRouter(auth);
          return MaterialApp.router(
            title: 'Medication Companion',
            theme: _theme(),
            locale: locale,
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
            routerConfig: router,
            debugShowCheckedModeBanner: false,
          );
        },
      ),
    );
  }

  GoRouter _buildRouter(FirebaseAuthService auth) {
    return GoRouter(
      initialLocation: '/',
      refreshListenable: auth,
      redirect: (context, state) {
        final signedIn = auth.isSignedIn;
        final onLogin = state.matchedLocation == '/login';

        if (!signedIn && !onLogin) return '/login';
        if (signedIn && onLogin) return '/home';
        return null;
      },
      routes: [
        GoRoute(
          path: '/',
          redirect: (_, __) => '/home',
        ),
        GoRoute(
          path: '/login',
          builder: (_, __) => const LoginScreen(),
        ),
        GoRoute(
          path: '/home',
          builder: (_, __) => const HomeScreen(),
        ),
        GoRoute(
          path: '/upload',
          builder: (context, state) {
            final extra = state.extra as Map<String, dynamic>? ?? {};
            final localeProvider = context.read<LocaleProvider>();
            return UploadScreen(
              language: extra['language'] as String? ?? localeProvider.languageCode,
            );
          },
        ),
        GoRoute(
          path: '/result',
          builder: (context, state) {
            final result = state.extra as PrescriptionResult;
            return ResultScreen(result: result);
          },
        ),
      ],
    );
  }

  ThemeData _theme() {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF1565C0), // NHS-style deep blue
        brightness: Brightness.light,
      ),
    );
  }
}
