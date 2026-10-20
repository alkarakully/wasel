import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:wasel_core/wasel_core.dart';

import '../state/session.dart';
import '../widgets/cart_bar.dart';
import '../widgets/store_card.dart';

/// Search stores and dishes near the delivery spot, optionally within one
/// kind of store. Results follow the typing after a short pause.
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _field = TextEditingController();
  Timer? _pause;
  String _query = '';
  String? _type;
  Future<List<Vendor>>? _results;

  @override
  void dispose() {
    _pause?.cancel();
    _field.dispose();
    super.dispose();
  }

  void _typed(String text) {
    _pause?.cancel();
    _pause = Timer(const Duration(milliseconds: 350), () {
      if (!mounted || text.trim() == _query) return;
      setState(() {
        _query = text.trim();
        _run();
      });
    });
  }

  void _run() {
    if (_query.isEmpty && _type == null) {
      _results = null;
      return;
    }
    _results = context.read<ApiClient>().vendors(
      at: context.read<Session>().deliveryPoint,
      type: _type,
      search: _query,
    );
  }

  @override
  Widget build(BuildContext context) {
    final s = S.of(context);
    final t = WaselTheme.of(context);
    return Scaffold(
      backgroundColor: t.canvas,
      bottomNavigationBar: const CartBar(),
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 16, 4),
              child: Row(
                children: [
                  IconButton(
                    tooltip: MaterialLocalizations.of(context)
                        .backButtonTooltip,
                    onPressed: () => Navigator.maybePop(context),
                    icon: Icon(
                      Directionality.of(context) == TextDirection.rtl
                          ? Ph.arrowRight
                          : Ph.arrowLeft,
                    ),
                  ),
                  Expanded(
                    child: TextField(
                      key: const Key('search-field'),
                      controller: _field,
                      autofocus: true,
                      textInputAction: TextInputAction.search,
                      onChanged: _typed,
                      onSubmitted: (text) {
                        _pause?.cancel();
                        setState(() {
                          _query = text.trim();
                          _run();
                        });
                      },
                      decoration: InputDecoration(
                        hintText: s.t('searchHint'),
                        prefixIcon: const Icon(Ph.magnifyingGlass, size: 22),
                        suffixIcon: ListenableBuilder(
                          listenable: _field,
                          builder: (context, _) => _field.text.isEmpty
                              ? const SizedBox.shrink()
                              : IconButton(
                                  tooltip: s.t('clear'),
                                  icon: const Icon(Ph.x, size: 18),
                                  onPressed: () {
                                    _field.clear();
                                    _pause?.cancel();
                                    setState(() {
                                      _query = '';
                                      _run();
                                    });
                                  },
                                ),
                        ),
                        filled: true,
                        fillColor: t.surface,
                        contentPadding: const EdgeInsets.symmetric(
                          vertical: 14,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(999),
                          borderSide: BorderSide(color: t.hairline),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(999),
                          borderSide: BorderSide(color: t.hairline),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(
              height: 52,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 8,
                ),
                children: [
                  for (final type in storeTypes)
                    Padding(
                      padding: const EdgeInsetsDirectional.only(end: 8),
                      child: FilterChip(
                        key: Key('type-$type'),
                        avatar: Icon(CuisineArt.iconForType(type), size: 18),
                        label: Text(s.t('type_$type')),
                        selected: _type == type,
                        showCheckmark: false,
                        onSelected: (on) => setState(() {
                          _type = on ? type : null;
                          _run();
                        }),
                      ),
                    ),
                ],
              ),
            ),
            Expanded(
              child: _results == null
                  ? ListMessage(
                      text: s.t('searchHelp'),
                      icon: Ph.magnifyingGlass,
                    )
                  : FutureBuilder<List<Vendor>>(
                      future: _results,
                      builder: (context, snapshot) {
                        if (snapshot.hasError) {
                          return ListMessage(
                            text: s.t('err_network'),
                            onRetry: () => setState(_run),
                          );
                        }
                        final stores = snapshot.data;
                        if (stores == null) {
                          return const SingleChildScrollView(
                            child: StoreSkeletons(count: 3),
                          );
                        }
                        if (stores.isEmpty) {
                          return ListMessage(
                            text: _query.isEmpty
                                ? s.t('noStores')
                                : s.t('noResults', {'q': _query}),
                            icon: Ph.magnifyingGlass,
                          );
                        }
                        return ListView(
                          keyboardDismissBehavior:
                              ScrollViewKeyboardDismissBehavior.onDrag,
                          padding: const EdgeInsets.only(top: 4, bottom: 28),
                          children: [
                            for (final (i, store) in stores.indexed)
                              Reveal(
                                key: ValueKey('result-${store.id}-$_query'),
                                index: i,
                                child: StoreCard(store: store),
                              ),
                          ],
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
