import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/store_session.dart';

/// Shown at sign-in while someone has team invites to answer: join the
/// store (as a manager or cashier) or decline. The board comes after.
class InvitesScreen extends StatefulWidget {
  const InvitesScreen({super.key});

  @override
  State<InvitesScreen> createState() => _InvitesScreenState();
}

class _InvitesScreenState extends State<InvitesScreen> {
  int? _busy;
  String? _error;

  Future<void> _answer(StoreInvite invite, {required bool accept}) async {
    setState(() {
      _busy = invite.id;
      _error = null;
    });
    try {
      await context.read<StoreSession>().answerInvite(invite, accept: accept);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = 'err_${error.code}');
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final session = context.watch<StoreSession>();
    final invites = session.invites ?? const <StoreInvite>[];

    return Scaffold(
      backgroundColor: t.canvas,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 640),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      TextButton.icon(
                        key: const Key('invites-logout'),
                        onPressed: session.signOut,
                        icon: const Icon(Ph.signOut, size: 20),
                        label: Text(s.t('logout')),
                      ),
                      const Spacer(),
                      const LanguageSwitch(),
                    ],
                  ),
                  const SizedBox(height: 16),
                  BezelCard(
                    radius: Radii.xl,
                    padding: const EdgeInsets.fromLTRB(24, 28, 24, 24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          s.t('invitesTitle'),
                          style: const TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.w700,
                            height: 1.25,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          s.t('invitesLead'),
                          style: TextStyle(color: t.muted, fontSize: 16),
                        ),
                        const SizedBox(height: 20),
                        for (final invite in invites) ...[
                          _InviteTile(
                            invite: invite,
                            busy: _busy == invite.id,
                            onAccept: () => _answer(invite, accept: true),
                            onDecline: () => _answer(invite, accept: false),
                          ),
                          const SizedBox(height: 12),
                        ],
                        if (_error != null)
                          Text(
                            s.t(_error!),
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.error,
                              fontWeight: FontWeight.w600,
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

class _InviteTile extends StatelessWidget {
  const _InviteTile({
    required this.invite,
    required this.busy,
    required this.onAccept,
    required this.onDecline,
  });

  final StoreInvite invite;
  final bool busy;
  final VoidCallback onAccept;
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    final role = s.t('role_${invite.role}');

    final details = Row(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(Radii.md),
          child: SizedBox(
            width: 56,
            height: 56,
            child: GlazePanel(
              child: Center(
                child: Icon(
                  invite.storeType == 'supermarket' ? Ph.basket : Ph.forkKnife,
                  color: Gold.c400,
                  size: 28,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                invite.storeName,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                s.t('invitedAs', {
                  'who': invite.invitedBy.isEmpty
                      ? s.t('role_owner')
                      : invite.invitedBy,
                  'role': role,
                }),
              ),
              Text(
                s.t('role_${invite.role}_help'),
                style: TextStyle(color: t.muted, fontSize: 14),
              ),
            ],
          ),
        ),
      ],
    );

    // The theme's buttons fill their width, so each takes half the row.
    final actions = Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            key: Key('decline-${invite.id}'),
            onPressed: busy ? null : onDecline,
            icon: const Icon(Ph.x, size: 18),
            label: Text(s.t('decline')),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: FilledButton.icon(
            key: Key('accept-invite-${invite.id}'),
            onPressed: busy ? null : onAccept,
            icon: const Icon(Ph.check, size: 18),
            label: Text(s.t('acceptInvite')),
          ),
        ),
      ],
    );

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: t.surface,
        borderRadius: BorderRadius.circular(Radii.lg),
        border: Border.all(color: t.hairline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [details, const SizedBox(height: 14), actions],
      ),
    );
  }
}
