class Weather {
  final String cityName;
  final double latitude;
  final double longitude;
  final DateTime updatedAtUtc;
  final int timezoneOffsetSeconds;
  final double temperature;
  final double feelsLike;
  final String description;
  final String weatherMain;
  final String iconCode;
  final double rainVolume;
  final int humidity;
  final double windSpeed;

  Weather({
    required this.cityName,
    required this.latitude,
    required this.longitude,
    required this.updatedAtUtc,
    required this.timezoneOffsetSeconds,
    required this.temperature,
    required this.feelsLike,
    required this.description,
    required this.weatherMain,
    required this.iconCode,
    required this.rainVolume,
    required this.humidity,
    required this.windSpeed,
  });

  factory Weather.fromJson(Map<String, dynamic> json) {
    final cityName = json['name'] as String? ?? '';
    final coordinates = json['coord'] as Map<String, dynamic>? ?? {};
    final main = json['main'] as Map<String, dynamic>? ?? {};
    final weatherList = json['weather'] as List<dynamic>? ?? <dynamic>[];
    final weather = weatherList.isNotEmpty
        ? weatherList.first as Map<String, dynamic>
        : <String, dynamic>{};
    final rain = json['rain'] as Map<String, dynamic>?;
    final wind = json['wind'] as Map<String, dynamic>? ?? {};
    final timestamp = (json['dt'] as num?)?.toInt() ?? 0;

    return Weather(
      cityName: cityName,
      latitude: (coordinates['lat'] as num?)?.toDouble() ?? 0.0,
      longitude: (coordinates['lon'] as num?)?.toDouble() ?? 0.0,
      updatedAtUtc: DateTime.fromMillisecondsSinceEpoch(
        timestamp * 1000,
        isUtc: true,
      ),
      timezoneOffsetSeconds: (json['timezone'] as num?)?.toInt() ?? 0,
      temperature: (main['temp'] as num?)?.toDouble() ?? 0.0,
      feelsLike: (main['feels_like'] as num?)?.toDouble() ?? 0.0,
      description: weather['description'] as String? ?? '',
      weatherMain: weather['main'] as String? ?? '',
      iconCode: weather['icon'] as String? ?? '01d',
      rainVolume: (rain?['1h'] as num?)?.toDouble() ?? 0.0,
      humidity: (main['humidity'] as num?)?.toInt() ?? 0,
      windSpeed: (wind['speed'] as num?)?.toDouble() ?? 0.0,
    );
  }

  String get temperatureText => '${temperature.round()}℃';

  String get feelsLikeText => '${feelsLike.round()}℃';

  String get coordinatesText =>
      '${latitude.toStringAsFixed(4)}, ${longitude.toStringAsFixed(4)}';

  String get updatedAtText {
    final localTime = updatedAtUtc.add(
      Duration(seconds: timezoneOffsetSeconds),
    );
    return '${localTime.year}/${localTime.month.toString().padLeft(2, '0')}/${localTime.day.toString().padLeft(2, '0')} ${localTime.hour.toString().padLeft(2, '0')}:${localTime.minute.toString().padLeft(2, '0')}:${localTime.second.toString().padLeft(2, '0')} (API地点の現地時刻)';
  }

  String get timezoneText {
    final sign = timezoneOffsetSeconds >= 0 ? '+' : '-';
    final absoluteOffset = timezoneOffsetSeconds.abs();
    final hours = (absoluteOffset ~/ 3600).toString().padLeft(2, '0');
    final minutes = ((absoluteOffset % 3600) ~/ 60).toString().padLeft(2, '0');
    return 'UTC$sign$hours:$minutes';
  }

  String get rainText =>
      rainVolume > 0 ? '${rainVolume.toStringAsFixed(1)} mm' : '0 mm';

  String get windSpeedText => '${windSpeed.toStringAsFixed(1)} m/s';
}
