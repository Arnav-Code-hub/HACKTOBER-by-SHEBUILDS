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

  @override
  Stream<List<Demand>> watchMyDemands(String uid) async* {
    final data = jsonObject(
      await _api.get('reports', query: <String, String>{'mine': 'true'}),
    );
    final items = data['items'];
    if (items is! List) {
      throw const ServerFailure('The API returned an invalid report list.');
    }
    yield items.map(demandFromJson).toList();
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
  Future<DemandCluster> joinCluster(String clusterId, String uid) async =>
      throw const ServerFailure('Joining a cluster is not connected yet.');
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
