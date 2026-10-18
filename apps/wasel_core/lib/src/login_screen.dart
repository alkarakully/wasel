import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'api/models.dart';
import 'strings.dart';
import 'session.dart';
import 'theme.dart';
import 'widgets/brand.dart';
import 'widgets/icons.dart';
import 'widgets/language_switch.dart';

/// Phone login: number and channel, then the 6-digit code.
class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    this.acceptUser,
    this.rejectedError = 'err_not_allowed',
  });

  /// Lets an app accept only some accounts (the captain app takes captains).
  /// A rejected sign-in is logged out on the server and shows [rejectedError].
  final bool Function(User user)? acceptUser;
  final String rejectedError;

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
      if (widget.acceptUser != null && !widget.acceptUser!(result.user)) {
        // Don't leave a usable token behind for an account this app refuses.
        api.token = result.token;
        try {
          await api.logout();
        } on ApiException {
          // The token stays unused on the server; nothing to do here.
        }
        api.token = null;
        setState(() => _error = widget.rejectedError);
        return;
      }
      if (mounted) {
        await context.read<BaseSession>().signIn(result.token, result.user);
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
    final t = WaselTheme.of(context);
    final top = MediaQuery.paddingOf(context).top;
    return Scaffold(
      backgroundColor: t.canvas,
      body: ListView(
        padding: EdgeInsets.zero,
        children: [
          GlazePanel(
            padding: EdgeInsets.fromLTRB(28, top + 20, 28, 72),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Align(
                  alignment: AlignmentDirectional.centerEnd,
                  child: LanguageSwitch(onDark: true),
                ),
                const SizedBox(height: 28),
                const Wordmark(size: 64),
                const SizedBox(height: 10),
                const GoldRule(),
                const SizedBox(height: 14),
                Text(
                  s.t('brandLine'),
                  style: const TextStyle(
                    color: Lapis.c100,
                    fontSize: 17,
                    height: 1.55,
                  ),
                ),
              ],
            ),
          ),
          // The form card overlaps the hero, like a plate resting on glaze.
          Transform.translate(
            offset: const Offset(0, -44),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: BezelCard(
                radius: Radii.xl,
                padding: const EdgeInsets.fromLTRB(22, 26, 22, 24),
                child: AnimatedSwitcher(
                  duration: Motion.medium,
                  switchInCurve: Motion.out,
                  switchOutCurve: Motion.out,
                  transitionBuilder: (child, animation) => FadeTransition(
                    opacity: animation,
                    child: SlideTransition(
                      position: Tween(
                        begin: const Offset(0, 0.04),
                        end: Offset.zero,
                      ).animate(animation),
                      child: child,
                    ),
                  ),
                  child: Column(
                    key: ValueKey(_sentTo == null),
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: _sentTo == null
                        ? _phoneStep(s, theme)
                        : _codeStep(s, theme),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _label(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(
      text,
      style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
    ),
  );

  List<Widget> _phoneStep(S s, ThemeData theme) {
    final t = WaselTheme.of(context);
    return [
      Text(
        s.t('loginTitle'),
        style: theme.textTheme.headlineSmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      const SizedBox(height: 6),
      Text(s.t('loginLead'), style: TextStyle(color: t.muted, height: 1.5)),
      const SizedBox(height: 24),
      _label(s.t('phone')),
      Directionality(
        textDirection: TextDirection.ltr,
        child: TextField(
          key: const Key('phone'),
          controller: _phone,
          keyboardType: TextInputType.phone,
          autofillHints: const [AutofillHints.telephoneNumberNational],
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
          decoration: InputDecoration(
            prefixIcon: Padding(
              padding: const EdgeInsetsDirectional.only(start: 16, end: 10),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '+964',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Container(width: 1, height: 22, color: t.hairline),
                ],
              ),
            ),
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
      const SizedBox(height: 8),
      Text(s.t('phoneHelp'), style: TextStyle(fontSize: 13, color: t.muted)),
      const SizedBox(height: 22),
      _label(s.t('sendBy')),
      Row(
        children: [
          Expanded(
            child: _ChannelTile(
              icon: Ph.whatsappLogo,
              label: s.t('whatsapp'),
              selected: _channel == 'whatsapp',
              onTap: () => setState(() => _channel = 'whatsapp'),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _ChannelTile(
              icon: Ph.chatText,
              label: s.t('sms'),
              selected: _channel == 'sms',
              onTap: () => setState(() => _channel = 'sms'),
            ),
          ),
        ],
      ),
      const SizedBox(height: 28),
      PillButton(
        key: const Key('send-code'),
        label: s.t('sendCode'),
        busy: _busy,
        onPressed: () => _sendCode(),
      ),
    ];
  }

  List<Widget> _codeStep(S s, ThemeData theme) {
    final t = WaselTheme.of(context);
    final rtl = Directionality.of(context) == TextDirection.rtl;
    return [
      Align(
        alignment: AlignmentDirectional.centerStart,
        child: TextButton.icon(
          onPressed: () => setState(() {
            _sentTo = null;
            _error = null;
          }),
          icon: Icon(rtl ? Ph.arrowRight : Ph.arrowLeft, size: 18),
          label: Text(s.t('changeNumber')),
        ),
      ),
      const SizedBox(height: 8),
      Text(
        s.t('codeTitle'),
        style: theme.textTheme.headlineSmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        s.t('codeLead', {
          'phone': '\u2066${_formatPhone(_sentTo!)}\u2069',
          'channel': s.t(_sentBy),
        }),
        style: TextStyle(color: t.muted, height: 1.5),
      ),
      const SizedBox(height: 24),
      _label(s.t('code')),
      TextField(
        key: const Key('code'),
        controller: _code,
        autofocus: true,
        keyboardType: TextInputType.number,
        autofillHints: const [AutofillHints.oneTimeCode],
        textAlign: TextAlign.center,
        textDirection: TextDirection.ltr,
        maxLength: 6,
        inputFormatters: [_CodeFormatter()],
        style: TextStyle(
          fontSize: 30,
          letterSpacing: 14,
          fontWeight: FontWeight.w600,
          color: theme.colorScheme.primary,
        ),
        decoration: InputDecoration(
          counterText: '',
          hintText: '······',
          hintStyle: TextStyle(color: t.muted.withValues(alpha: 0.4)),
          errorText: _error == null ? null : s.t(_error!),
        ),
        onChanged: (value) {
          if (value.length == 6) _verify();
        },
      ),
      const SizedBox(height: 24),
      PillButton(label: s.t('confirm'), busy: _busy, onPressed: _verify),
      const SizedBox(height: 14),
      Center(
        child: _resendIn > 0
            ? Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Ph.clock, size: 16, color: t.muted),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      s.t('resendIn', {'s': _resendIn}),
                      style: TextStyle(color: t.muted),
                    ),
                  ),
                ],
              )
            : TextButton(
                onPressed: _busy ? null : () => _sendCode(phone: _sentTo),
                child: Text(s.t('resend')),
              ),
      ),
    ];
  }
}

/// One choice of delivery channel for the code.
class _ChannelTile extends StatelessWidget {
  const _ChannelTile({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = WaselTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      selected: selected,
      child: Pressable(
        onTap: onTap,
        child: AnimatedContainer(
          duration: Motion.fast,
          curve: Motion.out,
          height: 54,
          decoration: BoxDecoration(
            color: selected ? scheme.secondaryContainer : t.sunk,
            borderRadius: BorderRadius.circular(Radii.md),
            border: Border.all(
              color: selected ? scheme.primary : t.hairline,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 22, color: selected ? scheme.primary : t.muted),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    color: selected ? scheme.primary : t.ink,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Keeps the code from whatever was typed or pasted: Arabic-Indic digits
/// become 0-9, and the last 6 digits are kept, so pasting a whole message
/// ("Your Wasel code for +964...: 482913") gives the code, not the phone
/// number.
class _CodeFormatter extends TextInputFormatter {
  static final _nonDigit = RegExp(r'[^0-9]');

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final ascii = newValue.text.runes.map((rune) {
      if (rune >= 0x0660 && rune <= 0x0669) return rune - 0x0660 + 0x30;
      if (rune >= 0x06F0 && rune <= 0x06F9) return rune - 0x06F0 + 0x30;
      return rune;
    });
    var digits = String.fromCharCodes(ascii).replaceAll(_nonDigit, '');
    if (digits.length > 6) digits = digits.substring(digits.length - 6);
    if (digits == newValue.text) return newValue;
    return TextEditingValue(
      text: digits,
      selection: TextSelection.collapsed(offset: digits.length),
    );
  }
}
