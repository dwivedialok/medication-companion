// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Bengali Bangla (`bn`).
class AppLocalizationsBn extends AppLocalizations {
  AppLocalizationsBn([String locale = 'bn']) : super(locale);

  @override
  String get appTitle => 'ওষুধ সঙ্গী';

  @override
  String get appSubtitle => 'এআই-চালিত প্রেসক্রিপশন বিশ্লেষণ';

  @override
  String get appLanguage => 'অ্যাপ ভাষা';

  @override
  String get continueDevMode => 'ডেভ মোডে চালিয়ে যান';

  @override
  String get devModeHint => 'ENVIRONMENT=local — Firebase প্রমাণীকরণ বাইপাস';

  @override
  String get orSignInFirebase => 'অথবা Firebase দিয়ে সাইন ইন করুন';

  @override
  String get signIn => 'সাইন ইন';

  @override
  String get createAccount => 'অ্যাকাউন্ট তৈরি করুন';

  @override
  String get email => 'ইমেইল';

  @override
  String get emailInvalid => 'বৈধ ইমেইল ঠিকানা লিখুন';

  @override
  String get password => 'পাসওয়ার্ড';

  @override
  String get confirmPassword => 'পাসওয়ার্ড নিশ্চিত করুন';

  @override
  String get passwordMinLength => 'কমপক্ষে ৬ অক্ষর ব্যবহার করুন';

  @override
  String get passwordsDoNotMatch => 'পাসওয়ার্ড মিলছে না';

  @override
  String get passwordStrengthHint =>
      '৮+ অক্ষর, বড়/ছোট হাতের অক্ষর, সংখ্যা ও চিহ্ন ব্যবহার করুন';

  @override
  String get passwordStrengthWeak => 'দুর্বল';

  @override
  String get passwordStrengthFair => 'মোটামুটি';

  @override
  String get passwordStrengthGood => 'ভালো';

  @override
  String get passwordStrengthStrong => 'শক্তিশালী';

  @override
  String get showPassword => 'পাসওয়ার্ড দেখান';

  @override
  String get hidePassword => 'পাসওয়ার্ড লুকান';

  @override
  String get createAccountDisclaimer =>
      'এই অ্যাপ শুধু তথ্যের জন্য। সবসময় আপনার ডাক্তার বা ফার্মাসিস্টের সাথে আলোচনা করুন।';

  @override
  String get errorInvalidEmail => 'অবৈধ ইমেইল ঠিকানা।';

  @override
  String get errorWrongPassword => 'ভুল ইমেইল বা পাসওয়ার্ড।';

  @override
  String get errorUserNotFound => 'এই ইমেইলের জন্য কোনো অ্যাকাউন্ট নেই।';

  @override
  String get errorEmailInUse => 'এই ইমেইলের জন্য অ্যাকাউন্ট আছে। সাইন ইন করুন।';

  @override
  String get errorWeakPassword => 'পাসওয়ার্ড কমপক্ষে ৬ অক্ষরের হতে হবে।';

  @override
  String get errorGeneric => 'কিছু ভুল হয়েছে। আবার চেষ্টা করুন।';

  @override
  String hello(String name) {
    return 'নমস্কার, $name';
  }

  @override
  String get readyToAnalyse => 'আপনার প্রেসক্রিপশন বিশ্লেষণ করতে প্রস্তুত?';

  @override
  String get audioLanguage => 'অডিও ভাষা';

  @override
  String get disclaimerHome =>
      'এই অ্যাপ শুধু তথ্যের জন্য। সবসময় আপনার ওষুধ নিয়ে ডাক্তার বা ফার্মাসিস্টের সাথে আলোচনা করুন।';

  @override
  String get analysePrescription => 'প্রেসক্রিপশন বিশ্লেষণ করুন';

  @override
  String get signOut => 'সাইন আউট';

  @override
  String get scanPrescription => 'প্রেসক্রিপশন স্ক্যান করুন';

  @override
  String get tapGallery => 'গ্যালারি থেকে বেছে নিতে ট্যাপ করুন';

  @override
  String get camera => 'ক্যামেরা';

  @override
  String get gallery => 'গ্যালারি';

  @override
  String get retakePhoto => 'আবার ছবি তুলুন';

  @override
  String get stepReading => 'প্রেসক্রিপশন পড়া হচ্ছে...';

  @override
  String get stepChecking => 'ইন্টারঅ্যাকশন পরীক্ষা করা হচ্ছে...';

  @override
  String get stepGenerating => 'ব্যাখ্যা তৈরি করা হচ্ছে...';

  @override
  String get statusPending => 'বিশ্লেষণের জন্য সারিতে...';

  @override
  String get statusProcessing => 'প্রেসক্রিপশন বিশ্লেষণ করা হচ্ছে...';

