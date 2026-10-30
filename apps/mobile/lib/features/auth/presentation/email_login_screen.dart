import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/routes.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/jm_app_bar.dart';
import '../../../shared/widgets/jm_logo.dart';
import 'auth_controller.dart';

/// Day 1 live login. Firebase handles credentials; FastAPI only receives an ID
/// token and supplies the scoped application profile.
class EmailLoginScreen extends ConsumerStatefulWidget {
  const EmailLoginScreen({super.key});
  @override
  ConsumerState<EmailLoginScreen> createState() => _EmailLoginScreenState();
}

class _EmailLoginScreenState extends ConsumerState<EmailLoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _form = GlobalKey<FormState>();

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    final ok = await ref
        .read(authControllerProvider.notifier)
        .signInWithEmail(_email.text, _password.text);
    if (ok && mounted) context.goNamed(AppRoute.home.name);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(authControllerProvider);
    return Scaffold(
      appBar: const JmAppBar(showBrand: true, actions: <Widget>[]),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(Insets.lg),
            child: Form(
              key: _form,
              child: AutofillGroup(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: <Widget>[
                    Center(child: JmLogo.mark(size: 56)),
                    const SizedBox(height: Insets.lg),
                    Text(
                      'Citizen Login',
                      style: Theme.of(context).textTheme.headlineLarge,
                    ),
                    const SizedBox(height: Insets.sm),
                    const Text(
                      'Sign in with your provisioned Firebase account. '
                      'Email/password is available in this build.',
                    ),
                    const SizedBox(height: Insets.lg),
                    TextFormField(
                      controller: _email,
                      enabled: !state.isSending,
                      keyboardType: TextInputType.emailAddress,
                      autofillHints: const <String>[AutofillHints.email],
                      decoration: const InputDecoration(labelText: 'Email'),
                      validator: (value) =>
                          value != null && value.trim().contains('@')
                          ? null
                          : 'Enter a valid email address.',
                      textInputAction: TextInputAction.next,
                    ),
                    const SizedBox(height: Insets.md),
                    TextFormField(
                      controller: _password,
                      enabled: !state.isSending,
                      obscureText: true,
                      autofillHints: const <String>[AutofillHints.password],
                      decoration: const InputDecoration(labelText: 'Password'),
                      validator: (value) => value == null || value.isEmpty
                          ? 'Enter your password.'
                          : null,
                      onFieldSubmitted: (_) {
                        if (!state.isSending) _submit();
                      },
                    ),
                    if (state.error != null) ...<Widget>[
                      const SizedBox(height: Insets.md),
                      Text(
                        state.error!.message,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ],
                    const SizedBox(height: Insets.lg),
                    FilledButton(
                      onPressed: state.isSending ? null : _submit,
                      child: Text(state.isSending ? 'Signing in…' : 'Sign in'),
                    ),
                    const SizedBox(height: Insets.md),
                    const Text(
                      'Phone OTP, Google sign-in, and account registration '
                      'are not connected in the Day 1 live build.',
                    ),
                    const SizedBox(height: Insets.lg),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(Insets.md),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Judge demo access',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: Insets.sm),
                            const Text(
                              'Copy these credentials into the sign-in fields:',
                            ),
                            const SizedBox(height: Insets.sm),
                            const SelectableText(
                              'Email: citizen@janmaang.example',
                            ),
                            const SelectableText('Password: 123456'),
                            const SizedBox(height: Insets.sm),
                            const Text(
                              'Use this account to report problems, track complaints '
                              'and verify repairs. This is a shared demonstration '
                              'account; other judges may change its demo records.',
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
