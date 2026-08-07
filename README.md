# weather_app

A simple Flutter weather app that fetches current weather data from OpenWeatherMap and displays it on screen.

## Setup

1. Copy `.env.example` to `.env`.
2. Open `.env` and set `OPENWEATHER_API_KEY=YOUR_API_KEY`.
3. Run `flutter pub get`.
4. Launch the app with `flutter run`.

## Notes

- The app currently loads weather for `Kasukabe,JP`.
- The `.env` file is ignored by Git, so your APIキーは公開されません。
- If the API key is missing or the network request fails, the app shows an error message and allows retrying.

