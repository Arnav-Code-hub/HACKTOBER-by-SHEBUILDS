import '../../features/ledger/domain/ledger_entry.dart';
import '../../features/ledger/domain/ledger_repository.dart';
import '../../features/verification/domain/verification.dart';
import '../../features/verification/domain/verification_repository.dart';
import '../errors/failure.dart';

/// Explicit failures prevent unfinished live features from returning fixtures
/// or claiming that a write was saved.
class UnavailableLedgerRepository implements LedgerRepository {
  @override
  Stream<List<LedgerEntry>> watchEntries({String? district}) => Stream.error(
    const ServerFailure('The public ledger is not connected yet.'),
  );
  @override
  Future<LedgerSummary> getSummary({String? district}) async =>
      throw const ServerFailure('Funding totals are not connected yet.');
}

class UnavailableVerificationRepository implements VerificationRepository {
  @override
  Future<VerificationRequest> getRequest(String demandId) async =>
      throw const ServerFailure('Citizen verification is not connected yet.');
  @override
  Future<FieldAssignment> getAssignment(String assignmentId) async =>
      throw const ServerFailure('Field assignments are not connected yet.');
  @override
  Stream<List<FieldAssignment>> watchAssignments(String uid) => Stream.error(
    const ServerFailure('Field assignments are not connected yet.'),
  );
  @override
  Future<void> submit(VerificationSubmission submission, String uid) async =>
      throw const ServerFailure(
        'Verification cannot be saved in this build yet.',
      );
}
