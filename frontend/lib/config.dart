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
}
