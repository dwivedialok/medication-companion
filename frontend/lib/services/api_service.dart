import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../auth/firebase_auth_service.dart';
import '../config.dart';
import '../models/prescription_result.dart';

/// Thrown when the prescription image cannot be read (Gate 1 reject).
class RetakeRequiredException implements Exception {
  final String message;
  const RetakeRequiredException(this.message);

  @override
  String toString() => message;
}

/// Thrown when the server returns a non-success status.
class ApiException implements Exception {
  final int statusCode;
  final String message;
  const ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiService {
  final FirebaseAuthService _auth;

  ApiService(this._auth);

  Future<Map<String, String>> _authHeaders() async {
    final token = await _auth.getIdToken();
    if (token != null) return {'Authorization': 'Bearer $token'};
    return {};
  }

  /// POST /prescription — multipart upload of [imageBytes].
  ///
  /// [mimeType] should be one of: image/jpeg, image/png, image/webp
  /// [language] is the BCP-47 target language for audio (default: en-IN)
  Future<PrescriptionResult> analyzePrescription({
    required Uint8List imageBytes,
    required String mimeType,
    String language = 'en-IN',
    String fileName = 'prescription.jpg',
  }) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/prescription');
    final headers = await _authHeaders();

    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(headers)
      ..fields['language'] = language
      ..files.add(http.MultipartFile.fromBytes(
        'image',
        imageBytes,
        filename: fileName,
        contentType: MediaType.parse(mimeType),
      ));

    final streamedResponse = await request.send().timeout(
      const Duration(seconds: 120),
    );
    final response = await http.Response.fromStream(streamedResponse);

    final body = _decodeBody(response);

    if (response.statusCode == 200) {
      return PrescriptionResult.fromJson(body as Map<String, dynamic>);
    }

    if (response.statusCode == 422) {
      final message = (body as Map<String, dynamic>)['message'] as String? ??
          'The prescription image was not clear enough. Please retake the photo.';
      throw RetakeRequiredException(message);
    }

    final message = (body is Map ? body['message'] ?? body['detail'] : null) ??
        'Something went wrong. Please try again.';
    throw ApiException(response.statusCode, message.toString());
  }

  dynamic _decodeBody(http.Response response) {
    try {
      return jsonDecode(response.body);
    } catch (_) {
      return response.body;
    }
  }
}
