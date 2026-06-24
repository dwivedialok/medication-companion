// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Tamil (`ta`).
class AppLocalizationsTa extends AppLocalizations {
  AppLocalizationsTa([String locale = 'ta']) : super(locale);

  @override
  String get appTitle => 'மருந்து துணை';

  @override
  String get appSubtitle => 'ஏஐ அடிப்படையிலான மருந்துச் சீட்டு பகுப்பாய்வு';

  @override
  String get appLanguage => 'பயன்பாட்டு மொழி';

  @override
  String get continueDevMode => 'டெவ் பயன்முறையில் தொடரவும்';

  @override
  String get devModeHint =>
      'ENVIRONMENT=local — Firebase அங்கீகாரம் தவிர்க்கப்பட்டது';

  @override
  String get orSignInFirebase => 'அல்லது Firebase மூலம் உள்நுழையவும்';

  @override
  String get signIn => 'உள்நுழை';

  @override
  String get createAccount => 'கணக்கு உருவாக்கு';

  @override
  String get email => 'மின்னஞ்சல்';

  @override
  String get emailInvalid => 'சரியான மின்னஞ்சல் முகவரியை உள்ளிடவும்';

  @override
  String get password => 'கடவுச்சொல்';

  @override
  String get confirmPassword => 'கடவுச்சொல்லை உறுதிப்படுத்து';

  @override
  String get passwordMinLength => 'குறைந்தது 6 எழுத்துகள் பயன்படுத்தவும்';

  @override
  String get passwordsDoNotMatch => 'கடவுச்சொற்கள் பொருந்தவில்லை';

  @override
  String get passwordStrengthHint =>
      '8+ எழுத்துகள், பெரிய/சிறிய எழுத்துகள், எண்கள் மற்றும் குறியீடுகள்';

  @override
  String get passwordStrengthWeak => 'பலவீனம்';

  @override
  String get passwordStrengthFair => 'சராசரி';

  @override
  String get passwordStrengthGood => 'நல்லது';

  @override
  String get passwordStrengthStrong => 'வலுவானது';

  @override
  String get showPassword => 'கடவுச்சொல்லை காட்டு';

  @override
  String get hidePassword => 'கடவுச்சொல்லை மறை';

  @override
  String get createAccountDisclaimer =>
      'இந்த பயன்பாடு தகவலுக்காக மட்டுமே. எப்போதும் மருத்துவரிடம் அல்லது மருந்தாளரிடம் கலந்தாலோசிக்கவும்.';

  @override
  String get errorInvalidEmail => 'தவறான மின்னஞ்சல் முகவரி.';

  @override
  String get errorWrongPassword => 'தவறான மின்னஞ்சல் அல்லது கடவுச்சொல்.';

  @override
  String get errorUserNotFound => 'இந்த மின்னஞ்சலுக்கு கணக்கு இல்லை.';

  @override
  String get errorEmailInUse =>
      'இந்த மின்னஞ்சலுக்கு ஏற்கனவே கணக்கு உள்ளது. உள்நுழைய முயற்சிக்கவும்.';

  @override
  String get errorWeakPassword =>
      'கடவுச்சொல் குறைந்தது 6 எழுத்துகள் இருக்க வேண்டும்.';

  @override
  String get errorGeneric => 'ஏதோ தவறு ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.';

  @override
  String hello(String name) {
    return 'வணக்கம், $name';
  }

  @override
  String get readyToAnalyse =>
      'உங்கள் மருந்துச் சீட்டை பகுப்பாய்வு செய்ய தயாரா?';

  @override
  String get audioLanguage => 'ஆடியோ மொழி';

  @override
  String get disclaimerHome =>
      'இந்த பயன்பாடு தகவலுக்காக மட்டுமே. உங்கள் மருந்துகளை எப்போதும் மருத்துவர் அல்லது மருந்தாளரிடம் கலந்தாலோசிக்கவும்.';

  @override
  String get analysePrescription => 'மருந்துச் சீட்டை பகுப்பாய்வு செய்';

  @override
  String get signOut => 'வெளியேறு';

  @override
  String get scanPrescription => 'மருந்துச் சீட்டை ஸ்கேன் செய்';

  @override
  String get tapGallery => 'கேலரியிலிருந்து தேர்ந்தெடுக்க தட்டவும்';

