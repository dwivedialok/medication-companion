// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Medication Companion';

  @override
  String get appSubtitle => 'AI-powered prescription analysis';

  @override
  String get appLanguage => 'App language';

  @override
  String get continueDevMode => 'Continue in dev mode';

  @override
  String get devModeHint => 'ENVIRONMENT=local — Firebase auth bypassed';

  @override
  String get orSignInFirebase => 'or sign in with Firebase';

  @override
  String get signIn => 'Sign in';

  @override
  String get createAccount => 'Create account';

  @override
  String get email => 'Email';

  @override
  String get emailInvalid => 'Enter a valid email address';

  @override
  String get password => 'Password';

  @override
  String get confirmPassword => 'Confirm password';

  @override
  String get passwordMinLength => 'Use at least 6 characters';

  @override
  String get passwordsDoNotMatch => 'Passwords do not match';

  @override
  String get passwordStrengthHint =>
      'Use 8+ characters with upper & lower case, numbers, and symbols';

  @override
  String get passwordStrengthWeak => 'Weak';

  @override
  String get passwordStrengthFair => 'Fair';

  @override
  String get passwordStrengthGood => 'Good';

  @override
  String get passwordStrengthStrong => 'Strong';

  @override
  String get showPassword => 'Show password';

  @override
  String get hidePassword => 'Hide password';

  @override
  String get createAccountDisclaimer =>
      'This app provides information only. Always discuss medications with your doctor or pharmacist.';

  @override
  String get errorInvalidEmail => 'Invalid email address.';

  @override
  String get errorWrongPassword => 'Incorrect email or password.';

  @override
  String get errorUserNotFound => 'No account found for this email.';

  @override
  String get errorEmailInUse =>
      'An account already exists for this email. Try signing in.';

  @override
  String get errorWeakPassword => 'Password must be at least 6 characters.';

  @override
  String get errorGeneric => 'Something went wrong. Please try again.';

  @override
  String hello(String name) {
    return 'Hello, $name';
  }

  @override
  String get readyToAnalyse => 'Ready to analyse your prescription?';

  @override
  String get audioLanguage => 'Audio language';

  @override
  String get disclaimerHome =>
      'This app is for information only. Always discuss your medications with your doctor or pharmacist.';

  @override
  String get analysePrescription => 'Analyse prescription';

  @override
  String get signOut => 'Sign out';

  @override
  String get scanPrescription => 'Scan prescription';

  @override
  String get tapGallery => 'Tap to select from gallery';

  @override
  String get camera => 'Camera';

  @override
  String get gallery => 'Gallery';

  @override
  String get retakePhoto => 'Retake photo';

  @override
  String get stepReading => 'Reading prescription...';

  @override
  String get stepChecking => 'Checking interactions...';

  @override
  String get stepGenerating => 'Generating explanation...';

  @override
  String get statusPending => 'Queued for analysis...';

  @override
  String get statusProcessing => 'Analysing prescription...';

  @override
  String get statusDone => 'Preparing your results...';

  @override
  String get loadingHint =>
      'This takes about 20–40 seconds.\nPlease keep this screen open.';

  @override
  String accessError(String error) {
    return 'Could not access camera or gallery: $error';
  }

  @override
  String get prescriptionAnalysis => 'Prescription Analysis';

  @override
  String medicationsFound(int count) {
    return 'Medications found ($count)';
  }

  @override
  String interactions(int count) {
    return 'Interactions ($count)';
  }

  @override
  String get summary => 'Summary';

  @override
  String get audioExplanation => 'Audio explanation';

  @override
  String get playing => 'Playing...';

  @override
  String get tapToPlay => 'Tap to play audio explanation';

  @override
  String get doctorQuestions => 'Questions for your doctor';

  @override
  String get backToHome => 'Back to home';

  @override
  String get severityHigh => 'High severity — review urgently with your doctor';

  @override
  String get severityModerate => 'Moderate severity — discuss with your doctor';

  @override
  String get severityLow => 'Low severity — informational';

  @override
  String get severityInfo => 'No interactions found';

  @override
  String get severityNone => 'No concerns identified';

  @override
  String get couldNotResolve => 'Could not be resolved';

  @override
  String get crossVisitDetected => 'Detected from your medication history';

  @override
  String get tagNew => 'NEW';

  @override
  String get tagExisting => 'EXISTING';

  @override
  String get tagUnresolved => 'UNRESOLVED';

  @override
  String get sevChipHigh => 'HIGH';

  @override
  String get sevChipModerate => 'MODERATE';

  @override
  String get sevChipLow => 'LOW';

  @override
  String get sevChipInfo => 'INFO';

  @override
  String get sevChipNone => 'NONE';

  @override
  String get sevWordHigh => 'high';

  @override
  String get sevWordModerate => 'moderate';

  @override
  String get sevWordLow => 'low';

  @override
  String mechanismDataset(String severityWord, String a, String b) {
    return 'Dataset records a $severityWord interaction between $a and $b. Please discuss this with your doctor or pharmacist.';
  }

  @override
  String get shownInEnglishNote => '(shown in English)';

  @override
  String get langEnglish => 'English';

  @override
  String get langHindi => 'Hindi';

  @override
  String get langTamil => 'Tamil';

  @override
  String get langTelugu => 'Telugu';

  @override
  String get langBengali => 'Bengali';
}
