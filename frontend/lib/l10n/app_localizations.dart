import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_bn.dart';
import 'app_localizations_en.dart';
import 'app_localizations_hi.dart';
import 'app_localizations_ta.dart';
import 'app_localizations_te.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('bn'),
    Locale('en'),
    Locale('hi'),
    Locale('ta'),
    Locale('te')
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Medication Companion'**
  String get appTitle;

  /// No description provided for @appSubtitle.
  ///
  /// In en, this message translates to:
  /// **'AI-powered prescription analysis'**
  String get appSubtitle;

  /// No description provided for @appLanguage.
  ///
  /// In en, this message translates to:
  /// **'App language'**
  String get appLanguage;

  /// No description provided for @continueDevMode.
  ///
  /// In en, this message translates to:
  /// **'Continue in dev mode'**
  String get continueDevMode;

  /// No description provided for @devModeHint.
  ///
  /// In en, this message translates to:
  /// **'ENVIRONMENT=local — Firebase auth bypassed'**
  String get devModeHint;

  /// No description provided for @orSignInFirebase.
  ///
  /// In en, this message translates to:
  /// **'or sign in with Firebase'**
  String get orSignInFirebase;

  /// No description provided for @signIn.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get signIn;

  /// No description provided for @createAccount.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get createAccount;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @emailInvalid.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid email address'**
  String get emailInvalid;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @confirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get confirmPassword;

  /// No description provided for @passwordMinLength.
  ///
  /// In en, this message translates to:
  /// **'Use at least 6 characters'**
  String get passwordMinLength;

  /// No description provided for @passwordsDoNotMatch.
  ///
  /// In en, this message translates to:
  /// **'Passwords do not match'**
  String get passwordsDoNotMatch;

  /// No description provided for @passwordStrengthHint.
  ///
  /// In en, this message translates to:
  /// **'Use 8+ characters with upper & lower case, numbers, and symbols'**
  String get passwordStrengthHint;

  /// No description provided for @passwordStrengthWeak.
  ///
  /// In en, this message translates to:
  /// **'Weak'**
  String get passwordStrengthWeak;

  /// No description provided for @passwordStrengthFair.
  ///
  /// In en, this message translates to:
  /// **'Fair'**
  String get passwordStrengthFair;

  /// No description provided for @passwordStrengthGood.
  ///
  /// In en, this message translates to:
  /// **'Good'**
  String get passwordStrengthGood;

  /// No description provided for @passwordStrengthStrong.
  ///
  /// In en, this message translates to:
  /// **'Strong'**
  String get passwordStrengthStrong;

  /// No description provided for @showPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get showPassword;

  /// No description provided for @hidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get hidePassword;

  /// No description provided for @createAccountDisclaimer.
  ///
  /// In en, this message translates to:
  /// **'This app provides information only. Always discuss medications with your doctor or pharmacist.'**
  String get createAccountDisclaimer;

  /// No description provided for @errorInvalidEmail.
  ///
  /// In en, this message translates to:
  /// **'Invalid email address.'**
  String get errorInvalidEmail;

  /// No description provided for @errorWrongPassword.
  ///
  /// In en, this message translates to:
  /// **'Incorrect email or password.'**
  String get errorWrongPassword;

  /// No description provided for @errorUserNotFound.
  ///
  /// In en, this message translates to:
  /// **'No account found for this email.'**
  String get errorUserNotFound;

  /// No description provided for @errorEmailInUse.
  ///
  /// In en, this message translates to:
  /// **'An account already exists for this email. Try signing in.'**
  String get errorEmailInUse;

  /// No description provided for @errorWeakPassword.
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 6 characters.'**
  String get errorWeakPassword;

  /// No description provided for @errorGeneric.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Please try again.'**
  String get errorGeneric;

  /// No description provided for @hello.
  ///
  /// In en, this message translates to:
  /// **'Hello, {name}'**
  String hello(String name);

  /// No description provided for @readyToAnalyse.
  ///
  /// In en, this message translates to:
  /// **'Ready to analyse your prescription?'**
  String get readyToAnalyse;

  /// No description provided for @audioLanguage.
  ///
  /// In en, this message translates to:
  /// **'Audio language'**
  String get audioLanguage;

  /// No description provided for @disclaimerHome.
  ///
  /// In en, this message translates to:
  /// **'This app is for information only. Always discuss your medications with your doctor or pharmacist.'**
  String get disclaimerHome;

  /// No description provided for @analysePrescription.
  ///
  /// In en, this message translates to:
  /// **'Analyse prescription'**
  String get analysePrescription;

  /// No description provided for @signOut.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get signOut;

  /// No description provided for @scanPrescription.
  ///
  /// In en, this message translates to:
  /// **'Scan prescription'**
  String get scanPrescription;

  /// No description provided for @tapGallery.
  ///
  /// In en, this message translates to:
  /// **'Tap to select from gallery'**
  String get tapGallery;

  /// No description provided for @camera.
  ///
  /// In en, this message translates to:
  /// **'Camera'**
  String get camera;

  /// No description provided for @gallery.
  ///
  /// In en, this message translates to:
  /// **'Gallery'**
  String get gallery;

  /// No description provided for @retakePhoto.
  ///
  /// In en, this message translates to:
  /// **'Retake photo'**
  String get retakePhoto;

  /// No description provided for @stepReading.
  ///
  /// In en, this message translates to:
  /// **'Reading prescription...'**
  String get stepReading;

  /// No description provided for @stepChecking.
  ///
  /// In en, this message translates to:
  /// **'Checking interactions...'**
  String get stepChecking;

  /// No description provided for @stepGenerating.
  ///
  /// In en, this message translates to:
  /// **'Generating explanation...'**
  String get stepGenerating;

  /// No description provided for @statusPending.
  ///
  /// In en, this message translates to:
  /// **'Queued for analysis...'**
  String get statusPending;

  /// No description provided for @statusProcessing.
  ///
  /// In en, this message translates to:
  /// **'Analysing prescription...'**
  String get statusProcessing;

  /// No description provided for @statusDone.
  ///
  /// In en, this message translates to:
  /// **'Preparing your results...'**
  String get statusDone;

  /// No description provided for @loadingHint.
  ///
  /// In en, this message translates to:
  /// **'This takes about 20–40 seconds.\nPlease keep this screen open.'**
  String get loadingHint;

  /// No description provided for @accessError.
  ///
  /// In en, this message translates to:
  /// **'Could not access camera or gallery: {error}'**
  String accessError(String error);

  /// No description provided for @prescriptionAnalysis.
  ///
  /// In en, this message translates to:
  /// **'Prescription Analysis'**
  String get prescriptionAnalysis;

  /// No description provided for @medicationsFound.
  ///
  /// In en, this message translates to:
  /// **'Medications found ({count})'**
  String medicationsFound(int count);

  /// No description provided for @interactions.
  ///
  /// In en, this message translates to:
  /// **'Interactions ({count})'**
  String interactions(int count);

  /// No description provided for @summary.
  ///
  /// In en, this message translates to:
  /// **'Summary'**
  String get summary;

  /// No description provided for @audioExplanation.
  ///
  /// In en, this message translates to:
  /// **'Audio explanation'**
  String get audioExplanation;

  /// No description provided for @playing.
  ///
  /// In en, this message translates to:
  /// **'Playing...'**
  String get playing;

  /// No description provided for @tapToPlay.
  ///
  /// In en, this message translates to:
  /// **'Tap to play audio explanation'**
  String get tapToPlay;

  /// No description provided for @doctorQuestions.
  ///
  /// In en, this message translates to:
  /// **'Questions for your doctor'**
  String get doctorQuestions;

  /// No description provided for @backToHome.
  ///
  /// In en, this message translates to:
  /// **'Back to home'**
  String get backToHome;

  /// No description provided for @severityHigh.
  ///
  /// In en, this message translates to:
  /// **'High severity — review urgently with your doctor'**
  String get severityHigh;

  /// No description provided for @severityModerate.
  ///
  /// In en, this message translates to:
  /// **'Moderate severity — discuss with your doctor'**
  String get severityModerate;

  /// No description provided for @severityLow.
  ///
  /// In en, this message translates to:
  /// **'Low severity — informational'**
  String get severityLow;

  /// No description provided for @severityInfo.
  ///
  /// In en, this message translates to:
  /// **'No interactions found'**
  String get severityInfo;

  /// No description provided for @severityNone.
  ///
  /// In en, this message translates to:
  /// **'No concerns identified'**
  String get severityNone;

  /// No description provided for @couldNotResolve.
  ///
  /// In en, this message translates to:
  /// **'Could not be resolved'**
  String get couldNotResolve;

  /// No description provided for @crossVisitDetected.
  ///
  /// In en, this message translates to:
  /// **'Detected from your medication history'**
  String get crossVisitDetected;

  /// No description provided for @tagNew.
  ///
  /// In en, this message translates to:
  /// **'NEW'**
  String get tagNew;

  /// No description provided for @tagExisting.
  ///
  /// In en, this message translates to:
  /// **'EXISTING'**
  String get tagExisting;

  /// No description provided for @tagUnresolved.
  ///
  /// In en, this message translates to:
  /// **'UNRESOLVED'**
  String get tagUnresolved;

  /// No description provided for @sevChipHigh.
  ///
  /// In en, this message translates to:
  /// **'HIGH'**
  String get sevChipHigh;

  /// No description provided for @sevChipModerate.
  ///
  /// In en, this message translates to:
  /// **'MODERATE'**
  String get sevChipModerate;

  /// No description provided for @sevChipLow.
  ///
  /// In en, this message translates to:
  /// **'LOW'**
  String get sevChipLow;

  /// No description provided for @sevChipInfo.
  ///
  /// In en, this message translates to:
  /// **'INFO'**
  String get sevChipInfo;

  /// No description provided for @sevChipNone.
  ///
  /// In en, this message translates to:
  /// **'NONE'**
  String get sevChipNone;

  /// No description provided for @sevWordHigh.
  ///
  /// In en, this message translates to:
  /// **'high'**
  String get sevWordHigh;

  /// No description provided for @sevWordModerate.
  ///
  /// In en, this message translates to:
  /// **'moderate'**
  String get sevWordModerate;

  /// No description provided for @sevWordLow.
  ///
  /// In en, this message translates to:
  /// **'low'**
  String get sevWordLow;

  /// No description provided for @mechanismDataset.
  ///
  /// In en, this message translates to:
  /// **'Dataset records a {severityWord} interaction between {a} and {b}. Please discuss this with your doctor or pharmacist.'**
  String mechanismDataset(String severityWord, String a, String b);

  /// No description provided for @shownInEnglishNote.
  ///
  /// In en, this message translates to:
  /// **'(shown in English)'**
  String get shownInEnglishNote;

  /// No description provided for @langEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get langEnglish;

  /// No description provided for @langHindi.
  ///
  /// In en, this message translates to:
  /// **'Hindi'**
  String get langHindi;

  /// No description provided for @langTamil.
  ///
  /// In en, this message translates to:
  /// **'Tamil'**
  String get langTamil;

  /// No description provided for @langTelugu.
  ///
  /// In en, this message translates to:
  /// **'Telugu'**
  String get langTelugu;

  /// No description provided for @langBengali.
  ///
  /// In en, this message translates to:
  /// **'Bengali'**
  String get langBengali;

  /// No description provided for @pastPrescriptionsButton.
  ///
  /// In en, this message translates to:
  /// **'Past prescriptions'**
  String get pastPrescriptionsButton;

  /// No description provided for @historyTitle.
  ///
  /// In en, this message translates to:
  /// **'Past prescriptions'**
  String get historyTitle;

  /// No description provided for @historyEmpty.
  ///
  /// In en, this message translates to:
  /// **'No past prescriptions yet. Analyse one to see it here.'**
  String get historyEmpty;

  /// No description provided for @historyLoadError.
  ///
  /// In en, this message translates to:
  /// **'Could not load your past prescriptions. Pull to retry.'**
  String get historyLoadError;

  /// No description provided for @historyProcessing.
  ///
  /// In en, this message translates to:
  /// **'Analysing...'**
  String get historyProcessing;

  /// No description provided for @historyFailed.
  ///
  /// In en, this message translates to:
  /// **'Analysis failed'**
  String get historyFailed;

  /// No description provided for @historyGate1Chip.
  ///
  /// In en, this message translates to:
  /// **'Needs retake'**
  String get historyGate1Chip;

  /// No description provided for @historyGate1Title.
  ///
  /// In en, this message translates to:
  /// **'Couldn\'t analyse this image'**
  String get historyGate1Title;

  /// No description provided for @historyImageUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Image unavailable'**
  String get historyImageUnavailable;

  /// No description provided for @prescriptionImageLabel.
  ///
  /// In en, this message translates to:
  /// **'Original prescription'**
  String get prescriptionImageLabel;

  /// No description provided for @openAnalysisInProgress.
  ///
  /// In en, this message translates to:
  /// **'Open in-progress analysis'**
  String get openAnalysisInProgress;

  /// No description provided for @analysisNotReady.
  ///
  /// In en, this message translates to:
  /// **'Your analysis is still being prepared.'**
  String get analysisNotReady;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['bn', 'en', 'hi', 'ta', 'te'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'bn':
      return AppLocalizationsBn();
    case 'en':
      return AppLocalizationsEn();
    case 'hi':
      return AppLocalizationsHi();
    case 'ta':
      return AppLocalizationsTa();
    case 'te':
      return AppLocalizationsTe();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
