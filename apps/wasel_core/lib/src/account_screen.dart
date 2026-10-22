import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'countries.dart';
import 'password_sheet.dart';
import 'session.dart';
import 'strings.dart';
import 'theme.dart';
import 'widgets/brand.dart';
import 'widgets/icons.dart';

/// The signed-in person's ways to sign in: their phone, an email (added with
/// a code sent to it) and a password.
class AccountScreen extends StatelessWidget {
  const AccountScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final session = context.watch<BaseSession>();
    final user = session.user;
    final api = context.read<ApiClient>();

    void saved(String message) => ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(s.t(message))));

    Future<void> setPassword() async {
      final updated = await showSetPasswordSheet(context, api);
      if (updated != null) {
        session.updateUser(updated);
        saved('passwordSaved');
      }
    }

    Future<void> addEmail() async {
      final updated = await showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        builder: (_) => _AddEmailSheet(api: api),
      );
      if (updated != null) {
        session.updateUser(updated);
        saved('emailSaved');
      }
    }

    Future<void> removeEmail() async {
      try {
        session.updateUser(await api.removeEmail());
      } on ApiException catch (error) {
        if (context.mounted) saved('err_${error.code}');
      }
    }

    return Scaffold(
      backgroundColor: t.canvas,
      appBar: AppBar(title: Text(s.t('account'))),
      body: user == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                BezelCard(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Column(
                    children: [
                      _Row(
                        icon: Ph.deviceMobile,
                        title: s.t('accountPhone'),
                        value: displayPhone(user.phone),
                        ltr: true,
                      ),
                      Divider(height: 1, color: t.hairline),
                      _Row(
                        key: const Key('account-email'),
                        icon: Ph.envelopeSimple,
                        title: s.t('accountEmail'),
                        value: user.email ?? s.t('noEmail'),
                        muted: user.email == null,
                        ltr: user.email != null,
                        actions: [
                          TextButton(
                            key: const Key('add-email'),
                            onPressed: addEmail,
                            child: Text(
                              s.t(
                                user.email == null ? 'addEmail' : 'changeEmail',
                              ),
                            ),
                          ),
                          if (user.email != null)
                            IconButton(
                              tooltip: s.t('removeEmail'),
                              onPressed: removeEmail,
                              icon: Icon(Ph.trash, size: 20, color: t.muted),
                            ),
                        ],
                      ),
                      Divider(height: 1, color: t.hairline),
                      _Row(
                        key: const Key('account-password'),
                        icon: Ph.key,
                        title: s.t('accountPassword'),
                        value: s.t(
                          user.hasPassword ? 'passwordSet' : 'passwordNotSet',
                        ),
                        muted: !user.hasPassword,
                        actions: [
                          TextButton(
                            key: const Key('set-password'),
                            onPressed: setPassword,
                            child: Text(
                              s.t(
                                user.hasPassword
                                    ? 'changePassword'
                                    : 'setPassword',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row({
    super.key,
    required this.icon,
    required this.title,
    required this.value,
    this.muted = false,
    this.ltr = false,
    this.actions = const [],
  });

  final IconData icon;
  final String title;
  final String value;
  final bool muted;

  /// Phone numbers and emails read left to right in any language.
  final bool ltr;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsetsDirectional.fromSTEB(16, 12, 8, 12),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: scheme.secondaryContainer,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 20, color: scheme.primary),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontSize: 13, color: t.muted)),
                const SizedBox(height: 2),
                Text(
                  value,
                  textDirection: ltr ? TextDirection.ltr : null,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: muted ? t.muted : t.ink,
                  ),
                ),
              ],
            ),
          ),
          ...actions,
        ],
      ),
    );
  }
}

/// Email, then the code sent to it.
class _AddEmailSheet extends StatefulWidget {
  const _AddEmailSheet({required this.api});
  final ApiClient api;

  @override
  State<_AddEmailSheet> createState() => _AddEmailSheetState();
}

class _AddEmailSheetState extends State<_AddEmailSheet> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  String? _sentTo;
  String? _error;
  bool _busy = false;
  int _resendIn = 0;
  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    _email.dispose();
    _code.dispose();
    super.dispose();
  }

  void _countdown(int seconds) {
    _timer?.cancel();
    setState(() => _resendIn = seconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_resendIn <= 1) timer.cancel();
      if (mounted) setState(() => _resendIn = (_resendIn - 1).clamp(0, 999));
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on ApiException catch (error) {
      setState(() => _error = 'err_${error.code}');
      if (error.retryAfter != null) _countdown(error.retryAfter!);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send() => _run(() async {
    final email = _email.text.trim().toLowerCase();
    final resendIn = await widget.api.addEmail(email);
    setState(() => _sentTo = email);
    _countdown(resendIn);
  });

  Future<void> _confirm() => _run(() async {
    final user = await widget.api.confirmEmail(_sentTo!, _code.text);
    if (mounted) Navigator.pop(context, user);
  });

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
              s.t('addEmail'),
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 16),
            if (_sentTo == null) ...[
              TextField(
                key: const Key('new-email'),
                controller: _email,
                autofocus: true,
                keyboardType: TextInputType.emailAddress,
                autocorrect: false,
                textDirection: TextDirection.ltr,
                autofillHints: const [AutofillHints.email],
                decoration: InputDecoration(
                  prefixIcon: const Icon(Ph.envelopeSimple, size: 20),
                  hintText: s.t('emailHint'),
                  errorText: _error == null ? null : s.t(_error!),
                  errorMaxLines: 3,
                ),
                onSubmitted: (_) => _send(),
              ),
              const SizedBox(height: 20),
              PillButton(
                key: const Key('send-email-code'),
                label: s.t('sendCode'),
                busy: _busy,
                onPressed: _send,
              ),
            ] else ...[
              Text(
                s.t('emailCodeSent', {'email': '\u2066$_sentTo\u2069'}),
                style: TextStyle(color: t.muted, height: 1.5),
              ),
              const SizedBox(height: 16),
              TextField(
                key: const Key('email-code'),
                controller: _code,
                autofocus: true,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                textAlign: TextAlign.center,
                textDirection: TextDirection.ltr,
                maxLength: 6,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                style: const TextStyle(fontSize: 26, letterSpacing: 12),
                decoration: InputDecoration(
                  counterText: '',
                  hintText: '······',
                  errorText: _error == null ? null : s.t(_error!),
                ),
                onChanged: (value) {
                  if (value.length == 6) _confirm();
                },
              ),
              const SizedBox(height: 20),
              PillButton(
                label: s.t('confirm'),
                busy: _busy,
                onPressed: _confirm,
              ),
              const SizedBox(height: 6),
              Center(
                child: _resendIn > 0
                    ? Text(
                        s.t('resendIn', {'s': _resendIn}),
                        style: TextStyle(color: t.muted),
                      )
                    : TextButton(
                        onPressed: _busy ? null : _send,
                        child: Text(s.t('resend')),
                      ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