  @override
  String get camera => 'கேமரா';

  @override
  String get gallery => 'கேலரி';

  @override
  String get retakePhoto => 'மீண்டும் படம் எடு';

  @override
  String get stepReading => 'மருந்துச் சீட்டு படிக்கப்படுகிறது...';

  @override
  String get stepChecking => 'தொடர்புகள் சரிபார்க்கப்படுகின்றன...';

  @override
  String get stepGenerating => 'விளக்கம் உருவாக்கப்படுகிறது...';

  @override
  String get statusPending => 'பகுப்பாய்வுக்காக வரிசையில்...';

  @override
  String get statusProcessing =>
      'மருந்துச் சீட்டு பகுப்பாய்வு செய்யப்படுகிறது...';

  @override
  String get statusDone => 'உங்கள் முடிவுகள் தயாராகின்றன...';

  @override
  String get loadingHint =>
      'இதற்கு சுமார் 20–40 வினாடிகள் ஆகும்.\nஇந்த திரையை திறந்து வைத்திருக்கவும்.';

  @override
  String accessError(String error) {
    return 'கேமரா அல்லது கேலரியை அணுக முடியவில்லை: $error';
  }

  @override
  String get prescriptionAnalysis => 'மருந்துச் சீட்டு பகுப்பாய்வு';

  @override
  String medicationsFound(int count) {
    return 'மருந்துகள் கண்டறியப்பட்டன ($count)';
  }

  @override
  String interactions(int count) {
    return 'தொடர்புகள் ($count)';
  }

  @override
  String get summary => 'சுருக்கம்';

  @override
  String get audioExplanation => 'ஆடியோ விளக்கம்';

  @override
  String get playing => 'இயங்குகிறது...';

  @override
  String get tapToPlay => 'ஆடியோ கேட்க தட்டவும்';

  @override
  String get doctorQuestions => 'மருத்துவரிடம் கேட்க வேண்டிய கேள்விகள்';

  @override
  String get backToHome => 'முகப்புக்கு திரும்பு';

  @override
  String get severityHigh => 'உயர் தீவிரம் — உடனடியாக மருத்துவரை அணுகவும்';

  @override
  String get severityModerate =>
      'மிதமான தீவிரம் — மருத்துவரிடம் கலந்தாலோசிக்கவும்';

  @override
  String get severityLow => 'குறைந்த தீவிரம் — தகவல்';

  @override
  String get severityInfo => 'தொடர்புகள் எதுவும் இல்லை';

  @override
  String get severityNone => 'கவலைகள் எதுவும் கண்டறியப்படவில்லை';

  @override
  String get couldNotResolve => 'அடையாளம் காண முடியவில்லை';

  @override
  String get crossVisitDetected =>
      'உங்கள் மருந்து வரலாற்றிலிருந்து கண்டறியப்பட்டது';

  @override
  String get tagNew => 'புதிய';

  @override
  String get tagExisting => 'ஏற்கனவே';

  @override
  String get tagUnresolved => 'கிடைக்கவில்லை';

  @override
  String get sevChipHigh => 'அதிக';

  @override
  String get sevChipModerate => 'மிதம்';

  @override
  String get sevChipLow => 'குறைவு';

  @override
  String get sevChipInfo => 'தகவல்';

  @override
  String get sevChipNone => 'சரி';

  @override
  String get sevWordHigh => 'அதிக';

  @override
  String get sevWordModerate => 'மிதமான';

  @override
  String get sevWordLow => 'குறைந்த';

  @override
  String mechanismDataset(String severityWord, String a, String b) {
    return '$a மற்றும் $b ஒன்றாக எடுத்துக்கொண்டால் $severityWord விளைவு ஏற்படலாம். உங்கள் டாக்டர் அல்லது மருந்தாளரிடம் பேசவும்.';
  }

  @override
  String get shownInEnglishNote => '(ஆங்கிலத்தில் காட்டப்படுகிறது)';

  @override
  String get langEnglish => 'ஆங்கிலம்';

  @override
  String get langHindi => 'ஹிந்தி';

  @override
  String get langTamil => 'தமிழ்';

  @override
  String get langTelugu => 'தெலுங்கு';

  @override
  String get langBengali => 'வங்காளம்';
}
