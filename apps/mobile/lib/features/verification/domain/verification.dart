import 'package:flutter/foundation.dart';

import '../../../shared/models/demand_enums.dart';

/// A citizen confirming whether a funded fix actually worked, or a field
/// officer capturing evidence against a checklist.
@immutable
class VerificationSubmission {
  const VerificationSubmission({
    required this.demandId,
    required this.kind,
    required this.isFixed,
    this.checklist = const <ChecklistItem>[],
    this.photoPaths = const <String>[],
    this.note = '',
    this.latitude,
    this.longitude,
    this.workOrderId,
    this.round,
  });

  final String demandId;

  /// The work order and verification round the verdict answers. Required by
  /// the live API; one verdict is accepted per round.
  final String? workOrderId;
  final int? round;
  final VerificationKind kind;
  final bool isFixed;
  final List<ChecklistItem> checklist;
  final List<String> photoPaths;
  final String note;
  final double? latitude;
  final double? longitude;
}

@immutable
class ChecklistItem {
  const ChecklistItem({
    required this.id,
    required this.question,
    required this.hint,
    this.checked = false,
  });

  final String id;
  final String question;
  final String hint;
  final bool checked;

  ChecklistItem copyWith({bool? checked}) => ChecklistItem(
    id: id,
    question: question,
    hint: hint,
    checked: checked ?? this.checked,
  );
}

/// The work a field officer has been assigned — the header of the field tool.
@immutable
class FieldAssignment {
  const FieldAssignment({
    required this.id,
    required this.demandId,
    required this.projectName,
    required this.locationLabel,
    required this.objective,
    required this.checklist,
    this.beforePhotoUrl,
  });

  final String id;
  final String demandId;
  final String projectName;
  final String locationLabel;
  final String objective;
  final List<ChecklistItem> checklist;
  final String? beforePhotoUrl;
}

/// What the citizen verification screen shows: the original report's
/// "before" photograph beside the officer's completion photograph. They are
/// evidence for the citizen's own judgement, not proof of a repair.
@immutable
class VerificationRequest {
  const VerificationRequest({
    required this.demandId,
    required this.demandTitle,
    required this.question,
    this.beforePhotoUrl,
    this.reportedAgo = '',
    this.workOrderId,
    this.reportCode,
    this.afterPhotoUrl,
    this.completedAgo = '',
    this.evidenceCardUrl,
    this.round = 1,
    this.afterRound,
    this.canVerify = true,
    this.blockedReason,
  });

  final String demandId;
  final String demandTitle;

  /// "Is the water source working now?"
  final String question;
  final String? beforePhotoUrl;
  final String reportedAgo;

  final String? workOrderId;
  final String? reportCode;

  /// The officer's completion evidence, when uploaded.
  final String? afterPhotoUrl;
  final String completedAgo;

  /// Server-generated before/after card. Its verdict text comes from saved
  /// data: "Awaiting citizen verification" until a verdict is recorded.
  final String? evidenceCardUrl;

  /// Verification round; above 1 after an earlier "not fixed" verdict.
  final int round;

  /// Round of the displayed completion; it can be the returned previous one.
  final int? afterRound;

  /// Whether this citizen may record a verdict now. Only the original
  /// reporter can, and only while the work awaits verification.
  final bool canVerify;

  /// Why [canVerify] is false, in words the citizen can act on.
  final String? blockedReason;
}
