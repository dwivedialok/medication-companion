import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../auth/firebase_auth_service.dart';
import '../config.dart';
import '../l10n/app_localizations.dart';
import '../utils/password_strength.dart';
import '../widgets/language_selector.dart';
import '../widgets/password_strength_indicator.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  String? _error;
  PasswordStrength _passwordStrength = PasswordStrength.empty;

  bool get _isSignUp => _tabController.index == 1;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(_onTabChanged);
    _passwordController.addListener(_onPasswordChanged);
  }

  void _onTabChanged() {
    setState(() {
      if (!_tabController.indexIsChanging) {
        _error = null;
        if (_tabController.index == 0) {
          _confirmPasswordController.clear();
        }
      }
    });
  }

  void _onPasswordChanged() {
    setState(() {
      _passwordStrength = evaluatePasswordStrength(_passwordController.text);
    });
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _passwordController.removeListener(_onPasswordChanged);
    _tabController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });

    final auth = context.read<FirebaseAuthService>();
    try {
      if (_isSignUp) {
        await auth.createAccountWithEmail(
          _emailController.text.trim(),
          _passwordController.text,
        );
      } else {
        await auth.signInWithEmail(
          _emailController.text.trim(),
          _passwordController.text,
        );
      }
      if (mounted) context.go('/home');
    } catch (e) {
      setState(() => _error = _friendlyError(context, e.toString()));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _friendlyError(BuildContext context, String raw) {
    final l10n = AppLocalizations.of(context)!;
    if (raw.contains('invalid-email')) return l10n.errorInvalidEmail;
    if (raw.contains('wrong-password') || raw.contains('invalid-credential')) {
      return l10n.errorWrongPassword;
    }
    if (raw.contains('user-not-found')) return l10n.errorUserNotFound;
    if (raw.contains('email-already-in-use')) return l10n.errorEmailInUse;
    if (raw.contains('weak-password')) return l10n.errorWeakPassword;
    return l10n.errorGeneric;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Align(
                    alignment: Alignment.centerRight,
                    child: LanguageSelector(compact: true),
                  ),
                  const SizedBox(height: 8),
                  Icon(Icons.medication, size: 64, color: theme.colorScheme.primary),
                  const SizedBox(height: 16),
                  Text(
                    l10n.appTitle,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    l10n.appSubtitle,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 32),

                  if (AppConfig.isLocal) ...[
                    FilledButton.icon(
                      onPressed: () {
                        context.read<FirebaseAuthService>().signInLocalDev();
                        context.go('/home');
                      },
                      icon: const Icon(Icons.developer_mode),
                      label: Text(l10n.continueDevMode),
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.orange.shade700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      l10n.devModeHint,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: Colors.orange.shade700,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Row(children: [
                      const Expanded(child: Divider()),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        child: Text(l10n.orSignInFirebase),
                      ),
                      const Expanded(child: Divider()),
                    ]),
                    const SizedBox(height: 24),
                  ],

                  TabBar(
                    controller: _tabController,
                    tabs: [
                      Tab(text: l10n.signIn),
                      Tab(text: l10n.createAccount),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TextFormField(
                          controller: _emailController,
                          keyboardType: TextInputType.emailAddress,
                          autofillHints: const [AutofillHints.email],
                          textInputAction: TextInputAction.next,
                          decoration: InputDecoration(
                            labelText: l10n.email,
                            prefixIcon: const Icon(Icons.email_outlined),
                            border: const OutlineInputBorder(),
                          ),
                          validator: (v) {
                            final value = v?.trim() ?? '';
                            if (value.isEmpty || !value.contains('@')) {
                              return l10n.emailInvalid;
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          autofillHints: _isSignUp
                              ? const [AutofillHints.newPassword]
                              : const [AutofillHints.password],
                          textInputAction:
                              _isSignUp ? TextInputAction.next : TextInputAction.done,
                          onFieldSubmitted: _isSignUp ? null : (_) => _submit(),
                          decoration: InputDecoration(
                            labelText: l10n.password,
                            prefixIcon: const Icon(Icons.lock_outline),
                            border: const OutlineInputBorder(),
                            helperText: _isSignUp ? l10n.passwordStrengthHint : null,
                            helperMaxLines: 2,
                            suffixIcon: IconButton(
                              tooltip: _obscurePassword
                                  ? l10n.showPassword
                                  : l10n.hidePassword,
                              onPressed: () => setState(
                                () => _obscurePassword = !_obscurePassword,
                              ),
                              icon: Icon(
                                _obscurePassword
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                              ),
                            ),
                          ),
                          validator: (v) {
                            if (v == null || v.length < 6) {
                              return l10n.passwordMinLength;
                            }
                            return null;
                          },
                        ),
                        if (_isSignUp)
                          PasswordStrengthIndicator(strength: _passwordStrength),
                        AnimatedCrossFade(
                          duration: const Duration(milliseconds: 200),
                          crossFadeState: _isSignUp
                              ? CrossFadeState.showSecond
                              : CrossFadeState.showFirst,
                          firstChild: const SizedBox.shrink(),
                          secondChild: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const SizedBox(height: 16),
                              TextFormField(
                                controller: _confirmPasswordController,
                                obscureText: _obscureConfirmPassword,
                                autofillHints: const [AutofillHints.newPassword],
                                textInputAction: TextInputAction.done,
                                onFieldSubmitted: (_) => _submit(),
                                decoration: InputDecoration(
                                  labelText: l10n.confirmPassword,
                                  prefixIcon: const Icon(Icons.lock_person_outlined),
                                  border: const OutlineInputBorder(),
                                  suffixIcon: IconButton(
                                    tooltip: _obscureConfirmPassword
                                        ? l10n.showPassword
                                        : l10n.hidePassword,
                                    onPressed: () => setState(
                                      () => _obscureConfirmPassword =
                                          !_obscureConfirmPassword,
                                    ),
                                    icon: Icon(
                                      _obscureConfirmPassword
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                    ),
                                  ),
                                ),
                                validator: (v) {
                                  if (!_isSignUp) return null;
                                  if (v != _passwordController.text) {
                                    return l10n.passwordsDoNotMatch;
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 12),
                              Text(
                                l10n.createAccountDisclaimer,
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: theme.colorScheme.errorContainer,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              _error!,
                              style: TextStyle(
                                color: theme.colorScheme.onErrorContainer,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ),
                        ],
                        const SizedBox(height: 24),
                        FilledButton(
                          onPressed: _loading ? null : _submit,
                          child: _loading
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : AnimatedBuilder(
                                  animation: _tabController,
                                  builder: (_, __) => Text(
                                    _isSignUp ? l10n.createAccount : l10n.signIn,
                                  ),
                                ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
