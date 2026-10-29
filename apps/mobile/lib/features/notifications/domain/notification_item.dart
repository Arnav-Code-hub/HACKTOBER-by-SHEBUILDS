class NotificationItem {
  const NotificationItem({
    required this.id,
    required this.title,
    required this.body,
    required this.createdAt,
    required this.readAt,
  });

  final String id;
  final String title;
  final String body;
  final DateTime createdAt;
  final DateTime? readAt;

  bool get isRead => readAt != null;

  factory NotificationItem.fromJson(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Invalid notification item.');
    }
    final id = value['id'];
    final title = value['title'];
    final body = value['body'];
    final createdAt = value['created_at'];
    final readAt = value['read_at'];
    if (id is! String ||
        title is! String ||
        body is! String ||
        createdAt is! String) {
      throw const FormatException('Incomplete notification item.');
    }
    return NotificationItem(
      id: id,
      title: title,
      body: body,
      createdAt: DateTime.parse(createdAt),
      readAt: readAt is String ? DateTime.tryParse(readAt) : null,
    );
  }
}
