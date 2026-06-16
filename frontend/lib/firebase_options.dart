// lib/firebase_options.dart
//
// STUB — replace with the output of:
//   flutterfire configure --project=<your-firebase-project-id>
//
// For local development (ENVIRONMENT=local), Firebase is bypassed entirely
// and this file is never imported. You only need to run `flutterfire configure`
// before deploying to production (Phase 4).

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart' show defaultTargetPlatform, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform {
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
      case TargetPlatform.iOS:
      case TargetPlatform.macOS:
      case TargetPlatform.windows:
      case TargetPlatform.linux:
        throw UnsupportedError(
          'DefaultFirebaseOptions are not configured for this platform. '
          'Run `flutterfire configure` to generate the correct options.',
        );
      default:
        // Web — replace these placeholder values with the real ones
        return const FirebaseOptions(
          apiKey: 'REPLACE_WITH_REAL_API_KEY',
          appId: 'REPLACE_WITH_REAL_APP_ID',
          messagingSenderId: 'REPLACE_WITH_REAL_SENDER_ID',
          projectId: 'REPLACE_WITH_REAL_PROJECT_ID',
          storageBucket: 'REPLACE_WITH_REAL_BUCKET',
          authDomain: 'REPLACE_WITH_REAL_AUTH_DOMAIN',
        );
    }
  }
}
