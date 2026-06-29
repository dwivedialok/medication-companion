/// Lightweight history row returned by GET /prescriptions.
/// Mirrors backend PrescriptionHistoryItem in schemas.py.
class PrescriptionHistoryItem {
  final String jobId;
  final String status; // pending | processing | done | failed
  final DateTime createdAt;
  final DateTime updatedAt;
  final String language;
  final String? overallSeverity; // HIGH | MODERATE | LOW | INFO | NONE
  final int? drugCount;
  final String? summaryOneLiner;
  final String? errorCode;
  final String? errorMessage;

  const PrescriptionHistoryItem({
    required this.jobId,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.language,
    this.overallSeverity,
    this.drugCount,
    this.summaryOneLiner,
    this.errorCode,
    this.errorMessage,
  });

  bool get isTerminal => status == 'done' || status == 'failed';
  bool get isReady => status == 'done';
  bool get isInProgress => status == 'pending' || status == 'processing';
  bool get isGate1Reject => errorCode == 'gate1_reject';

  factory PrescriptionHistoryItem.fromJson(Map<String, dynamic> json) {
    DateTime parseDate(String? raw) {
      if (raw == null || raw.isEmpty) return DateTime.fromMillisecondsSinceEpoch(0);
      return DateTime.tryParse(raw)?.toLocal() ??
          DateTime.fromMillisecondsSinceEpoch(0);
    }

    return PrescriptionHistoryItem(
      jobId: json['job_id'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
      createdAt: parseDate(json['created_at'] as String?),
      updatedAt: parseDate(json['updated_at'] as String?),
      language: json['language'] as String? ?? 'en-IN',
      overallSeverity: json['overall_severity'] as String?,
      drugCount: json['drug_count'] as int?,
      summaryOneLiner: json['summary_one_liner'] as String?,
      errorCode: json['error_code'] as String?,
      errorMessage: json['error_message'] as String?,
    );
  }
}
