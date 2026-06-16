import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../auth/firebase_auth_service.dart';
import '../config.dart';

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
  final _formKey = GlobalKey<FormState>();
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.addListener(() => setState(() => _error = null));
  }

  @override
  void dispose() {
    _tabController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
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
      if (_tabController.index == 0) {
        await auth.signInWithEmail(
          _emailController.text.trim(),
          _passwordController.text,
        );
      } else {
        await auth.createAccountWithEmail(
          _emailController.text.trim(),
          _passwordController.text,
        );
      }
      if (mounted) context.go('/home');
    } catch (e) {
      setState(() => _error = _friendlyError(e.toString()));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _friendlyError(String raw) {
    if (raw.contains('invalid-email')) return 'Invalid email address.';
    if (raw.contains('wrong-password') || raw.contains('invalid-credential')) {
      return 'Incorrect email or password.';
    }
    if (raw.contains('user-not-found')) return 'No account found for this email.';
    if (raw.contains('email-already-in-use')) {
      return 'An account already exists for this email. Try signing in.';
    }
    if (raw.contains('weak-password')) {
      return 'Password must be at least 6 characters.';
    }
    return 'Something went wrong. Please try again.';
  }

  @override
  Widget build(BuildContext context) {
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
                  const SizedBox(height: 32),
                  Icon(Icons.medication, size: 64, color: theme.colorScheme.primary),
                  const SizedBox(height: 16),
                  Text(
                    'Medication Companion',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    'AI-powered prescription analysis',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 40),

                  // Dev-mode bypass button
                  if (AppConfig.isLocal) ...[
                    FilledButton.icon(
                      onPressed: () => context.go('/home'),
                      icon: const Icon(Icons.developer_mode),
                      label: const Text('Continue in dev mode'),
                      style: FilledButton.styleFrom(
                        backgroundColor: Colors.orange.shade700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'ENVIRONMENT=local — Firebase auth bypassed',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: Colors.orange.shade700,
                      ),
                    ),
                    const SizedBox(height: 24),
                    const Row(children: [
                      Expanded(child: Divider()),
                      Padding(
                        padding: EdgeInsets.symmetric(horizontal: 12),
                        child: Text('or sign in with Firebase'),
                      ),
                      Expanded(child: Divider()),
                    ]),
                    const SizedBox(height: 24),
                  ],

                  // Sign in / Sign up tabs
                  TabBar(
                    controller: _tabController,
                    tabs: const [Tab(text: 'Sign in'), Tab(text: 'Create account')],
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
                          textInputAction: TextInputAction.next,
                          decoration: const InputDecoration(
                            labelText: 'Email',
                            prefixIcon: Icon(Icons.email_outlined),
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) =>
                              (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: true,
                          textInputAction: TextInputAction.done,
                          onFieldSubmitted: (_) => _submit(),
                          decoration: const InputDecoration(
                            labelText: 'Password',
                            prefixIcon: Icon(Icons.lock_outline),
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) =>
                              (v == null || v.length < 6) ? 'Minimum 6 characters' : null,
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 12),
                          Text(
                            _error!,
                            style: TextStyle(color: theme.colorScheme.error),
                            textAlign: TextAlign.center,
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
                                    _tabController.index == 0 ? 'Sign in' : 'Create account',
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
