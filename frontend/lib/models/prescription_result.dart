/// Dart models mirroring backend/schemas.py.
/// All fromJson constructors handle null-safety gracefully.

class ResolvedDrug {
  final String rawName;
  final String genericName;
  final String? drugClass;
  final String tag; // NEW | EXISTING | UNRESOLVED

  const ResolvedDrug({
    required this.rawName,
    required this.genericName,
    this.drugClass,
    required this.tag,
  });

  factory ResolvedDrug.fromJson(Map<String, dynamic> json) => ResolvedDrug(
        rawName: json['raw_name'] as String? ?? '',
        genericName: json['generic_name'] as String? ?? '',
        drugClass: json['drug_class'] as String?,
        tag: json['tag'] as String? ?? 'UNRESOLVED',
      );
}

class InteractionFinding {
  final String drugA;
  final String drugB;
  final String severity; // HIGH | MODERATE | LOW | INFO | NONE
  final String mechanism;
  final String source; // current_visit | cross_visit

  const InteractionFinding({
    required this.drugA,
    required this.drugB,
    required this.severity,
    required this.mechanism,
    this.source = 'current_visit',
  });

  factory InteractionFinding.fromJson(Map<String, dynamic> json) =>
      InteractionFinding(
        drugA: json['drug_a'] as String? ?? '',
        drugB: json['drug_b'] as String? ?? '',
        severity: json['severity'] as String? ?? 'NONE',
        mechanism: json['mechanism'] as String? ?? '',
        source: json['source'] as String? ?? 'current_visit',
      );
}

class EvalScores {
  final int? safetyScore;
  final int? clarityScore;

  const EvalScores({this.safetyScore, this.clarityScore});

  factory EvalScores.fromJson(Map<String, dynamic> json) => EvalScores(
        safetyScore: json['safety_score'] as int?,
        clarityScore: json['clarity_score'] as int?,
      );
}

class PrescriptionResult {
  final String sessionId;
  final List<ResolvedDrug> resolvedDrugs;
  final List<InteractionFinding> interactions;
  final String overallSeverity; // HIGH | MODERATE | LOW | INFO | NONE
  final String explanationEn;
  final String explanationLocalised;
  final String audioUrl;
  final List<String> doctorQuestions;
  final String disclaimer;
  final EvalScores? evalScores;

  const PrescriptionResult({
    required this.sessionId,
    required this.resolvedDrugs,
    required this.interactions,
    required this.overallSeverity,
    required this.explanationEn,
    required this.explanationLocalised,
    required this.audioUrl,
    required this.doctorQuestions,
    required this.disclaimer,
    this.evalScores,
  });

  factory PrescriptionResult.fromJson(Map<String, dynamic> json) =>
      PrescriptionResult(
        sessionId: json['session_id'] as String? ?? '',
        resolvedDrugs: (json['resolved_drugs'] as List<dynamic>? ?? [])
            .map((e) => ResolvedDrug.fromJson(e as Map<String, dynamic>))
            .toList(),
        interactions: (json['interactions'] as List<dynamic>? ?? [])
            .map((e) => InteractionFinding.fromJson(e as Map<String, dynamic>))
            .toList(),
        overallSeverity: json['overall_severity'] as String? ?? 'NONE',
        explanationEn: json['explanation_en'] as String? ?? '',
        explanationLocalised:
            json['explanation_localised'] as String? ?? '',
        audioUrl: json['audio_url'] as String? ?? '',
        doctorQuestions: (json['doctor_questions'] as List<dynamic>? ?? [])
            .map((e) => e as String)
            .toList(),
        disclaimer: json['disclaimer'] as String? ?? '',
        evalScores: json['eval_scores'] != null
            ? EvalScores.fromJson(
                json['eval_scores'] as Map<String, dynamic>)
            : null,
      );
}
