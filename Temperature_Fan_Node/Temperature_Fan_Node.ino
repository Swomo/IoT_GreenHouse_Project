#include <DHT.h>

// Pin definitions
#define DHT_PIN 2          // DHT11 data pin
#define RELAY_PIN 7        // Relay control pin
#define DHT_TYPE DHT11     // DHT sensor type

// Temperature thresholds (in Celsius) - Adjusted for Malaysian climate
#define TEMP_THRESHOLD_ON 32.0   // Turn fan ON when temp exceeds this (excessive heat)
#define TEMP_THRESHOLD_OFF 29.0  // Turn fan OFF when temp drops below this (normal warm range)

// Initialize DHT sensor
DHT dht(DHT_PIN, DHT_TYPE);

// Variables
float temperature = 0.0;
float humidity = 0.0;
bool fanStatus = false;
unsigned long lastReading = 0;
const unsigned long readingInterval = 2000; // Read sensor every 2 seconds

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("Greenhouse Temperature Control System Starting...");
  
  // Initialize DHT sensor
  dht.begin();
  
  // Set relay pin as output
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // Start with fan OFF (relay inactive for active-LOW relay)
  
  Serial.println("System initialized successfully!");
  Serial.println("Temperature Thresholds:");
  Serial.print("Fan ON: "); Serial.print(TEMP_THRESHOLD_ON); Serial.println("°C");
  Serial.print("Fan OFF: "); Serial.print(TEMP_THRESHOLD_OFF); Serial.println("°C");
  Serial.println("----------------------------------------");
}

void loop() {
  // Check if it's time to read the sensor
  if (millis() - lastReading >= readingInterval) {
    readSensorData();
    controlFan();
    displayStatus();
    lastReading = millis();
  }
}

void readSensorData() {
  // Read temperature and humidity
  humidity = dht.readHumidity();
  temperature = dht.readTemperature();
  
  // Check if readings are valid
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("ERROR: Failed to read from DHT sensor!");
    return;
  }
}

void controlFan() {
  // Hysteresis control to prevent rapid on/off switching
  if (!fanStatus && temperature > TEMP_THRESHOLD_ON) {
    // Turn fan ON
    digitalWrite(RELAY_PIN, LOW);  // LOW activates relay for active-LOW modules
    fanStatus = true;
    Serial.println(">>> FAN TURNED ON - Temperature too high!");
  }
  else if (fanStatus && temperature < TEMP_THRESHOLD_OFF) {
    // Turn fan OFF
    digitalWrite(RELAY_PIN, HIGH); // HIGH deactivates relay for active-LOW modules
    fanStatus = false;
    Serial.println(">>> FAN TURNED OFF - Temperature normalized");
  }
}

void displayStatus() {
  Serial.print("Temp: ");
  Serial.print(temperature, 1);
  Serial.print("°C | Humidity: ");
  Serial.print(humidity, 1);
  Serial.print("% | Fan: ");
  Serial.println(fanStatus ? "ON" : "OFF");
}
