import 'prescription_result.dart';

/// Job status from GET /jobs/{job_id} (mirrors backend PrescriptionJobStatus).
class PrescriptionJob {
  final String jobId;
  final String patientId;
  final String status; // pending | processing | done | failed
  final PrescriptionResult? result;
  final PrescriptionJobError? error;

  const PrescriptionJob({
    required this.jobId,
    required this.patientId,
    required this.status,
    this.result,
    this.error,
  });

  factory PrescriptionJob.fromJson(Map<String, dynamic> json) => PrescriptionJob(
        jobId: json['job_id'] as String? ?? '',
        patientId: json['patient_id'] as String? ?? '',
        status: json['status'] as String? ?? 'pending',
        result: json['result'] != null
            ? PrescriptionResult.fromJson(
                json['result'] as Map<String, dynamic>,
              )
            : null,
        error: json['error'] != null
            ? PrescriptionJobError.fromJson(
                json['error'] as Map<String, dynamic>,
              )
            : null,
      );

  bool get isTerminal => status == 'done' || status == 'failed';
}

class PrescriptionJobError {
  final String code; // gate1_reject | pipeline_error | internal_error
  final String message;
  final String? reason;

  const PrescriptionJobError({
    required this.code,
    required this.message,
    this.reason,
  });

  factory PrescriptionJobError.fromJson(Map<String, dynamic> json) =>
      PrescriptionJobError(
        code: json['code'] as String? ?? 'internal_error',
        message: json['message'] as String? ?? 'Something went wrong.',
        reason: json['reason'] as String?,
      );
}
