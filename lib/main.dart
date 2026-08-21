import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'weather_api.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  runApp(const WeatherApp());
}

class WeatherApp extends StatelessWidget {
  const WeatherApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Weather App',
      theme: ThemeData(useMaterial3: true),
      home: const WeatherPage(),
    );
  }
}

class WeatherPage extends StatefulWidget {
  const WeatherPage({super.key});

  @override
  State<WeatherPage> createState() => _WeatherPageState();
}

class _WeatherPageState extends State<WeatherPage> {
  late Future<WeatherResponse> _weatherFuture;
  final WeatherApi _weatherApi = WeatherApi();
  static const String _cityQuery = 'Kasukabe,JP';

  @override
  void initState() {
    super.initState();
    _weatherFuture = _weatherApi.fetchCurrentWeather(_cityQuery);
  }

  void _refreshWeather() {
    setState(() {
      _weatherFuture = _weatherApi.fetchCurrentWeather(_cityQuery);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('天気予報')),
      body: FutureBuilder<WeatherResponse>(
        future: _weatherFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text(
                      '天気情報の取得中にエラーが発生しました。',
                      style: TextStyle(fontSize: 18),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      snapshot.error.toString(),
                      style: const TextStyle(color: Colors.red),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: _refreshWeather,
                      child: const Text('再読み込み'),
                    ),
                  ],
                ),
              ),
            );
          }

          final response = snapshot.data!;
          final weather = response.weather;
          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    weather.cityName,
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Icon(_weatherIcon(weather.iconCode), size: 100),
                  const SizedBox(height: 20),
                  Text(
                    weather.temperatureText,
                    style: const TextStyle(
                      fontSize: 56,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    weather.description,
                    style: const TextStyle(fontSize: 24),
                  ),
                  const SizedBox(height: 30),
                  Text(
                    '湿度 ${weather.humidity}%',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '降水量 ${weather.rainText}',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '体感温度 ${weather.feelsLikeText}',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '風速 ${weather.windSpeedText}',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '天気状態 ${weather.weatherMain} / ${weather.description}',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '取得地点 ${weather.coordinatesText}',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'API地点のタイムゾーン ${weather.timezoneText}',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'APIデータ更新時刻 ${weather.updatedAtText}',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'アプリ取得時刻 ${response.fetchedAtText} (端末時刻)',
                    style: const TextStyle(fontSize: 18),
                  ),
                  const SizedBox(height: 16),
                  const SizedBox(height: 8),
                  ElevatedButton(
                    onPressed: _refreshWeather,
                    child: const Text('最新情報に更新'),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  IconData _weatherIcon(String iconCode) {
    final code = iconCode.toLowerCase();
    if (code.startsWith('01')) {
      return Icons.wb_sunny;
    }
    if (code.startsWith('02') ||
        code.startsWith('03') ||
        code.startsWith('04')) {
      return Icons.cloud;
    }
    if (code.startsWith('09') || code.startsWith('10')) {
      return Icons.beach_access;
    }
    if (code.startsWith('11')) {
      return Icons.bolt;
    }
    if (code.startsWith('13')) {
      return Icons.ac_unit;
    }
    return Icons.cloud_queue;
  }
}
