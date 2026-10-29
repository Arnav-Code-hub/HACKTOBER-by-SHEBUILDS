import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/localization/app_locale.dart';
import '../../core/localization/app_strings.dart';
import '../../core/theme/app_spacing.dart';

class AppLanguageSelector extends ConsumerWidget {
  const AppLanguageSelector({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final strings = AppStrings.of(context);
    final languageCode =
        ref.watch(appLocaleProvider).value?.languageCode ?? 'en';
    final colorScheme = Theme.of(context).colorScheme;

    final dropdown = DropdownButtonHideUnderline(
      child: DropdownButton<String>(
        value: appLanguageNames.containsKey(languageCode) ? languageCode : 'en',
        isExpanded: !compact,
        icon: const Icon(Icons.expand_more_rounded),
        onChanged: (value) {
          if (value != null) {
            ref.read(appLocaleProvider.notifier).setLanguage(value);
          }
        },
        items: appLanguageNames.entries
            .map(
              (entry) => DropdownMenuItem<String>(
                value: entry.key,
                child: Text(entry.value, overflow: TextOverflow.ellipsis),
              ),
            )
            .toList(growable: false),
      ),
    );

    if (compact) {
      return Semantics(
        label: strings.text('language'),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(24),
          ),
          child: Padding(
            padding: const EdgeInsets.only(left: Insets.sm, right: Insets.xs),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Icon(
                  Icons.language_rounded,
                  size: 18,
                  color: colorScheme.primary,
                ),
                const SizedBox(width: Insets.xs),
                SizedBox(width: 112, child: dropdown),
              ],
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          strings.text('language'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: Insets.xs),
        Text(
          strings.text('language_help'),
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: Insets.sm),
        InputDecorator(
          decoration: const InputDecoration(border: OutlineInputBorder()),
          child: dropdown,
        ),
      ],
    );
  }
}
