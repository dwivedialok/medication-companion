import 'package:flutter_test/flutter_test.dart';
import 'package:medication_companion/config.dart';

void main() {
  test('AppConfig defaults to local development settings', () {
    expect(AppConfig.apiBaseUrl, 'http://localhost:8080');
    expect(AppConfig.environment, 'local');
    expect(AppConfig.isLocal, isTrue);
  });
}
