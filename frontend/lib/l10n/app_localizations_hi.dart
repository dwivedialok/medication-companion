// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Hindi (`hi`).
class AppLocalizationsHi extends AppLocalizations {
  AppLocalizationsHi([String locale = 'hi']) : super(locale);

  @override
  String get appTitle => 'दवा दोस्त';

  @override
  String get appSubtitle => 'AI से दवाई पर्चे की जाँच';

  @override
  String get appLanguage => 'ऐप की भाषा';

  @override
  String get continueDevMode => 'Dev मोड में आगे बढ़ें';

  @override
  String get devModeHint => 'ENVIRONMENT=local — Firebase लॉगिन बंद है';

  @override
  String get orSignInFirebase => 'या Firebase से लॉगिन करें';

  @override
  String get signIn => 'लॉगिन';

  @override
  String get createAccount => 'नया अकाउंट बनाएं';

  @override
  String get email => 'ईमेल';

  @override
  String get emailInvalid => 'सही ईमेल डालें';

  @override
  String get password => 'पासवर्ड';

  @override
  String get confirmPassword => 'पासवर्ड दोबारा डालें';

  @override
  String get passwordMinLength => 'कम से कम 6 अक्षर का पासवर्ड डालें';

  @override
  String get passwordsDoNotMatch => 'दोनों पासवर्ड एक जैसे नहीं हैं';

  @override
  String get passwordStrengthHint =>
      'मज़बूत पासवर्ड के लिए 8+ अक्षर, बड़े/छोटे letters, नंबर और symbol डालें';

  @override
  String get passwordStrengthWeak => 'कमज़ोर';

  @override
  String get passwordStrengthFair => 'ठीक-ठाक';

  @override
  String get passwordStrengthGood => 'अच्छा';

  @override
  String get passwordStrengthStrong => 'मज़बूत';

  @override
  String get showPassword => 'पासवर्ड दिखाएं';

  @override
  String get hidePassword => 'पासवर्ड छिपाएं';

  @override
  String get createAccountDisclaimer =>
      'यह ऐप सिर्फ़ जानकारी के लिए है। अपनी दवाओं के बारे में हमेशा अपने डॉक्टर या केमिस्ट से बात करें।';

  @override
  String get errorInvalidEmail => 'गलत ईमेल।';

  @override
  String get errorWrongPassword => 'ईमेल या पासवर्ड गलत है।';

  @override
  String get errorUserNotFound => 'इस ईमेल का कोई अकाउंट नहीं मिला।';

  @override
  String get errorEmailInUse => 'इस ईमेल से अकाउंट पहले से है। लॉगिन करें।';

  @override
  String get errorWeakPassword => 'पासवर्ड कम से कम 6 अक्षर का होना चाहिए।';

  @override
  String get errorGeneric => 'कुछ गड़बड़ हो गई। फिर से कोशिश करें।';

  @override
  String hello(String name) {
    return 'नमस्ते, $name';
  }

  @override
  String get readyToAnalyse => 'अपनी दवाई पर्चे की जाँच करें?';

  @override
  String get audioLanguage => 'आवाज़ की भाषा';

  @override
  String get disclaimerHome =>
      'यह ऐप सिर्फ़ जानकारी के लिए है। अपनी दवाओं के बारे में हमेशा डॉक्टर या केमिस्ट से बात करें।';

  @override
  String get analysePrescription => 'दवाई पर्चे की जाँच करें';

  @override
  String get signOut => 'लॉगआउट';

  @override
  String get scanPrescription => 'दवाई पर्चे स्कैन करें';

  @override
  String get tapGallery => 'गैलरी से फोटो चुनने के लिए यहाँ टैप करें';

  @override
  String get camera => 'कैमरा';

  @override
  String get gallery => 'गैलरी';

  @override
  String get retakePhoto => 'नई फोटो लें';

  @override
  String get stepReading => 'दवाई पर्चा पढ़ा जा रहा है...';

  @override
  String get stepChecking => 'दवाओं की आपस में जाँच हो रही है...';

  @override
  String get stepGenerating => 'नतीजे तैयार हो रहे हैं...';

  @override
  String get statusPending => 'जाँच की कतार में...';

