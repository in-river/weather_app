import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

import 'models/weather.dart';

const String _openWeatherBaseUrl = 'api.openweathermap.org';
const String _openWeatherApiKeyName = 'OPENWEATHER_API_KEY';

class WeatherResponse {
  final Weather weather;
  final DateTime fetchedAt;

  WeatherResponse({required this.weather, required this.fetchedAt});

  String get fetchedAtText =>
      '${fetchedAt.year}/${fetchedAt.month.toString().padLeft(2, '0')}/${fetchedAt.day.toString().padLeft(2, '0')} ${fetchedAt.hour.toString().padLeft(2, '0')}:${fetchedAt.minute.toString().padLeft(2, '0')}:${fetchedAt.second.toString().padLeft(2, '0')}';
}

class WeatherApi {
  Future<WeatherResponse> fetchCurrentWeather(String city) async {
    final apiKey = dotenv.env[_openWeatherApiKeyName] ?? '';
    if (apiKey.isEmpty) {
      throw StateError(
        'OpenWeatherMap APIキーが設定されていません。プロジェクトルートに .env ファイルを作成し、$_openWeatherApiKeyName=YOUR_API_KEY を追加してください。',
      );
    }

    final uri = Uri.https(
      _openWeatherBaseUrl,
      '/data/2.5/weather',
      <String, String>{
        'q': city,
        'appid': apiKey,
        'units': 'metric',
        'lang': 'ja',
      },
    );

    final response = await http.get(uri);
    final fetchedAt = DateTime.now();
    if (response.statusCode != 200) {
      throw Exception('天気データの取得に失敗しました（HTTP ${response.statusCode}）。');
    }

    final jsonMap = jsonDecode(response.body) as Map<String, dynamic>;
    debugPrint(
      'OpenWeather Raw JSON:\n${const JsonEncoder.withIndent('  ').convert(jsonMap)}',
    );
    return WeatherResponse(
      weather: Weather.fromJson(jsonMap),
      fetchedAt: fetchedAt,
    );
  }
}
