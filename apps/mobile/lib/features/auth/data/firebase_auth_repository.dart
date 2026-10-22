import 'package:firebase_auth/firebase_auth.dart';

import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
import '../domain/app_user.dart';
import '../domain/auth_repository.dart';

class FirebaseAuthRepository implements AuthRepository {
  FirebaseAuthRepository(this._auth, this._api);
  final FirebaseAuth _auth;
  final ApiClient _api;
  AppUser? _user;

  @override
  AppUser? get currentUser => _user;

  Future<AppUser> _profile(User user) async {
    final data = jsonObject(await _api.get('users/me'));
    const roles = <String>{
      'citizen',
      'student',
      'faculty',
      'institute',
      'panchayat',
      'department',
      'officer',
      'industry',
      'gov_admin',
      'super_admin',
    };
    if (data['firebase_uid'] != user.uid ||
        data['id'] is! String ||
        !roles.contains(data['role'])) {
      throw const AuthFailure(
        'The API profile does not match your Firebase account.',
      );
    }
    return _user = AppUser(
      uid: data['id'] as String,
      firebaseUid: user.uid,
      role: data['role'] as String,
      email: data['email'] as String? ?? user.email,
      displayName: data['display_name'] as String?,
      district: data['district_name'] as String? ?? '',
      isFieldOfficer: data['role'] == 'officer',
    );
  }

  @override
  Stream<AppUser?> authStateChanges() => _auth.authStateChanges().asyncMap((
    user,
  ) async {
    if (user == null) return _user = null;
    try {
      return await _profile(user);
    } on Failure {
      // A Firebase identity alone is insufficient for scoped business access.
      _user = null;
      rethrow;
    }
  });

  @override
  Future<AppUser> signInWithEmail({
    required String email,
    required String password,
  }) async {
    try {
      final credential = await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
      return await _profile(credential.user!);
    } on FirebaseAuthException catch (error) {
      throw AuthFailure(switch (error.code) {
        'invalid-email' => 'Enter a valid email address.',
        'too-many-requests' => 'Too many login attempts. Try again later.',
        'network-request-failed' =>
          'Cannot reach Firebase. Check your connection.',
        'operation-not-allowed' =>
          'Enable email/password sign-in in Firebase Authentication.',
        _ => 'Sign-in failed. Check your account details and Firebase setup.',
      });
    } on Failure {
      await _auth.signOut();
      rethrow;
    }
  }

  @override
  Future<void> signOut() async {
    _user = null;
    await _auth.signOut();
  }

  @override
  Future<String> sendOtp(String phoneNumber) async => throw const ServerFailure(
    'Phone OTP is not connected in the Day 1 live build. Use email/password.',
  );

  @override
  Future<AppUser> verifyOtp({
    required String verificationId,
    required String smsCode,
    bool linkAadhaar = false,
  }) async => throw const ServerFailure('Phone OTP is not connected.');

  @override
  Future<AppUser> signInWithGoogle() async => throw const ServerFailure(
    'Google sign-in is not connected in the Day 1 live build. Use email/password.',
  );

  @override
  Future<void> updateProfile(AppUser user) async =>
      throw const ServerFailure('Profile updates are not connected yet.');
}
