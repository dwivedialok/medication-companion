import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../auth/firebase_auth_service.dart';
import '../config.dart';
import '../models/prescription_job.dart';
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

typedef JobStatusCallback = void Function(String status);

class ApiService {
  final FirebaseAuthService _auth;

  ApiService(this._auth);

  static const _pollDelaysSec = [2, 3, 5, 5, 10, 10, 15, 15, 15, 10];

  Future<Map<String, String>> _authHeaders() async {
    final token = await _auth.getIdToken();
    if (token != null) return {'Authorization': 'Bearer $token'};
    return {};
  }

  /// Upload image and run analysis (sync 200 or async 202 + poll).
  ///
  /// [onJobStatus] receives pending | processing | done | failed during async poll.
  Future<PrescriptionResult> analyzePrescription({
    required Uint8List imageBytes,
    required String mimeType,
    String language = 'en-IN',
    String fileName = 'prescription.jpg',
    JobStatusCallback? onJobStatus,
  }) async {
    final upload = await _uploadPrescriptionImage(
      imageBytes: imageBytes,
      mimeType: mimeType,
      fileName: fileName,
    );

    final analyzeResp = await _postPrescription(
      gcsUri: upload.gcsUri,
      language: language,
      contentType: upload.contentType,
    );

    if (analyzeResp.statusCode == 200) {
      final body = _decodeBody(analyzeResp) as Map<String, dynamic>;
      return PrescriptionResult.fromJson(body);
    }

    if (analyzeResp.statusCode == 202) {
      final body = _decodeBody(analyzeResp) as Map<String, dynamic>;
      final jobId = body['job_id'] as String?;
      if (jobId == null || jobId.isEmpty) {
        throw ApiException(202, 'Missing job_id in async response.');
      }
      onJobStatus?.call('pending');
      return waitForPrescriptionResult(
        jobId,
        onStatus: onJobStatus,
      );
    }

    return _handlePrescriptionError(analyzeResp);
  }

  Future<({String gcsUri, String contentType})> _uploadPrescriptionImage({
    required Uint8List imageBytes,
    required String mimeType,
    required String fileName,
  }) async {
    final base = _baseUrl;
    final headers = {
      ...await _authHeaders(),
      'Content-Type': 'application/json',
    };

    final uploadUrlResp = await http
        .post(
          Uri.parse('$base/upload-url'),
          headers: headers,
          body: jsonEncode({'content_type': mimeType}),
        )
        .timeout(const Duration(seconds: 30));

    final uploadBody = _decodeBody(uploadUrlResp);

    if (uploadUrlResp.statusCode == 200) {
      final uploadMap = uploadBody as Map<String, dynamic>;
      final signedPutUrl = uploadMap['upload_url'] as String;
      final gcsUri = uploadMap['gcs_uri'] as String;
      final contentType = uploadMap['content_type'] as String? ?? mimeType;

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
      return (gcsUri: gcsUri, contentType: contentType);
    }

    if (AppConfig.isLocal) {
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
      final map = directBody as Map<String, dynamic>;
      return (
        gcsUri: map['gcs_uri'] as String,
        contentType: map['content_type'] as String? ?? mimeType,
      );
    }

    throw ApiException(
      uploadUrlResp.statusCode,
      _errorMessage(uploadBody) ?? 'Could not prepare image upload.',
    );
  }

  Future<http.Response> _postPrescription({
    required String gcsUri,
    required String language,
    required String contentType,
  }) async {
    final base = _baseUrl;
    final headers = {
      ...await _authHeaders(),
      'Content-Type': 'application/json',
    };

    // Sync path: long timeout. Async path: broker returns quickly with 202.
    final timeout = AppConfig.asyncPrescription
        ? const Duration(seconds: 30)
        : const Duration(seconds: 120);

    return http
        .post(
          Uri.parse('$base/prescription'),
          headers: headers,
          body: jsonEncode({
            'gcs_uri': gcsUri,
            'language': language,
            'content_type': contentType,
          }),
        )
        .timeout(timeout);
  }

  Future<PrescriptionJob> getJobStatus(String jobId) async {
    final base = _baseUrl;
    final resp = await http
        .get(
          Uri.parse('$base/jobs/$jobId'),
          headers: await _authHeaders(),
        )
        .timeout(const Duration(seconds: 30));

    final body = _decodeBody(resp);
    if (resp.statusCode == 200) {
      return PrescriptionJob.fromJson(body as Map<String, dynamic>);
    }
    throw ApiException(
      resp.statusCode,
      _errorMessage(body) ?? 'Could not load job status.',
    );
  }

  Future<PrescriptionResult> waitForPrescriptionResult(
    String jobId, {
    JobStatusCallback? onStatus,
  }) async {
    for (final delaySec in _pollDelaysSec) {
      await Future.delayed(Duration(seconds: delaySec));
      final job = await getJobStatus(jobId);
      onStatus?.call(job.status);

      if (job.status == 'done') {
        final result = job.result;
        if (result == null) {
          throw ApiException(500, 'Job completed without a result.');
        }
        return result;
      }

      if (job.status == 'failed') {
        _throwFromJobError(job.error);
      }
    }

    throw ApiException(
      504,
      'Analysis is taking longer than expected. Please try again.',
    );
  }

  Never _throwFromJobError(PrescriptionJobError? error) {
    if (error?.code == 'gate1_reject') {
      throw RetakeRequiredException(
        error!.message.isNotEmpty
            ? error.message
            : 'The prescription image was not clear enough. Please retake the photo.',
      );
    }
    throw ApiException(
      500,
      error?.message ?? 'Analysis failed. Please try again.',
    );
  }

  Never _handlePrescriptionError(http.Response response) {
    final body = _decodeBody(response);

    if (response.statusCode == 422) {
      final message = (body is Map ? body['message'] : null) as String? ??
          'The prescription image was not clear enough. Please retake the photo.';
      throw RetakeRequiredException(message);
    }

    throw ApiException(
      response.statusCode,
      _errorMessage(body) ?? 'Something went wrong. Please try again.',
    );
  }

  String get _baseUrl => AppConfig.apiBaseUrl.replaceAll(RegExp(r'/+$'), '');

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
