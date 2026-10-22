import 'package:flutter/material.dart';

import 'api/api_client.dart';
import 'api/models.dart';
import 'strings.dart';
import 'theme.dart';
import 'widgets/brand.dart';
import 'widgets/icons.dart';

/// A password field with a show/hide eye.
class PasswordField extends StatefulWidget {
  const PasswordField({
    super.key,
    required this.controller,
    this.label,
    this.errorText,
    this.newPassword = false,
    this.onSubmitted,
    this.onChanged,
    this.autofocus = false,
  });

  final TextEditingController controller;
  final String? label;
  final String? errorText;

  /// Lets the phone's password manager suggest a strong new password.
  final bool newPassword;
  final ValueChanged<String>? onSubmitted;
  final ValueChanged<String>? onChanged;
  final bool autofocus;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _hidden = true;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    return TextField(
      key: widget.key == null ? const Key('password') : null,
      controller: widget.controller,
      autofocus: widget.autofocus,
      obscureText: _hidden,
      enableSuggestions: false,
      autocorrect: false,
      textDirection: TextDirection.ltr,
      autofillHints: [
        widget.newPassword ? AutofillHints.newPassword : AutofillHints.password,
      ],
      decoration: InputDecoration(
        labelText: widget.label,
        errorText: widget.errorText,
        errorMaxLines: 3,
        prefixIcon: const Icon(Ph.lockSimple, size: 20),
        suffixIcon: IconButton(
          tooltip: s.t('showPassword'),
          icon: Icon(_hidden ? Ph.eye : Ph.eyeSlash, size: 20),
          onPressed: () => setState(() => _hidden = !_hidden),
        ),
      ),
      onChanged: widget.onChanged,
      onSubmitted: widget.onSubmitted,
    );
  }
}

/// Asks for a new password and saves it. Returns the updated account, or
/// null if the person tapped "Not now". [api] must be signed in.
Future<User?> showSetPasswordSheet(
  BuildContext context,
  ApiClient api, {
  bool offer = false,
}) {
  return showModalBottomSheet<User>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _SetPasswordSheet(api: api, offer: offer),
  );
}

class _SetPasswordSheet extends StatefulWidget {
  const _SetPasswordSheet({required this.api, required this.offer});
  final ApiClient api;

  /// Offered right after a code sign-in (vs. chosen from the account screen).
  final bool offer;

  @override
  State<_SetPasswordSheet> createState() => _SetPasswordSheetState();
}

class _SetPasswordSheetState extends State<_SetPasswordSheet> {
  final _password = TextEditingController();
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _password.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_password.text.length < 8 || _busy) {
      setState(() => _error = 'err_weak_password');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final user = await widget.api.setPassword(_password.text);
      if (mounted) Navigator.pop(context, user);
    } on ApiException catch (error) {
      setState(() => _error = 'err_${error.code}');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        22,
        0,
        22,
        16 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              widget.offer ? s.t('setPasswordTitle') : s.t('setPassword'),
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              s.t('setPasswordLead'),
              style: TextStyle(color: t.muted, height: 1.5),
            ),
            const SizedBox(height: 18),
            AutofillGroup(
              child: PasswordField(
                key: const Key('new-password'),
                controller: _password,
                label: s.t('newPassword'),
                newPassword: true,
                autofocus: true,
                errorText: _error == null ? null : s.t(_error!),
                onSubmitted: (_) => _save(),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              s.t('passwordHelp'),
              style: TextStyle(fontSize: 13, color: t.muted),
            ),
            const SizedBox(height: 20),
            PillButton(
              key: const Key('save-password'),
              label: s.t('savePassword'),
              busy: _busy,
              onPressed: _save,
            ),
            if (widget.offer) ...[
              const SizedBox(height: 6),
              TextButton(
                key: const Key('not-now'),
                onPressed: () => Navigator.pop(context),
                child: Text(s.t('notNow')),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
