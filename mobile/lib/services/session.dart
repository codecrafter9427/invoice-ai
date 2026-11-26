import '../api/client.dart';

/// In-memory demo session shared across screens.
class Session {
  Session._();
  static final Session instance = Session._();

  final ApiClient api = ApiClient();
  String? email;
  String? role;

  bool get isLoggedIn => api.accessToken != null;

  void clear() {
    api.accessToken = null;
    email = null;
    role = null;
  }
}
