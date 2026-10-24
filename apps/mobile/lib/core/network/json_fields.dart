import '../errors/failure.dart';

/// Type-checked reads from an API JSON object.
///
/// Each reader throws a [ServerFailure] naming the field when the value has
/// the wrong type, instead of letting a cast throw a `TypeError` that callers
/// do not expect. A list can then skip one malformed record and keep the rest.
extension JsonFields on Map<String, dynamic> {
  Never _invalid(String key) =>
      throw ServerFailure('The API returned an invalid "$key" field.');

  String requiredString(String key) {
    final value = this[key];
    if (value is String) return value;
    _invalid(key);
  }

  String? optionalString(String key) {
    final value = this[key];
    if (value == null || value is String) return value as String?;
    _invalid(key);
  }

  num? optionalNum(String key) {
    final value = this[key];
    if (value == null) return null;
    if (value is num && value.isFinite) return value;
    _invalid(key);
  }

  int? optionalInt(String key) {
    final value = optionalNum(key);
    if (value == null) return null;
    if (value == value.roundToDouble()) return value.toInt();
    _invalid(key);
  }

  bool requiredBool(String key) {
    final value = this[key];
    if (value is bool) return value;
    _invalid(key);
  }

  DateTime requiredDate(String key) => optionalDate(key) ?? _invalid(key);

  /// An ISO-8601 timestamp; a malformed string is invalid, not absent.
  DateTime? optionalDate(String key) {
    final value = optionalString(key);
    if (value == null) return null;
    return DateTime.tryParse(value) ?? _invalid(key);
  }

  /// An optional HTTPS URL; any other scheme is invalid.
  String? optionalHttpsUrl(String key) {
    final value = optionalString(key);
    if (value == null) return null;
    if (Uri.tryParse(value)?.scheme == 'https') return value;
    _invalid(key);
  }

  String requiredHttpsUrl(String key) => optionalHttpsUrl(key) ?? _invalid(key);
}
