// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Telugu (`te`).
class AppLocalizationsTe extends AppLocalizations {
  AppLocalizationsTe([String locale = 'te']) : super(locale);

  @override
  String get appTitle => 'మందు సహచరుడు';

  @override
  String get appSubtitle => 'AI ఆధారిత ప్రిస్క్రిప్షన్ విశ్లేషణ';

  @override
  String get appLanguage => 'యాప్ భాష';

  @override
  String get continueDevMode => 'డెవ్ మోడ్‌లో కొనసాగించండి';

  @override
  String get devModeHint => 'ENVIRONMENT=local — Firebase ప్రామాణీకరణ బైపాస్';

  @override
  String get orSignInFirebase => 'లేదా Firebaseతో సైన్ ఇన్ చేయండి';

  @override
  String get signIn => 'సైన్ ఇన్';

  @override
  String get createAccount => 'ఖాతా సృష్టించండి';

  @override
  String get email => 'ఇమెయిల్';

  @override
  String get emailInvalid => 'చెల్లుబాటు అయ్యే ఇమెయిల్ చిరునామా నమోదు చేయండి';

  @override
  String get password => 'పాస్‌వర్డ్';

  @override
  String get confirmPassword => 'పాస్‌వర్డ్‌ను నిర్ధారించండి';

  @override
  String get passwordMinLength => 'కనీసం 6 అక్షరాలు ఉపయోగించండి';

  @override
  String get passwordsDoNotMatch => 'పాస్‌వర్డ్‌లు సరిపోలలేదు';

  @override
  String get passwordStrengthHint =>
      '8+ అక్షరాలు, పెద్ద/చిన్న అక్షరాలు, సంఖ్యలు మరియు చిహ్నాలు';

  @override
  String get passwordStrengthWeak => 'బలహీనం';

  @override
  String get passwordStrengthFair => 'సరాసరి';

  @override
  String get passwordStrengthGood => 'మంచిది';

  @override
  String get passwordStrengthStrong => 'బలమైనది';

  @override
  String get showPassword => 'పాస్‌వర్డ్ చూపించు';

  @override
  String get hidePassword => 'పాస్‌వర్డ్ దాచు';

  @override
  String get createAccountDisclaimer =>
      'ఈ యాప్ సమాచారం కోసం మాత్రమే. ఎప్పుడూ మీ వైద్యుడు లేదా ఫార్మసిస్ట్‌తో చర్చించండి.';

  @override
  String get errorInvalidEmail => 'చెల్లని ఇమెయిల్ చిరునామా.';

  @override
  String get errorWrongPassword => 'తప్పు ఇమెయిల్ లేదా పాస్‌వర్డ్.';

  @override
  String get errorUserNotFound => 'ఈ ఇమెయిల్‌కు ఖాతా కనుగొనబడలేదు.';

  @override
  String get errorEmailInUse =>
      'ఈ ఇమెయిల్‌కు ఇప్పటికే ఖాతా ఉంది. సైన్ ఇన్ చేయండి.';

  @override
  String get errorWeakPassword => 'పాస్‌వర్డ్ కనీసం 6 అక్షరాలు ఉండాలి.';

  @override
  String get errorGeneric => 'ఏదో తప్పు జరిగింది. దయచేసి మళ్లీ ప్రయత్నించండి.';

  @override
  String hello(String name) {
    return 'నమస్కారం, $name';
  }

  @override
  String get readyToAnalyse =>
      'మీ ప్రిస్క్రిప్షన్‌ను విశ్లేషించడానికి సిద్ధంగా ఉన్నారా?';

  @override
  String get audioLanguage => 'ఆడియో భాష';

  @override
  String get disclaimerHome =>
      'ఈ యాప్ సమాచారం కోసం మాత్రమే. మీ మందుల గురించి ఎప్పుడూ వైద్యుడు లేదా ఫార్మసిస్ట్‌తో చర్చించండి.';

  @override
  String get analysePrescription => 'ప్రిస్క్రిప్షన్‌ను విశ్లేషించండి';

  @override
  String get signOut => 'సైన్ అవుట్';

  @override
  String get scanPrescription => 'ప్రిస్క్రిప్షన్‌ను స్కాన్ చేయండి';

  @override
  String get tapGallery => 'గ్యాలరీ నుండి ఎంచుకోవడానికి ట్యాప్ చేయండి';

  @override
  String get camera => 'కెమెరా';

  @override
  String get gallery => 'గ్యాలరీ';

  @override
  String get retakePhoto => 'ఫోటో మళ్లీ తీయండి';

  @override
  String get stepReading => 'ప్రిస్క్రిప్షన్ చదవబడుతోంది...';

  @override
  String get stepChecking => 'పరస్పర చర్యలు తనిఖీ చేయబడుతున్నాయి...';

  @override
  String get stepGenerating => 'వివరణ సృష్టించబడుతోంది...';

  @override
  String get statusPending => 'విశ్లేషణ కోసం వరుసలో...';

  @override
  String get statusProcessing => 'ప్రిస్క్రిప్షన్ విశ్లేషించబడుతోంది...';

