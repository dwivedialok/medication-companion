import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

import '../config.dart';

/// Wraps Firebase Auth with a local-dev bypass.
///
/// In local mode (AppConfig.isLocal), no Firebase calls are made:
/// the user is always treated as signed-in and API requests carry no token
/// (the backend accepts them via DEV_PATIENT_ID bypass).
class FirebaseAuthService extends ChangeNotifier {
  FirebaseAuthService() {
    if (!AppConfig.isLocal) {
      FirebaseAuth.instance.authStateChanges().listen((user) {
        _user = user;
        notifyListeners();
      });
    }
  }

  User? _user;

  /// True when there is an authenticated user (or running in local dev mode).
  bool get isSignedIn => AppConfig.isLocal || _user != null;

  /// Display name for UI: email in prod, "Dev User" locally.
  String get displayName {
    if (AppConfig.isLocal) return 'Dev User';
    return _user?.email ?? _user?.displayName ?? 'User';
  }

  /// Returns the Firebase ID token to attach as a Bearer header.
  /// Returns null in local mode (backend bypass handles auth).
  Future<String?> getIdToken() async {
    if (AppConfig.isLocal) return null;
    return _user?.getIdToken();
  }

  Future<void> signInWithEmail(String email, String password) async {
    if (AppConfig.isLocal) {
      notifyListeners();
      return;
    }
    await FirebaseAuth.instance.signInWithEmailAndPassword(
      email: email,
      password: password,
    );
  }

  Future<void> createAccountWithEmail(String email, String password) async {
    if (AppConfig.isLocal) {
      notifyListeners();
      return;
    }
    await FirebaseAuth.instance.createUserWithEmailAndPassword(
      email: email,
      password: password,
    );
  }

  Future<void> signOut() async {
    if (AppConfig.isLocal) {
      notifyListeners();
      return;
    }
    await FirebaseAuth.instance.signOut();
    _user = null;
    notifyListeners();
  }
}
