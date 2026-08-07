class Weather {
  final String cityName;
  final double temperature;
  final String description;
  final String iconCode;
  final double rainVolume;
  final int humidity;

  Weather({
    required this.cityName,
    required this.temperature,
    required this.description,
    required this.iconCode,
    required this.rainVolume,
    required this.humidity,
  });

  factory Weather.fromJson(Map<String, dynamic> json) {
    final cityName = json['name'] as String? ?? '';
    final main = json['main'] as Map<String, dynamic>? ?? {};
    final weatherList = json['weather'] as List<dynamic>? ?? <dynamic>[];
    final weather = weatherList.isNotEmpty ? weatherList.first as Map<String, dynamic> : <String, dynamic>{};
    final rain = json['rain'] as Map<String, dynamic>?;

    return Weather(
      cityName: cityName,
      temperature: (main['temp'] as num?)?.toDouble() ?? 0.0,
      description: weather['description'] as String? ?? '',
      iconCode: weather['icon'] as String? ?? '01d',
      rainVolume: (rain?['1h'] as num?)?.toDouble() ?? 0.0,
      humidity: (main['humidity'] as num?)?.toInt() ?? 0,
    );
  }

  String get temperatureText => '${temperature.round()}℃';

  String get rainText => rainVolume > 0 ? '${rainVolume.toStringAsFixed(1)} mm' : '0 mm';
}