  @override
  String get statusDone => 'మీ ఫలితాలు సిద్ధం చేయబడుతున్నాయి...';

  @override
  String get loadingHint =>
      'దీనికి సుమారు 20–40 సెకన్లు పడుతుంది.\nదయచేసి ఈ స్క్రీన్‌ను తెరిచి ఉంచండి.';

  @override
  String accessError(String error) {
    return 'కెమెరా లేదా గ్యాలరీని యాక్సెస్ చేయలేకపోయాము: $error';
  }

  @override
  String get prescriptionAnalysis => 'ప్రిస్క్రిప్షన్ విశ్లేషణ';

  @override
  String medicationsFound(int count) {
    return 'మందులు కనుగొనబడ్డాయి ($count)';
  }

  @override
  String interactions(int count) {
    return 'పరస్పర చర్యలు ($count)';
  }

  @override
  String get summary => 'సారాంశం';

  @override
  String get audioExplanation => 'ఆడియో వివరణ';

  @override
  String get playing => 'ప్లే అవుతోంది...';

  @override
  String get tapToPlay => 'ఆడియో వినడానికి ట్యాప్ చేయండి';

  @override
  String get doctorQuestions => 'మీ వైద్యుడికి అడగాల్సిన ప్రశ్నలు';

  @override
  String get backToHome => 'హోమ్‌కు తిరిగి';

  @override
  String get severityHigh => 'అధిక తీవ్రత — వెంటనే వైద్యుడిని సంప్రదించండి';

  @override
  String get severityModerate => 'మధ్యస్థ తీవ్రత — వైద్యుడితో చర్చించండి';

  @override
  String get severityLow => 'తక్కువ తీవ్రత — సమాచారం';

  @override
  String get severityInfo => 'పరస్పర చర్యలు కనుగొనబడలేదు';

  @override
  String get severityNone => 'ఆందోళనలు గుర్తించబడలేదు';

  @override
  String get couldNotResolve => 'గుర్తించలేకపోయాము';

  @override
  String get crossVisitDetected => 'మీ మందుల చరిత్ర నుండి గుర్తించబడింది';

  @override
  String get tagNew => 'కొత్త';

  @override
  String get tagExisting => 'ఇప్పటికే';

  @override
  String get tagUnresolved => 'దొరకలేదు';

  @override
  String get sevChipHigh => 'ఎక్కువ';

  @override
  String get sevChipModerate => 'మధ్యస్థ';

  @override
  String get sevChipLow => 'తక్కువ';

  @override
  String get sevChipInfo => 'సమాచారం';

  @override
  String get sevChipNone => 'సరే';

  @override
  String get sevWordHigh => 'ఎక్కువ';

  @override
  String get sevWordModerate => 'మధ్యస్థ';

  @override
  String get sevWordLow => 'తక్కువ';

  @override
  String mechanismDataset(String severityWord, String a, String b) {
    return '$a మరియు $b కలిపి తీసుకుంటే $severityWord ప్రభావం ఉండవచ్చు. మీ డాక్టర్ లేదా ఫార్మసిస్ట్‌తో మాట్లాడండి.';
  }

  @override
  String get shownInEnglishNote => '(ఆంగ్లంలో చూపబడింది)';

  @override
  String get langEnglish => 'ఆంగ్లం';

  @override
  String get langHindi => 'హిందీ';

  @override
  String get langTamil => 'తమిళం';

  @override
  String get langTelugu => 'తెలుగు';

  @override
  String get langBengali => 'బెంగాలీ';

  @override
  String get pastPrescriptionsButton => 'గత ప్రిస్క్రిప్షన్‌లు';

  @override
  String get historyTitle => 'గత ప్రిస్క్రిప్షన్‌లు';

  @override
  String get historyEmpty =>
      'ఇంకా గత ప్రిస్క్రిప్షన్‌లు లేవు. ఒకదాన్ని విశ్లేషించి ఇక్కడ చూడండి.';

  @override
  String get historyLoadError =>
      'మీ గత ప్రిస్క్రిప్షన్‌లను లోడ్ చేయలేకపోయాము. మళ్లీ ప్రయత్నించడానికి కిందికి లాగండి.';

  @override
  String get historyProcessing => 'విశ్లేషిస్తోంది...';

  @override
  String get historyFailed => 'విశ్లేషణ విఫలమైంది';

  @override
  String get historyGate1Chip => 'కొత్త ఫోటో అవసరం';

  @override
  String get historyGate1Title => 'ఈ చిత్రాన్ని చదవలేకపోయాము';

  @override
  String get historyImageUnavailable => 'చిత్రం అందుబాటులో లేదు';

  @override
  String get prescriptionImageLabel => 'అసలు ప్రిస్క్రిప్షన్';

  @override
  String get openAnalysisInProgress => 'జరుగుతున్న విశ్లేషణను తెరవండి';

  @override
  String get analysisNotReady => 'మీ విశ్లేషణ ఇంకా సిద్ధమవుతోంది.';
}
