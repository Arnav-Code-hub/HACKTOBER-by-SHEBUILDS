import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/json_fields.dart';
import '../../../core/utils/formatters.dart';
import '../../../shared/models/demand_enums.dart';
import '../domain/verification.dart';
import '../domain/verification_repository.dart';

/// Citizen verification against the live API.
///
/// `GET reports/{id}/verification` returns the evidence and whether this
/// citizen may give a verdict; `POST work-orders/{id}/verify` records it. The
/// API alone decides eligibility (original reporter, awaiting verification);
/// [VerificationRequest.canVerify] only shapes the screen.
///
/// Officer field work uses the web workspace, so field assignments are not
/// available in this app.
class HttpVerificationRepository implements VerificationRepository {
  HttpVerificationRepository(this._api);
  final ApiClient _api;

  @override
  Future<VerificationRequest> getRequest(String demandId) async {
    final Object? response;
    try {
      response = await _api.get(
        'reports/${Uri.encodeComponent(demandId)}/verification',
      );
    } on NotFoundFailure {
      throw const NotFoundFailure(
        'Verification opens once the repair work has been submitted.',
      );
    }
    return verificationRequestFromJson(demandId, response);
  }

  @override
  Future<void> submit(VerificationSubmission submission, String uid) async {
    final workOrderId = submission.workOrderId;
    final round = submission.round;
    if (submission.kind != VerificationKind.citizen ||
        workOrderId == null ||
        round == null) {
      throw const ValidationFailure(
        'This verification is missing its work order. Reload and try again.',
      );
    }
    final note = submission.note.trim();
    await _api.post(
      'work-orders/${Uri.encodeComponent(workOrderId)}/verify',
      <String, Object?>{
        'verdict': submission.isFixed,
        if (note.isNotEmpty) 'comment': note,
      },
      // One verdict per round: a retried tap is the same request, and a
      // different verdict for the same round is refused by the API (409).
      idempotencyKey: 'verify-$workOrderId-$round',
    );
  }

  @override
  Future<FieldAssignment> getAssignment(String assignmentId) async =>
      throw const ServerFailure(
        'Officers record field work in the JanMaang web workspace.',
      );

  @override
  Stream<List<FieldAssignment>> watchAssignments(String uid) => Stream.error(
    const ServerFailure(
      'Officers record field work in the JanMaang web workspace.',
    ),
  );
}

/// Explicit mapping of the verification view. Photos must be HTTPS; any
/// malformed field fails visibly as a [ServerFailure] rather than showing
/// invented evidence or throwing a `TypeError`.
VerificationRequest verificationRequestFromJson(
  String demandId,
  Object? value, {
  DateTime? now,
}) {
  try {
    return _verificationRequest(demandId, jsonObject(value), now);
  } on Failure {
    rethrow;
  } on TypeError {
    throw const ServerFailure('The API returned an invalid verification.');
  }
}

VerificationRequest _verificationRequest(
  String demandId,
  Map<String, dynamic> data,
  DateTime? now,
) {
  final round = data.optionalInt('round');
  final canVerify = data.requiredBool('can_verify');
  final category = DemandCategory.values
      .where((c) => c.name == data.requiredString('category'))
      .firstOrNull;
  if (round == null || round < 1 || category == null) {
    throw const ServerFailure('The API returned an invalid verification.');
  }
  final before = _photo(data['before']);
  final after = data['after'] == null ? null : _photo(data['after']);

  return VerificationRequest(
    demandId: demandId,
    demandTitle: data.requiredString('title'),
    reportCode: data.optionalString('report_code'),
    workOrderId: data.requiredString('work_order_id'),
    round: round,
    question: switch (category) {
      DemandCategory.water => 'Is the water source working now?',
      DemandCategory.lighting => 'Are the lights working now?',
      DemandCategory.roads => 'Is the road repaired now?',
      _ => 'Has the problem been fixed?',
    },
    beforePhotoUrl: before.url,
    reportedAgo: Formatters.relative(before.at, now: now),
    afterPhotoUrl: after?.url,
    completedAgo: after == null ? '' : Formatters.relative(after.at, now: now),
    evidenceCardUrl: data.optionalHttpsUrl('card_url'),
    canVerify: canVerify,
    blockedReason: canVerify
        ? null
        : (data.optionalString('blocked_reason') ??
              'This repair is not waiting for your verification.'),
  );
}

({String url, DateTime at}) _photo(Object? value) {
  final photo = jsonObject(value);
  return (
    url: photo.requiredHttpsUrl('url'),
    at: photo.requiredDate('uploaded_at'),
  );
}
