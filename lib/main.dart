import 'package:flutter/material.dart';

void main() {
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

class WeatherPage extends StatelessWidget {
  const WeatherPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('天気予報')),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              '春日部市',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 20),
            Icon(Icons.wb_sunny, size: 100),
            SizedBox(height: 20),
            Text(
              '30℃',
              style: TextStyle(fontSize: 56, fontWeight: FontWeight.bold),
            ),
            Text('晴れ', style: TextStyle(fontSize: 24)),
            SizedBox(height: 30),
            Text('降水確率 20%', style: TextStyle(fontSize: 18)),
          ],
        ),
      ),
    );
  }
}
