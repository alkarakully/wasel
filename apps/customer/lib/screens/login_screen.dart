import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../api/api_client.dart';
import '../l10n.dart';
import '../state/session.dart';
import '../theme.dart';
import '../widgets/language_switch.dart';

/// Phone login: number and channel, then the 6-digit code.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController();
  final _code = TextEditingController();
  String _channel = 'whatsapp';
  String? _sentTo; // normalized phone once a code is sent
  String _sentBy = 'whatsapp';
  String? _error;
  bool _busy = false;
  int _resendIn = 0;
  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    _phone.dispose();
    _code.dispose();
    super.dispose();
  }

  void _countdown(int seconds) {
    _timer?.cancel();
    setState(() => _resendIn = seconds);
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_resendIn <= 1) timer.cancel();
      setState(() => _resendIn = (_resendIn - 1).clamp(0, 999));
    });
  }

  Future<void> _sendCode({String? phone}) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final sent = await context.read<ApiClient>().requestCode(
        phone ?? _phone.text,
        _channel,
      );
      setState(() {
        _sentTo = sent.phone;
        _sentBy = sent.channel;
        _code.clear();
      });
      _countdown(sent.resendIn);
    } on ApiException catch (error) {
      setState(() => _error = 'err_${error.code}');
      if (error.retryAfter != null) _countdown(error.retryAfter!);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    if (_code.text.length != 6 || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = context.read<ApiClient>();
      final result = await api.verifyCode(_sentTo!, _code.text);
      if (mounted) {
        await context.read<Session>().signIn(result.token, result.user);
      }
    } on ApiException catch (error) {
      setState(() => _error = 'err_${error.code}');
      _code.selection = TextSelection(
        baseOffset: 0,
        extentOffset: _code.text.length,
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _formatPhone(String e164) {
    final local = e164.replaceFirst('+964', '');
    return '+964 ${local.substring(0, 3)} ${local.substring(3, 6)} ${local.substring(6)}';
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        top: false,
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            Container(
              color: Brand.lapis,
              padding: EdgeInsets.fromLTRB(
                24,
                MediaQuery.paddingOf(context).top + 24,
                24,
                28,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'واصل',
                    style: TextStyle(
                      color: Brand.gold,
                      fontSize: 56,
                      fontWeight: FontWeight.w800,
                      height: 1.15,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    s.t('brandLine'),
                    style: const TextStyle(
                      color: Brand.onLapis,
                      fontSize: 16,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: LanguageSwitch(),
                  ),
                  const SizedBox(height: 28),
                  if (_sentTo == null)
                    ..._phoneStep(s, theme)
                  else
                    ..._codeStep(s, theme),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _phoneStep(S s, ThemeData theme) => [
    Text(
      s.t('loginTitle'),
      style: theme.textTheme.headlineMedium?.copyWith(
        fontWeight: FontWeight.w700,
      ),
    ),
    const SizedBox(height: 6),
    Text(
      s.t('loginLead'),
      style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
    ),
    const SizedBox(height: 24),
    Text(s.t('phone'), style: const TextStyle(fontWeight: FontWeight.w600)),
    const SizedBox(height: 8),
    Directionality(
      textDirection: TextDirection.ltr,
      child: TextField(
        key: const Key('phone'),
        controller: _phone,
        keyboardType: TextInputType.phone,
        autofillHints: const [AutofillHints.telephoneNumberNational],
        style: const TextStyle(fontSize: 18),
        decoration: InputDecoration(
          prefixText: '+964  ',
          hintText: '0770 123 4567',
          errorText: _error == null ? null : s.t(_error!),
          errorMaxLines: 2,
        ),
        onChanged: (_) {
          if (_error != null) setState(() => _error = null);
        },
        onSubmitted: (_) => _sendCode(),
      ),
    ),
    const SizedBox(height: 6),
    Text(
      s.t('phoneHelp'),
      style: TextStyle(fontSize: 13, color: theme.colorScheme.onSurfaceVariant),
    ),
    const SizedBox(height: 20),
    Text(s.t('sendBy'), style: const TextStyle(fontWeight: FontWeight.w600)),
    const SizedBox(height: 8),
    SegmentedButton<String>(
      segments: [
        ButtonSegment(
          value: 'whatsapp',
          label: Text(s.t('whatsapp')),
          icon: const Icon(Icons.chat_outlined),
        ),
        ButtonSegment(
          value: 'sms',
          label: Text(s.t('sms')),
          icon: const Icon(Icons.sms_outlined),
        ),
      ],
      selected: {_channel},
      onSelectionChanged: (value) => setState(() => _channel = value.first),
    ),
    const SizedBox(height: 28),
    FilledButton(
      key: const Key('send-code'),
      onPressed: _busy ? null : () => _sendCode(),
      child: Text(s.t('sendCode')),
    ),
  ];

  List<Widget> _codeStep(S s, ThemeData theme) => [
    Align(
      alignment: AlignmentDirectional.centerStart,
      child: TextButton.icon(
        onPressed: () => setState(() {
          _sentTo = null;
          _error = null;
        }),
        icon: const Icon(Icons.arrow_back),
        label: Text(s.t('changeNumber')),
      ),
    ),
    const SizedBox(height: 8),
    Text(
      s.t('codeTitle'),
      style: theme.textTheme.headlineMedium?.copyWith(
        fontWeight: FontWeight.w700,
      ),
    ),
    const SizedBox(height: 6),
    Text(
      s.t('codeLead', {
        'phone': '\u2066${_formatPhone(_sentTo!)}\u2069',
        'channel': s.t(_sentBy),
      }),
      style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
    ),
    const SizedBox(height: 24),
    Text(s.t('code'), style: const TextStyle(fontWeight: FontWeight.w600)),
    const SizedBox(height: 8),
    TextField(
      key: const Key('code'),
      controller: _code,
      autofocus: true,
      keyboardType: TextInputType.number,
      autofillHints: const [AutofillHints.oneTimeCode],
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
      maxLength: 6,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      style: const TextStyle(
        fontSize: 28,
        letterSpacing: 12,
        fontWeight: FontWeight.w600,
      ),
      decoration: InputDecoration(
        counterText: '',
        errorText: _error == null ? null : s.t(_error!),
      ),
      onChanged: (value) {
        if (value.length == 6) _verify();
      },
    ),
    const SizedBox(height: 24),
    FilledButton(
      onPressed: _busy ? null : _verify,
      child: Text(s.t('confirm')),
    ),
    const SizedBox(height: 12),
    Center(
      child: _resendIn > 0
          ? Text(
              s.t('resendIn', {'s': _resendIn}),
              style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
            )
          : TextButton(
              onPressed: _busy ? null : () => _sendCode(phone: _sentTo),
              child: Text(s.t('resend')),
            ),
    ),
  ];
}