  @override
  String get statusDone => 'আপনার ফলাফল প্রস্তুত করা হচ্ছে...';

  @override
  String get loadingHint =>
      'এতে প্রায় ২০–৪০ সেকেন্ড লাগে।\nএই স্ক্রিন খোলা রাখুন।';

  @override
  String accessError(String error) {
    return 'ক্যামেরা বা গ্যালেরি অ্যাক্সেস করা যায়নি: $error';
  }

  @override
  String get prescriptionAnalysis => 'প্রেসক্রিপশন বিশ্লেষণ';

  @override
  String medicationsFound(int count) {
    return 'ওষুধ পাওয়া গেছে ($count)';
  }

  @override
  String interactions(int count) {
    return 'ইন্টারঅ্যাকশন ($count)';
  }

  @override
  String get summary => 'সারসংক্ষেপ';

  @override
  String get audioExplanation => 'অডিও ব্যাখ্যা';

  @override
  String get playing => 'চলছে...';

  @override
  String get tapToPlay => 'অডিও শুনতে ট্যাপ করুন';

  @override
  String get doctorQuestions => 'ডাক্তারকে জিজ্ঞাসা করার প্রশ্ন';

  @override
  String get backToHome => 'হোমে ফিরে যান';

  @override
  String get severityHigh =>
      'উচ্চ তীব্রতা — জরুরি ভিত্তিতে ডাক্তারের সাথে যোগাযোগ করুন';

  @override
  String get severityModerate => 'মাঝারি তীব্রতা — ডাক্তারের সাথে আলোচনা করুন';

  @override
  String get severityLow => 'কম তীব্রতা — তথ্যমূলক';

  @override
  String get severityInfo => 'কোনো ইন্টারঅ্যাকশন পাওয়া যায়নি';

  @override
  String get severityNone => 'কোনো উদ্বেগ চিহ্নিত হয়নি';

  @override
  String get couldNotResolve => 'শনাক্ত করা যায়নি';

  @override
  String get crossVisitDetected => 'আপনার ওষুধের ইতিহাস থেকে শনাক্ত';

  @override
  String get tagNew => 'নতুন';

  @override
  String get tagExisting => 'আগের';

  @override
  String get tagUnresolved => 'পাওয়া যায়নি';

  @override
  String get sevChipHigh => 'বেশি';

  @override
  String get sevChipModerate => 'মাঝারি';

  @override
  String get sevChipLow => 'কম';

  @override
  String get sevChipInfo => 'তথ্য';

  @override
  String get sevChipNone => 'ঠিক আছে';

  @override
  String get sevWordHigh => 'বেশি';

  @override
  String get sevWordModerate => 'মাঝারি';

  @override
  String get sevWordLow => 'কম';

  @override
  String mechanismDataset(String severityWord, String a, String b) {
    return '$a এবং $b একসঙ্গে নিলে $severityWord প্রভাব হতে পারে। আপনার ডাক্তার বা ফার্মাসিস্টের সাথে কথা বলুন।';
  }

  @override
  String get shownInEnglishNote => '(ইংরেজিতে দেখানো হচ্ছে)';

  @override
  String get langEnglish => 'ইংরেজি';

  @override
  String get langHindi => 'হিন্দি';

  @override
  String get langTamil => 'তামিল';

  @override
  String get langTelugu => 'তেলুগু';

  @override
  String get langBengali => 'বাংলা';

  @override
  String get pastPrescriptionsButton => 'পূর্ববর্তী প্রেসক্রিপশন';

  @override
  String get historyTitle => 'পূর্ববর্তী প্রেসক্রিপশন';

  @override
  String get historyEmpty =>
      'এখনও কোনো পূর্ববর্তী প্রেসক্রিপশন নেই। একটি বিশ্লেষণ করে এখানে দেখুন।';

  @override
  String get historyLoadError =>
      'আপনার পূর্ববর্তী প্রেসক্রিপশন লোড করা যায়নি। আবার চেষ্টা করতে নিচে টানুন।';

  @override
  String get historyProcessing => 'বিশ্লেষণ চলছে...';

  @override
  String get historyFailed => 'বিশ্লেষণ ব্যর্থ হয়েছে';

  @override
  String get historyGate1Chip => 'নতুন ছবি দরকার';

  @override
  String get historyGate1Title => 'এই ছবিটি পড়া যায়নি';

  @override
  String get historyImageUnavailable => 'ছবি উপলব্ধ নয়';

  @override
  String get prescriptionImageLabel => 'মূল প্রেসক্রিপশন';

  @override
  String get openAnalysisInProgress => 'চলমান বিশ্লেষণ খুলুন';

  @override
  String get analysisNotReady => 'আপনার বিশ্লেষণ এখনও প্রস্তুত হচ্ছে।';
}
