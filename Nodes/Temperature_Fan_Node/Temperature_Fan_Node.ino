/*
 * IoT Greenhouse - Node 2: Enhanced Temperature Control System with Command Interface
 * 
 * This system monitors temperature/humidity and controls a ventilation fan.
 * 
 * NEW: Accepts commands from Raspberry Pi for manual fan control
 * 
 * Commands accepted:
 * - FAN_ON       (turn fan on manually)
 * - FAN_OFF      (turn fan off manually) 
 * - FAN_AUTO     (return to automatic mode)
 * - STATUS       (report current status)
 * 
 * Hardware Requirements:
 * - Arduino Uno/Nano
 * - DHT11 temperature/humidity sensor
 * - Relay module for fan control
 * - Ventilation fan
 */

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

// NEW: Manual control variables
enum ControlMode {
  AUTO_MODE,
  MANUAL_ON,
  MANUAL_OFF
};

ControlMode currentMode = AUTO_MODE;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("=== IoT Greenhouse Node 2: Enhanced Temperature Control ===");
  Serial.println("Command Interface Ready - Listening for Pi commands");
  
  // Initialize DHT sensor
  dht.begin();
  
  // Set relay pin as output
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, HIGH); // Start with fan OFF (relay inactive for active-LOW relay)
  
  Serial.println("System initialized successfully!");
  Serial.println("Temperature Thresholds:");
  Serial.print("Fan ON: "); Serial.print(TEMP_THRESHOLD_ON); Serial.println("°C");
  Serial.print("Fan OFF: "); Serial.print(TEMP_THRESHOLD_OFF); Serial.println("°C");
  Serial.println(">>> SYSTEM_READY");
  Serial.println("----------------------------------------");
}

void loop() {
  // Handle commands from Raspberry Pi (NEW)
  handleSerialCommands();
  
  // Check if it's time to read the sensor
  if (millis() - lastReading >= readingInterval) {
    readSensorData();
    controlFan();
    displayStatus();
    lastReading = millis();
  }
}

// NEW: Handle commands from Raspberry Pi
void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.length() == 0) return;
    
    if (command == "FAN_ON") {
      setManualFanControl(MANUAL_ON);
      Serial.println(">>> FAN_MANUAL_ON");
    }
    else if (command == "FAN_OFF") {
      setManualFanControl(MANUAL_OFF);
      Serial.println(">>> FAN_MANUAL_OFF");
    }
    else if (command == "FAN_AUTO") {
      setManualFanControl(AUTO_MODE);
      Serial.println(">>> FAN_AUTO_MODE");
    }
    else if (command == "STATUS") {
      reportDetailedStatus();
    }
    else {
      Serial.println(">>> UNKNOWN_COMMAND: " + command);
    }
  }
}

// NEW: Set manual fan control mode
void setManualFanControl(ControlMode mode) {
  currentMode = mode;
  
  switch (mode) {
    case MANUAL_ON:
      digitalWrite(RELAY_PIN, LOW);  // Turn fan ON
      fanStatus = true;
      Serial.println(">>> FAN_FORCED_ON");
      break;
      
    case MANUAL_OFF:
      digitalWrite(RELAY_PIN, HIGH); // Turn fan OFF
      fanStatus = false;
      Serial.println(">>> FAN_FORCED_OFF");
      break;
      
    case AUTO_MODE:
      Serial.println(">>> FAN_AUTO_MODE_ACTIVE");
      // Fan control will be handled by controlFan() function
      break;
  }
}

// NEW: Detailed status report for Pi
void reportDetailedStatus() {
  Serial.println(">>> STATUS_REPORT_START");
  Serial.println(">>> CONTROL_MODE: " + getModeString(currentMode));
  Serial.println(">>> FAN_STATUS: " + String(fanStatus ? "ON" : "OFF"));
  Serial.println(">>> TEMPERATURE: " + String(temperature, 1));
  Serial.println(">>> HUMIDITY: " + String(humidity, 1));
  Serial.println(">>> TEMP_THRESHOLD_ON: " + String(TEMP_THRESHOLD_ON));
  Serial.println(">>> TEMP_THRESHOLD_OFF: " + String(TEMP_THRESHOLD_OFF));
  Serial.println(">>> STATUS_REPORT_END");
}

String getModeString(ControlMode mode) {
  switch (mode) {
    case AUTO_MODE: return "AUTO";
    case MANUAL_ON: return "MANUAL_ON";
    case MANUAL_OFF: return "MANUAL_OFF";
    default: return "UNKNOWN";
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
  // Only use automatic control if in AUTO mode (MODIFIED)
  if (currentMode == AUTO_MODE) {
    // Hysteresis control to prevent rapid on/off switching
    if (!fanStatus && temperature > TEMP_THRESHOLD_ON) {
      // Turn fan ON
      digitalWrite(RELAY_PIN, LOW);  // LOW activates relay for active-LOW modules
      fanStatus = true;
      Serial.println(">>> FAN_AUTO_ON - Temperature too high!");
    }
    else if (fanStatus && temperature < TEMP_THRESHOLD_OFF) {
      // Turn fan OFF
      digitalWrite(RELAY_PIN, HIGH); // HIGH deactivates relay for active-LOW modules
      fanStatus = false;
      Serial.println(">>> FAN_AUTO_OFF - Temperature normalized");
    }
  }
  // In manual modes, fan state is already set by setManualFanControl()
}

void displayStatus() {
  Serial.print("Temp: ");
  Serial.print(temperature, 1);
  Serial.print("°C | Humidity: ");
  Serial.print(humidity, 1);
  Serial.print("% | Fan: ");
  Serial.print(fanStatus ? "ON" : "OFF");
  Serial.print(" | Mode: ");
  Serial.println(getModeString(currentMode));
}