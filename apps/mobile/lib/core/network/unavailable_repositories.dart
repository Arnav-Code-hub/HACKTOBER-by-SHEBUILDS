import '../../features/ledger/domain/ledger_entry.dart';
import '../../features/ledger/domain/ledger_repository.dart';
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
