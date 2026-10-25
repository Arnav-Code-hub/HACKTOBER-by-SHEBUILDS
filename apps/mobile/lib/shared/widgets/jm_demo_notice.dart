import 'package:flutter/material.dart';

import '../../core/theme/app_spacing.dart';
import '../../core/theme/janmaang_typography.dart';
import 'jm_card.dart';

/// Identifies sample content even when authentication and reporting are live.
class JmDemoNotice extends StatelessWidget {
  const JmDemoNotice({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return JmCard(
      padding: const EdgeInsets.all(Insets.md),
      backgroundColor: scheme.secondaryContainer,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.science_outlined, color: scheme.onSecondaryContainer),
          const SizedBox(width: Insets.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Demo data',
                  style: JanMaangTypography.labelMd.copyWith(
                    color: scheme.onSecondaryContainer,
                  ),
                ),
                const SizedBox(height: Insets.xs),
                Text(
                  message,
                  style: JanMaangTypography.bodySm.copyWith(
                    color: scheme.onSecondaryContainer,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
