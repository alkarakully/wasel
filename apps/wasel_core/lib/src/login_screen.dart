import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api/api_client.dart';
import 'api/models.dart';
import 'countries.dart';
import 'password_sheet.dart';
import 'strings.dart';
import 'session.dart';
import 'theme.dart';
import 'widgets/brand.dart';
import 'widgets/country_picker.dart';
import 'widgets/icons.dart';
import 'widgets/language_switch.dart';
import 'widgets/motion.dart';

/// Sign-in with a code (WhatsApp to a phone, or email to a confirmed
/// address) or with a password (phone number or email). A phone's first
/// code sign-in also creates the account; afterwards the app offers to set
/// a password for next time.
class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    this.acceptUser,
    this.admitUser,
    this.rejectedError = 'err_not_allowed',
  });

  /// Lets an app accept only some accounts (the captain app takes captains).
  /// A rejected sign-in is logged out on the server and shows [rejectedError].
  final bool Function(User user)? acceptUser;

  /// Like [acceptUser], for when the answer needs the server (the store app
  /// also lets in someone with a team invite). The client is already signed
  /// in with the new token while it runs.
  final Future<bool> Function(ApiClient api, User user)? admitUser;
  final String rejectedError;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _code = TextEditingController();
  // 'code' or 'password'.
  String _mode = 'code';
  // Where a code goes, or what to sign in with: 'phone' or 'email'.
  String _by = 'phone';
  // The phone's country: Iraq at first, then the last one picked here.
  String _country = 'IQ';
  static const _countryKey = 'wasel_phone_country';
  // Once tapped "Not now", the password offer doesn't come back on this device.
  static const _offerSkippedKey = 'wasel_password_offer_skipped';
  String? _sentTo; // normalized phone or email once a code is sent
  String _sentBy = 'whatsapp';
  String? _error;
  bool _busy = false;
  int _resendIn = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    SharedPreferences.getInstance().then((prefs) {
      final saved = prefs.getString(_countryKey);
      if (saved != null && mounted && countries.any((c) => c.code == saved)) {
        setState(() => _country = saved);
      }
    });
  }

  Future<void> _pickCountry() async {
    final picked = await showCountryPicker(context, _country);
    if (picked == null || !mounted) return;
    setState(() {
      _country = picked;
      _error = null;
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_countryKey, picked);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _phone.dispose();
    _email.dispose();
    _password.dispose();
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

  void _switch({String? mode, String? by}) => setState(() {
    _mode = mode ?? _mode;
    _by = by ?? _by;
    _error = null;
  });

  Future<void> _sendCode({String? to}) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final email = to != null ? to.contains('@') : _by == 'email';
      final address = to ?? (email ? _email.text.trim() : _phone.text);
      final sent = await context.read<ApiClient>().requestCode(
        phone: email ? null : address,
        email: email ? address : null,
        country: _country,
      );
      setState(() {
        _sentTo = sent.to;
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
    await _signIn(
      () => context.read<ApiClient>().verifyCode(
        _sentTo!,
        _code.text,
        country: _country,
      ),
      byCode: true,
    );
    if (_error != null) {
      _code.selection = TextSelection(
        baseOffset: 0,
        extentOffset: _code.text.length,
      );
    }
  }

  Future<void> _passwordSignIn() async {
    if (_password.text.isEmpty || _busy) return;
    final login = _by == 'email' ? _email.text.trim() : _phone.text;
    await _signIn(
      () => context.read<ApiClient>().passwordLogin(
        login,
        _password.text,
        country: _country,
      ),
    );
  }

  /// Signs in with [attempt]'s token if this app takes the account; after a
  /// code sign-in, offers a password to someone who has none.
  Future<void> _signIn(
    Future<({String token, User user})> Function() attempt, {
    bool byCode = false,
  }) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    final api = context.read<ApiClient>();
    try {
      final result = await attempt();
      var admitted = widget.acceptUser?.call(result.user) ?? true;
      if (admitted && widget.admitUser != null) {
        api.token = result.token;
        try {
          admitted = await widget.admitUser!(api, result.user);
        } finally {
          api.token = null;
        }
      }
      if (!admitted) {
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
      var user = result.user;
      final prefs = await SharedPreferences.getInstance();
      if (byCode &&
          !user.hasPassword &&
          prefs.getBool(_offerSkippedKey) != true &&
          mounted) {
        api.token = result.token;
        // The sign-in itself is done; don't spin behind the sheet.
        setState(() => _busy = false);
        final updated = await showSetPasswordSheet(context, api, offer: true);
        api.token = null;
        if (updated == null) await prefs.setBool(_offerSkippedKey, true);
        user = updated ?? user;
      }
      if (mounted) {
        await context.read<BaseSession>().signIn(result.token, user);
      }
    } on ApiException catch (error) {
      setState(() => _error = 'err_${error.code}');
      if (error.code == 'locked' && error.retryAfter != null) {
        _countdown(error.retryAfter!);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _formatAddress(String to) => to.contains('@') ? to : displayPhone(to);

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final theme = Theme.of(context);
    final t = WaselTheme.of(context);
    final top = MediaQuery.paddingOf(context).top;

    final form = BezelCard(
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
              ? _startStep(s, theme)
              : _codeStep(s, theme),
        ),
      ),
    );

    Widget brand(double wordmark) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Reveal(child: Wordmark(size: wordmark)),
        const SizedBox(height: 10),
        const GoldRule(),
        const SizedBox(height: 14),
        Reveal(
          index: 2,
          child: Text(
            s.t('brandLine'),
            style: const TextStyle(
              color: Lapis.c100,
              fontSize: 17,
              height: 1.55,
            ),
          ),
        ),
      ],
    );

    return Scaffold(
      backgroundColor: t.canvas,
      body: LayoutBuilder(
        builder: (context, box) {
          // Tablets and wide windows: glaze panel beside a centred form.
          if (box.maxWidth >= 900) {
            return Row(
              children: [
                Expanded(
                  flex: 5,
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(12, top + 12, 12, 12),
                    child: GlazePanel(
                      radius: Radii.xl,
                      padding: const EdgeInsets.all(40),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          const Align(
                            alignment: AlignmentDirectional.centerEnd,
                            child: LanguageSwitch(onDark: true),
                          ),
                          const Spacer(),
                          brand(104),
                        ],
                      ),
                    ),
                  ),
                ),
                Expanded(
                  flex: 7,
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(32),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 480),
                        child: Reveal(index: 3, offset: 28, child: form),
                      ),
                    ),
                  ),
                ),
              ],
            );
          }
          return ListView(
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
                    // Phones keep the compact logo; tablets in portrait get a larger one.
                    brand(box.maxWidth < 600 ? 64 : 92),
                  ],
                ),
              ),
              // The form card overlaps the hero, like a plate resting on glaze.
              Transform.translate(
                offset: const Offset(0, -44),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 560),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Reveal(index: 3, offset: 28, child: form),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
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

  Widget _phoneField(S s, ThemeData theme, {VoidCallback? onSubmitted}) {
    final t = WaselTheme.of(context);
    return Directionality(
      textDirection: TextDirection.ltr,
      child: TextField(
        key: const Key('phone'),
        controller: _phone,
        keyboardType: TextInputType.phone,
        autofillHints: const [AutofillHints.telephoneNumberNational],
        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
        decoration: InputDecoration(
          prefixIcon: Semantics(
            button: true,
            label:
                '${s.t('phoneCountry')}: ${countryFor(_country).name(s.lang)}',
            excludeSemantics: true,
            child: InkWell(
              key: const Key('phone-country'),
              onTap: _busy ? null : _pickCountry,
              borderRadius: const BorderRadius.horizontal(
                left: Radius.circular(14),
              ),
              child: Padding(
                padding: const EdgeInsetsDirectional.only(start: 14, end: 10),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CountryBadge(_country),
                    const SizedBox(width: 6),
                    Text(
                      '+${countryFor(_country).dial}',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                    const SizedBox(width: 2),
                    Icon(Ph.caretDown, size: 14, color: t.muted),
                    const SizedBox(width: 8),
                    Container(width: 1, height: 22, color: t.hairline),
                  ],
                ),
              ),
            ),
          ),
          hintText: _country == 'IQ' ? '0770 123 4567' : null,
          errorText: _mode == 'code' && _error != null ? s.t(_error!) : null,
          errorMaxLines: 2,
        ),
        onChanged: (_) {
          if (_error != null) setState(() => _error = null);
        },
        onSubmitted: (_) => onSubmitted?.call(),
      ),
    );
  }

  Widget _emailField(S s, {VoidCallback? onSubmitted}) => TextField(
    key: const Key('email'),
    controller: _email,
    keyboardType: TextInputType.emailAddress,
    autocorrect: false,
    textDirection: TextDirection.ltr,
    autofillHints: const [AutofillHints.email],
    style: const TextStyle(fontSize: 17),
    decoration: InputDecoration(
      prefixIcon: const Icon(Ph.envelopeSimple, size: 20),
      hintText: s.t('emailHint'),
      errorText: _mode == 'code' && _error != null ? s.t(_error!) : null,
      errorMaxLines: 3,
    ),
    onChanged: (_) {
      if (_error != null) setState(() => _error = null);
    },
    onSubmitted: (_) => onSubmitted?.call(),
  );

  List<Widget> _startStep(S s, ThemeData theme) {
    final t = WaselTheme.of(context);
    final code = _mode == 'code';
    return [
      Text(
        s.t('loginTitle'),
        style: theme.textTheme.headlineSmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      const SizedBox(height: 6),
      Text(
        s.t(code ? 'loginLeadCode' : 'loginLeadPassword'),
        style: TextStyle(color: t.muted, height: 1.5),
      ),
      const SizedBox(height: 18),
      SegmentedButton<String>(
        key: const Key('login-mode'),
        showSelectedIcon: false,
        segments: [
          ButtonSegment(value: 'code', label: Text(s.t('byCode'))),
          ButtonSegment(value: 'password', label: Text(s.t('byPassword'))),
        ],
        selected: {_mode},
        onSelectionChanged: (picked) => _switch(mode: picked.first),
      ),
      const SizedBox(height: 22),
      _label(code ? s.t('sendBy') : s.t('phoneOrEmail')),
      Row(
        children: [
          Expanded(
            child: _ChannelTile(
              key: const Key('by-phone'),
              icon: code ? Ph.whatsappLogo : Ph.deviceMobile,
              label: code ? s.t('whatsapp') : s.t('phone'),
              selected: _by == 'phone',
              onTap: () => _switch(by: 'phone'),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: _ChannelTile(
              key: const Key('by-email'),
              icon: Ph.envelopeSimple,
              label: s.t('email'),
              selected: _by == 'email',
              onTap: () => _switch(by: 'email'),
            ),
          ),
        ],
      ),
      const SizedBox(height: 16),
      AutofillGroup(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_by == 'phone') ...[
              _label(s.t('phone')),
              _phoneField(
                s,
                theme,
                onSubmitted: code ? () => _sendCode() : _passwordSignIn,
              ),
              if (code) ...[
                const SizedBox(height: 8),
                Text(
                  s.t('phoneHelp'),
                  style: TextStyle(fontSize: 13, color: t.muted),
                ),
              ],
            ] else ...[
              _label(s.t('emailAddress')),
              _emailField(
                s,
                onSubmitted: code ? () => _sendCode() : _passwordSignIn,
              ),
              if (code) ...[
                const SizedBox(height: 8),
                Text(
                  s.t('emailCodeHelp'),
                  style: TextStyle(fontSize: 13, color: t.muted, height: 1.4),
                ),
              ],
            ],
            if (!code) ...[
              const SizedBox(height: 16),
              _label(s.t('password')),
              PasswordField(
                controller: _password,
                errorText: _error == null ? null : s.t(_error!),
                onChanged: (_) {
                  if (_error != null) setState(() => _error = null);
                },
                onSubmitted: (_) => _passwordSignIn(),
              ),
            ],
          ],
        ),
      ),
      const SizedBox(height: 28),
      PillButton(
        key: Key(code ? 'send-code' : 'sign-in'),
        label: s.t(code ? 'sendCode' : 'signIn'),
        busy: _busy,
        onPressed: code ? () => _sendCode() : _passwordSignIn,
      ),
      if (!code) ...[
        const SizedBox(height: 8),
        TextButton(
          key: const Key('forgot-password'),
          onPressed: () => _switch(mode: 'code'),
          child: Text(s.t('forgotPassword'), textAlign: TextAlign.center),
        ),
      ],
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
          label: Text(
            s.t(_sentTo!.contains('@') ? 'changeAddress' : 'changeNumber'),
          ),
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
          'phone': '\u2066${_formatAddress(_sentTo!)}\u2069',
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
                onPressed: _busy ? null : () => _sendCode(to: _sentTo),
                child: Text(s.t('resend')),
              ),
      ),
    ];
  }
}

/// One choice of delivery channel for the code.
class _ChannelTile extends StatelessWidget {
  const _ChannelTile({
    super.key,
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
