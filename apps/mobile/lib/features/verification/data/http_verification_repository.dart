import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
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

/// Explicit mapping of the verification view. Photos must be HTTPS; an
/// unexpected shape fails visibly rather than showing invented evidence.
VerificationRequest verificationRequestFromJson(
  String demandId,
  Object? value, {
  DateTime? now,
}) {
  final data = jsonObject(value);
  final workOrderId = data['work_order_id'];
  final title = data['title'];
  final round = data['round'];
  final canVerify = data['can_verify'];
  final category = DemandCategory.values
      .where((c) => c.name == data['category'])
      .firstOrNull;
  if (workOrderId is! String ||
      title is! String ||
      round is! int ||
      round < 1 ||
      canVerify is! bool ||
      category == null) {
    throw const ServerFailure('The API returned an invalid verification.');
  }
  final before = _photo(data['before'], required: true)!;
  final after = _photo(data['after'], required: false);
  final card = data['card_url'];
  if (card != null && (card is! String || Uri.tryParse(card)?.scheme != 'https')) {
    throw const ServerFailure('The API returned an invalid evidence card.');
  }

  return VerificationRequest(
    demandId: demandId,
    demandTitle: title,
    reportCode: data['report_code'] as String?,
    workOrderId: workOrderId,
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
    evidenceCardUrl: card as String?,
    canVerify: canVerify,
    blockedReason: canVerify
        ? null
        : (data['blocked_reason'] as String? ??
              'This repair is not waiting for your verification.'),
  );
}

({String url, DateTime at})? _photo(Object? value, {required bool required}) {
  if (value == null && !required) return null;
  final photo = jsonObject(value);
  final url = photo['url'];
  final at = DateTime.tryParse(photo['uploaded_at']?.toString() ?? '');
  if (url is! String || Uri.tryParse(url)?.scheme != 'https' || at == null) {
    throw const ServerFailure('The API returned invalid evidence photos.');
  }
  return (url: url, at: at);
}
