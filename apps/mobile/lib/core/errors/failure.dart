/// A user-facing failure. Data-layer exceptions are converted into these at the
/// repository boundary so presentation never has to know about Firebase.
sealed class Failure implements Exception {
  const Failure(this.message, {this.cause, this.stackTrace});

  final String message;
  final Object? cause;
  final StackTrace? stackTrace;

  @override
  String toString() => '$runtimeType: $message';
}

class NetworkFailure extends Failure {
  const NetworkFailure([
    super.message =
        'Cannot reach the service. Keep this tab open and retry. '
        'Unsent drafts have not been saved to the server.',
    Object? cause,
    StackTrace? stackTrace,
  ]) : super(cause: cause, stackTrace: stackTrace);
}

class AuthFailure extends Failure {
  const AuthFailure(super.message, {super.cause, super.stackTrace});
}

class PermissionFailure extends Failure {
  const PermissionFailure(super.message, {super.cause, super.stackTrace});
}

class NotFoundFailure extends Failure {
  const NotFoundFailure([super.message = 'We could not find that record.']);
}

class ServerFailure extends Failure {
  const ServerFailure([
    super.message = 'Something went wrong on our side. Please try again.',
    Object? cause,
    StackTrace? stackTrace,
  ]) : super(cause: cause, stackTrace: stackTrace);
}

class ValidationFailure extends Failure {
  const ValidationFailure(super.message);
}

/// The server refused the request because the record changed since the
/// caller last read it (HTTP 409): a conflicting earlier action or a stale
/// precondition. Callers can explain it or reload instead of retrying blindly.
class ConflictFailure extends Failure {
  const ConflictFailure(super.message);
}
