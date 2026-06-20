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

  /// Analyse a prescription image via the auth broker:
  /// 1. POST /upload-url → signed GCS PUT URL
  /// 2. PUT image bytes to GCS
  /// 3. POST /prescription with gcs_uri + language
  ///
  /// [mimeType] should be one of: image/jpeg, image/png, image/webp
  /// [language] is the BCP-47 target language for audio (default: en-IN)
  Future<PrescriptionResult> analyzePrescription({
    required Uint8List imageBytes,
    required String mimeType,
    String language = 'en-IN',
    String fileName = 'prescription.jpg',
  }) async {
    final base = AppConfig.apiBaseUrl.replaceAll(RegExp(r'/+$'), '');
    final headers = {
      ...await _authHeaders(),
      'Content-Type': 'application/json',
    };

    // Step 1: request signed upload URL (production path)
    final uploadUrlResp = await http
        .post(
          Uri.parse('$base/upload-url'),
          headers: headers,
          body: jsonEncode({'content_type': mimeType}),
        )
        .timeout(const Duration(seconds: 30));

    final uploadBody = _decodeBody(uploadUrlResp);
    String gcsUri;
    String contentType;

    if (uploadUrlResp.statusCode == 200) {
      final uploadMap = uploadBody as Map<String, dynamic>;
      final signedPutUrl = uploadMap['upload_url'] as String;
      gcsUri = uploadMap['gcs_uri'] as String;
      contentType = uploadMap['content_type'] as String? ?? mimeType;

      final putResp = await http
          .put(
            Uri.parse(signedPutUrl),
            headers: {'Content-Type': contentType},
            body: imageBytes,
          )
          .timeout(const Duration(seconds: 60));

      if (putResp.statusCode < 200 || putResp.statusCode >= 300) {
        throw ApiException(
          putResp.statusCode,
          'Image upload failed (${putResp.statusCode}). Please try again.',
        );
      }
    } else if (AppConfig.isLocal) {
      // Local dev fallback when user ADC cannot sign GCS URLs
      final multipartRequest = http.MultipartRequest(
        'POST',
        Uri.parse('$base/upload-direct'),
      );
      multipartRequest.headers.addAll(await _authHeaders());
      multipartRequest.files.add(
        http.MultipartFile.fromBytes(
          'image',
          imageBytes,
          filename: fileName,
          contentType: MediaType.parse(mimeType),
        ),
      );
      final directStreamed = await multipartRequest.send().timeout(
        const Duration(seconds: 60),
      );
      final directRespBody = await http.Response.fromStream(directStreamed);
      final directBody = _decodeBody(directRespBody);
      if (directRespBody.statusCode != 200) {
        throw ApiException(
          directRespBody.statusCode,
          _errorMessage(directBody) ?? 'Local image upload failed.',
        );
      }
      gcsUri = (directBody as Map<String, dynamic>)['gcs_uri'] as String;
      contentType =
          (directBody)['content_type'] as String? ?? mimeType;
    } else {
      throw ApiException(
        uploadUrlResp.statusCode,
        _errorMessage(uploadBody) ?? 'Could not prepare image upload.',
      );
    }

    // Step 3: trigger analysis via auth broker → Agent Runtime
    final analyzeResp = await http
        .post(
          Uri.parse('$base/prescription'),
          headers: headers,
          body: jsonEncode({
            'gcs_uri': gcsUri,
            'language': language,
            'content_type': contentType,
          }),
        )
        .timeout(const Duration(seconds: 120));

    final body = _decodeBody(analyzeResp);

    if (analyzeResp.statusCode == 200) {
      return PrescriptionResult.fromJson(body as Map<String, dynamic>);
    }

    if (analyzeResp.statusCode == 422) {
      final message = (body as Map<String, dynamic>)['message'] as String? ??
          'The prescription image was not clear enough. Please retake the photo.';
      throw RetakeRequiredException(message);
    }

    throw ApiException(
      analyzeResp.statusCode,
      _errorMessage(body) ?? 'Something went wrong. Please try again.',
    );
  }

  String? _errorMessage(dynamic body) {
    if (body is Map) {
      return (body['message'] ?? body['detail'])?.toString();
    }
    return null;
  }

  dynamic _decodeBody(http.Response response) {
    try {
      return jsonDecode(response.body);
    } catch (_) {
      return response.body;
    }
  }
}
