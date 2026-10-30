import 'dart:async';
import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:janmaang/core/errors/failure.dart';
import 'package:janmaang/core/network/api_client.dart';
import 'package:janmaang/features/auth/data/firebase_auth_repository.dart';
import 'package:janmaang/features/auth/domain/app_user.dart';

/// Minimal Firebase fakes: only the members the repository uses are real.
class FakeUser implements User {
  FakeUser(this.uid);
  @override
  final String uid;
  @override
  String? get email => '$uid@example.test';
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeCredential implements UserCredential {
  FakeCredential(this.user);
  @override
  final User? user;
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeAuth implements FirebaseAuth {
  final _changes = StreamController<User?>.broadcast();
  int signOuts = 0;

  void restore(User? user) => _changes.add(user);

  @override
  Stream<User?> authStateChanges() => _changes.stream;

  @override
  Future<UserCredential> signInWithEmailAndPassword({
    required String email,
    required String password,
  }) async {
    final user = FakeUser('firebase-uid');
    _changes.add(user);
    return FakeCredential(user);
  }

  @override
  Future<void> signOut() async {
    signOuts++;
    _changes.add(null);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Map<String, Object?> profile(String role) => <String, Object?>{
  'id': 'local-user',
  'firebase_uid': 'firebase-uid',
  'role': role,
  'display_name': 'Test',
  'email': 'firebase-uid@example.test',
  'district_id': 'district',
  'department_id': null,
  'institute_id': null,
};

void main() {
  group('ApiClient.warmUp', () {
    test(
      'sends one unauthenticated /health request for concurrent callers',
      () async {
        var healthCalls = 0;
        final api = ApiClient(
          baseUrl: 'https://api.example.test',
          token: () async => 'secret-token',
          client: MockClient((request) async {
            expect(request.url.toString(), 'https://api.example.test/health');
            expect(request.headers.containsKey('Authorization'), isFalse);
            healthCalls++;
            return http.Response('{"status":"ok"}', 200);
          }),
        );

        await Future.wait(<Future<void>>[api.warmUp(), api.warmUp()]);
        await api.warmUp();

        expect(healthCalls, 1);
        api.close();
      },
    );

    test('retries, then fails visibly without caching the failure', () async {
      var healthCalls = 0;
      final api = ApiClient(
        baseUrl: 'https://api.example.test',
        token: () async => 'token',
        client: MockClient((request) async {
          healthCalls++;
          return http.Response('starting', 503);
        }),
      );

      Future<void> warm() => api.warmUp(attempts: 2, pause: Duration.zero);
      await expectLater(warm(), throwsA(isA<NetworkFailure>()));
      expect(healthCalls, 2);
      await expectLater(warm(), throwsA(isA<NetworkFailure>()));
      expect(healthCalls, 4);
      api.close();
    });

    test('keeps waiting while a sleeping host answers 503', () async {
      var healthCalls = 0;
      final api = ApiClient(
        baseUrl: 'https://api.example.test',
        token: () async => 'token',
        client: MockClient((request) async {
          healthCalls++;
          return healthCalls <= 2
              ? http.Response('starting', 503)
              : http.Response('{"status":"ok"}', 200);
        }),
      );

      await api.warmUp(pause: Duration.zero);
      expect(healthCalls, 3);
      api.close();
    });

    test('gives up once the time budget is spent', () async {
      final api = ApiClient(
        baseUrl: 'https://api.example.test',
        token: () async => 'token',
        client: MockClient((request) async => http.Response('starting', 503)),
      );

      await expectLater(
        api.warmUp(
          pause: const Duration(milliseconds: 20),
          budget: const Duration(milliseconds: 100),
        ),
        throwsA(isA<NetworkFailure>()),
      );
      api.close();
    });
  });

  group('FirebaseAuthRepository', () {
    ({FirebaseAuthRepository repository, FakeAuth auth, List<String> paths})
    build(http.Response Function(http.Request) profileResponse) {
      final paths = <String>[];
      final auth = FakeAuth();
      final api = ApiClient(
        baseUrl: 'https://api.example.test',
        token: () async => 'token',
        client: MockClient((request) async {
          paths.add(request.url.path);
          if (request.url.path == '/health') return http.Response('{}', 200);
          return profileResponse(request);
        }),
      );
      return (
        repository: FirebaseAuthRepository(auth, api),
        auth: auth,
        paths: paths,
      );
    }

    test('a restored session the API cannot confirm emits an error', () async {
      final setup = build((_) => http.Response('down', 503));
      final events = setup.repository.authStateChanges();
      final next = events.first;

      setup.auth.restore(FakeUser('firebase-uid'));

      await expectLater(next, throwsA(isA<ServerFailure>()));
    });

    test('a citizen profile signs in after warming the API', () async {
      final setup = build(
        (_) => http.Response(jsonEncode(profile('citizen')), 200),
      );
      final events = setup.repository.authStateChanges();
      final next = events.first;

      setup.auth.restore(FakeUser('firebase-uid'));

      final user = await next;
      expect(user, isA<AppUser>());
      expect(user!.uid, 'local-user');
      expect(setup.paths, <String>['/health', '/api/v1/users/me']);
    });

    test('a staff account is refused, signed out, and not also streamed as an error', () async {
      final setup = build(
        (_) => http.Response(jsonEncode(profile('officer')), 200),
      );
      final emitted = <Object?>[];
      final subscription = setup.repository.authStateChanges().listen(
        emitted.add,
        onError: emitted.add,
      );

      await expectLater(
        setup.repository.signInWithEmail(
          email: 'officer@example.test',
          password: 'password',
        ),
        throwsA(
          isA<PermissionFailure>().having(
            (f) => f.message,
            'message',
            contains('for citizens'),
          ),
        ),
      );
      await pumpEventQueue();

      expect(setup.auth.signOuts, 1);
      expect(emitted.whereType<Failure>(), isEmpty);
      // The sign-in and the auth listener share one profile request.
      expect(setup.paths.where((p) => p == '/api/v1/users/me').length, 1);
      await subscription.cancel();
    });
  });
}
