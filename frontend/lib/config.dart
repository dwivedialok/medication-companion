/// App-wide configuration read from --dart-define at build time.
/// Defaults are wired for local development (backend on localhost).
class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );

  static const environment = String.fromEnvironment(
    'ENVIRONMENT',
    defaultValue: 'local',
  );

  /// True when running against the local backend (no Firebase auth required).
  static bool get isLocal => environment == 'local';

  /// When true, POST /prescription expects 202 + poll GET /jobs/{id}.
  /// Build with: --dart-define=ASYNC_PRESCRIPTION=true
  /// Keep false until broker has ASYNC_PRESCRIPTION=true (Phase C cutover).
  static const asyncPrescription = bool.fromEnvironment(
    'ASYNC_PRESCRIPTION',
    defaultValue: false,
  );
}
