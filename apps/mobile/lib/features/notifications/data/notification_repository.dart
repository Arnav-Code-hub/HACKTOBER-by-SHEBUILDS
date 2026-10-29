import '../../../core/network/api_client.dart';
import '../domain/notification_item.dart';

class NotificationRepository {
  NotificationRepository(this._api);

  final ApiClient _api;

  Future<NotificationPage> load() async {
    final payload = await _api.get('notifications');
    if (payload is! Map<String, dynamic> || payload['items'] is! List) {
      throw const FormatException('The server returned an invalid inbox.');
    }
    final items = (payload['items'] as List)
        .map(NotificationItem.fromJson)
        .toList(growable: false);
    final unreadCount = payload['unread_count'];
    return NotificationPage(
      items: items,
      unreadCount: unreadCount is int ? unreadCount : 0,
    );
  }

  Future<void> markRead(String id) async {
    await _api.post(
      'notifications/${Uri.encodeComponent(id)}/read',
      const <String, Object?>{},
    );
  }
}

class NotificationPage {
  const NotificationPage({required this.items, required this.unreadCount});

  static const empty = NotificationPage(
    items: <NotificationItem>[],
    unreadCount: 0,
  );

  final List<NotificationItem> items;
  final int unreadCount;
}