  @override
  String get statusProcessing => 'दवाई पर्चे की जाँच हो रही है...';

  @override
  String get statusDone => 'नतीजे तैयार हो रहे हैं...';

  @override
  String get loadingHint =>
      'इसमें 20–40 सेकंड लगते हैं।\nयह स्क्रीन खुली रखें।';

  @override
  String accessError(String error) {
    return 'कैमरा या गैलरी नहीं खुल पाई: $error';
  }

  @override
  String get prescriptionAnalysis => 'दवाई पर्चे की जाँच';

  @override
  String medicationsFound(int count) {
    return 'मिली दवाएँ ($count)';
  }

  @override
  String interactions(int count) {
    return 'दवाओं का असर ($count)';
  }

  @override
  String get summary => 'मुख्य बातें';

  @override
  String get audioExplanation => 'सुनकर समझें';

  @override
  String get playing => 'चल रहा है...';

  @override
  String get tapToPlay => 'सुनने के लिए टैप करें';

  @override
  String get doctorQuestions => 'डॉक्टर से पूछने के सवाल';

  @override
  String get backToHome => 'वापस होम पर';

  @override
  String get severityHigh => 'बहुत ज़रूरी — तुरंत डॉक्टर से मिलें';

  @override
  String get severityModerate => 'थोड़ा ज़रूरी — डॉक्टर से बात करें';

  @override
  String get severityLow => 'मामूली — सिर्फ़ जानकारी के लिए';

  @override
  String get severityInfo => 'कोई दिक्कत नहीं मिली';

  @override
  String get severityNone => 'कोई परेशानी नहीं';

  @override
  String get couldNotResolve => 'पहचान नहीं हो पाई';

  @override
  String get crossVisitDetected => 'आपकी पुरानी दवाओं से मिला';

  @override
  String get tagNew => 'नई दवा';

  @override
  String get tagExisting => 'चल रही दवा';

  @override
  String get tagUnresolved => 'पहचान नहीं हुई';

  @override
  String get sevChipHigh => 'गंभीर';

  @override
  String get sevChipModerate => 'मध्यम';

  @override
  String get sevChipLow => 'हल्का';

  @override
  String get sevChipInfo => 'जानकारी';

  @override
  String get sevChipNone => 'ठीक';

  @override
  String get sevWordHigh => 'गंभीर';

  @override
  String get sevWordModerate => 'मध्यम';

  @override
  String get sevWordLow => 'हल्का';

  @override
  String mechanismDataset(String severityWord, String a, String b) {
    return '$a और $b को एक साथ लेने पर $severityWord दुष्प्रभाव (साइड-इफेक्ट) हो सकते हैं। कृपया अपने डॉक्टर या केमिस्ट से सलाह लें।';
  }

  @override
  String get shownInEnglishNote => '(अंग्रेज़ी में दिखाया गया है)';

  @override
  String get langEnglish => 'English';

  @override
  String get langHindi => 'हिंदी';

  @override
  String get langTamil => 'தமிழ்';

  @override
  String get langTelugu => 'తెలుగు';

  @override
  String get langBengali => 'বাংলা';

  @override
  String get pastPrescriptionsButton => 'पुरानी जाँच';

  @override
  String get historyTitle => 'पुरानी जाँच';

  @override
  String get historyEmpty =>
      'अभी तक कोई पुरानी जाँच नहीं है। नई दवाई पर्चे की जाँच करें।';

  @override
  String get historyLoadError =>
      'पुरानी जाँच लोड नहीं हो पाई। नीचे खींचकर फिर कोशिश करें।';

  @override
  String get historyProcessing => 'जाँच चल रही है...';

  @override
  String get historyFailed => 'जाँच पूरी नहीं हो पाई';

  @override
  String get historyGate1Chip => 'नई फोटो चाहिए';

  @override
  String get historyGate1Title => 'यह फोटो पढ़ी नहीं जा सकी';

  @override
  String get historyImageUnavailable => 'फोटो उपलब्ध नहीं है';

  @override
  String get prescriptionImageLabel => 'मूल दवाई पर्चा';

  @override
  String get openAnalysisInProgress => 'चल रही जाँच खोलें';

  @override
  String get analysisNotReady => 'आपकी जाँच अभी तैयार हो रही है।';
}
