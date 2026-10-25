import 'package:flutter/foundation.dart';

import '../../../core/errors/failure.dart';
import '../../../core/network/api_client.dart';
import '../../../shared/models/demand_enums.dart';
import '../../report/data/report_dto.dart';
import '../domain/demand.dart';
import '../domain/demand_cluster.dart';
import '../domain/demands_repository.dart';

class HttpDemandsRepository implements DemandsRepository {
  HttpDemandsRepository(this._api);
  final ApiClient _api;

  /// Records in the last "my reports" load that this build could not read.
  /// They are skipped rather than replaced with invented placeholders.
  int unreadableInLastLoad = 0;

  @override
  Stream<List<Demand>> watchMyDemands(String uid) async* {
    final data = jsonObject(
      await _api.get('reports', query: <String, String>{'mine': 'true'}),
    );
    final items = data['items'];
    if (items is! List) {
      throw const ServerFailure('The API returned an invalid report list.');
    }
    // One unreadable record must not hide the citizen's other reports.
    final readable = <Demand>[];
    var unreadable = 0;
    for (final item in items) {
      try {
        readable.add(demandFromJson(item));
      } on Failure catch (failure) {
        unreadable++;
        final id = item is Map ? item['id'] : null;
        debugPrint('Skipped unreadable report $id: ${failure.message}');
      }
    }
    unreadableInLastLoad = unreadable;
    yield readable;
  }

  @override
  Future<Demand> getDemand(String id) async =>
      demandFromJson(await _api.get('reports/${Uri.encodeComponent(id)}'));

  @override
  Stream<List<Demand>> watchNearbyDemands({int limit = 10}) => Stream.error(
    const ServerFailure(
      'Nearby community reports are not connected yet. Use Track for your saved reports.',
    ),
  );
  @override
  Future<DemandCluster> getCluster(String id) async =>
      throw const ServerFailure('Cluster views are not connected yet.');
  @override
  Future<DemandCluster?> findSimilarCluster({
    required DemandCategory category,
    required double latitude,
    required double longitude,
  }) async =>
      throw const ServerFailure('Cluster suggestions are not connected yet.');
  @override
  Future<int> joinCluster(String clusterId) async {
    final response = jsonObject(
      await _api.post(
        'clusters/${Uri.encodeComponent(clusterId)}/support',
        const <String, Object?>{},
      ),
    );
    final supporters = response['supporter_count'];
    if (response['id'] != clusterId || supporters is! int || supporters < 1) {
      throw const ServerFailure('The API returned an invalid support receipt.');
    }
    return supporters;
  }

  @override
  Future<void> questionRanking({
    required String demandId,
    required String uid,
    required String reason,
  }) async =>
      throw const ServerFailure('Ranking appeals are not connected yet.');
  @override
  Future<CommunityPulse> getCommunityPulse(String district) async =>
      throw const ServerFailure('District totals are not connected yet.');
}
