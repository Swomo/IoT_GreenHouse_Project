/*
 * IoT Greenhouse - Node 1: Enhanced Soil Health System with Command Interface
 * 
 * This system monitors 3 soil moisture sensors and automatically controls
 * a servo motor to direct water flow to the section that needs it most.
 * 
 * NEW: Accepts commands from Raspberry Pi for manual watering control
 * 
 * Commands accepted:
 * - WATER_SECTOR_1_15  (water sector 1 for 15 seconds)
 * - WATER_SECTOR_2_10  (water sector 2 for 10 seconds) 
 * - WATER_SECTOR_3_20  (water sector 3 for 20 seconds)
 * - STOP_MANUAL        (stop any manual watering)
 * - STATUS             (report current status)
 * 
 * Hardware Requirements:
 * - Arduino Uno/Nano
 * - 3x Soil Moisture Sensors
 * - 1x Servo Motor (SG90 or similar) - represents water flow direction control
 * - 1x LED (status indicator)
 */

#include <Servo.h>

// Pin Definitions
const int SOIL_PIN_1 = A0;
const int SOIL_PIN_2 = A1;
const int SOIL_PIN_3 = A2;
const int SERVO_PIN = 9;
const int LED_PIN = 13;

// Servo object
Servo waterDirectionServo;

// Servo positions
const int SERVO_10_OCLOCK = 60;   // Sector 1
const int SERVO_2_OCLOCK = 120;   // Sector 2
const int SERVO_6_OCLOCK = 180;   // Sector 3
const int SERVO_NEUTRAL = 0;

// Thresholds
const int DRY_THRESHOLD = 700;
const int WET_THRESHOLD = 300;

// Timing
unsigned long lastReading = 0;
const unsigned long READING_INTERVAL = 5000;

// System state
enum SystemState {
  MONITORING,
  WATERING,
  MANUAL_WATERING,
  DRAINING,
  ALL_DRY,
  ALL_OVERWATERED,
  OSCILLATING
};

SystemState currentState = MONITORING;
bool systemActive = true;
int soilValues[3] = {0, 0, 0};

// Manual watering control (NEW)
bool manualWateringActive = false;
unsigned long manualWateringStart = 0;
int manualWateringDuration = 0;
int manualWateringSector = 0;

// Growth tracking
int plantGrowthCounter = 0;
const int GROWTH_THRESHOLD = 100;

void setup() {
  Serial.begin(9600);
  Serial.println("=== IoT Greenhouse Node 1: Enhanced Soil Health System ===");
  Serial.println("Command Interface Ready - Listening for Pi commands");

  pinMode(LED_PIN, OUTPUT);
  waterDirectionServo.attach(SERVO_PIN);
  waterDirectionServo.write(SERVO_NEUTRAL);
  digitalWrite(LED_PIN, LOW);

  delay(2000);
  Serial.println(">>> SYSTEM_READY");
}

void loop() {
  // Handle commands from Raspberry Pi (NEW)
  handleSerialCommands();
  
  // Check manual watering timeout (NEW)
  checkManualWatering();
  
  // Regular sensor reading and automation
  if (millis() - lastReading >= READING_INTERVAL) {
    readSoilSensors();
    displaySensorReadings();

    // Only run automatic control if not in manual mode (MODIFIED)
    if (systemActive && !manualWateringActive) {
      SystemState newState = determineSystemState();
      if (newState != currentState) {
        currentState = newState;
        controlServo();
      }

      if (currentState == OSCILLATING) {
        handleOscillation();
      }
    }

    lastReading = millis();
    plantGrowthCounter++;
  }

  updateStatusLED();
  delay(100);
}

// NEW: Handle commands from Raspberry Pi
void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.length() == 0) return;
    
    // Parse watering commands: WATER_SECTOR_X_Y
    if (command.startsWith("WATER_SECTOR_")) {
      parseWateringCommand(command);
    }
    // Stop manual watering
    else if (command == "STOP_MANUAL") {
      stopManualWatering();
      Serial.println(">>> MANUAL_WATERING_STOPPED");
    }
    // Status request
    else if (command == "STATUS") {
      reportDetailedStatus();
    }
    // Legacy commands
    else if (command == "RESET") {
      currentState = MONITORING;
      waterDirectionServo.write(SERVO_NEUTRAL);
      manualWateringActive = false;
      Serial.println(">>> SYSTEM_RESET");
    } else if (command == "OFF") {
      systemActive = false;
      Serial.println(">>> SYSTEM_DISABLED");
    } else if (command == "ON") {
      systemActive = true;
      Serial.println(">>> SYSTEM_ENABLED");
    } else {
      Serial.println(">>> UNKNOWN_COMMAND: " + command);
    }
  }
}

// NEW: Parse watering command from Pi
void parseWateringCommand(String command) {
  // Parse: WATER_SECTOR_1_15
  int firstUnderscore = command.indexOf('_', 13);  // After "WATER_SECTOR_"
  int secondUnderscore = command.indexOf('_', firstUnderscore + 1);
  
  if (firstUnderscore > 0 && secondUnderscore > 0) {
    int sector = command.substring(13, firstUnderscore).toInt();
    int duration = command.substring(secondUnderscore + 1).toInt();
    
    if (sector >= 1 && sector <= 3 && duration > 0 && duration <= 60) {
      startManualWatering(sector, duration);
      Serial.println(">>> MANUAL_WATERING_STARTED: Sector " + String(sector) + " for " + String(duration) + "s");
    } else {
      Serial.println(">>> INVALID_PARAMETERS: Sector must be 1-3, Duration 1-60s");
    }
  } else {
    Serial.println(">>> COMMAND_FORMAT_ERROR: Use WATER_SECTOR_X_Y");
  }
}

// NEW: Start manual watering
void startManualWatering(int sector, int duration) {
  // Stop any current automation
  manualWateringActive = true;
  manualWateringSector = sector;
  manualWateringDuration = duration;
  manualWateringStart = millis();
  currentState = MANUAL_WATERING;
  
  // Position servo for the specified sector
  int servoPosition = SERVO_NEUTRAL;
  switch (sector) {
    case 1: servoPosition = SERVO_10_OCLOCK; break;
    case 2: servoPosition = SERVO_2_OCLOCK; break;
    case 3: servoPosition = SERVO_6_OCLOCK; break;
  }
  
  waterDirectionServo.write(servoPosition);
  digitalWrite(LED_PIN, HIGH);
  
  Serial.println(">>> SERVO_POSITION: " + String(servoPosition) + " degrees");
}

// NEW: Check manual watering timeout
void checkManualWatering() {
  if (manualWateringActive) {
    unsigned long elapsed = millis() - manualWateringStart;
    
    if (elapsed >= (manualWateringDuration * 1000)) {
      stopManualWatering();
      Serial.println(">>> MANUAL_WATERING_COMPLETED");
    }
  }
}

// NEW: Stop manual watering
void stopManualWatering() {
  manualWateringActive = false;
  waterDirectionServo.write(SERVO_NEUTRAL);
  digitalWrite(LED_PIN, LOW);
  currentState = MONITORING;
  
  Serial.println(">>> SERVO_POSITION: 0 degrees (NEUTRAL)");
}

// NEW: Detailed status report for Pi
void reportDetailedStatus() {
  Serial.println(">>> STATUS_REPORT_START");
  Serial.println(">>> SYSTEM_STATE: " + getStateString(currentState));
  Serial.println(">>> MANUAL_ACTIVE: " + String(manualWateringActive ? "true" : "false"));
  
  if (manualWateringActive) {
    unsigned long remaining = (manualWateringDuration * 1000) - (millis() - manualWateringStart);
    Serial.println(">>> MANUAL_REMAINING: " + String(remaining / 1000) + "s");
    Serial.println(">>> MANUAL_SECTOR: " + String(manualWateringSector));
  }
  
  Serial.println(">>> SOIL_VALUES: " + String(soilValues[0]) + "," + String(soilValues[1]) + "," + String(soilValues[2]));
  Serial.println(">>> STATUS_REPORT_END");
}

String getStateString(SystemState state) {
  switch (state) {
    case MONITORING: return "MONITORING";
    case WATERING: return "WATERING";
    case MANUAL_WATERING: return "MANUAL_WATERING";
    case DRAINING: return "DRAINING";
    case ALL_DRY: return "ALL_DRY";
    case ALL_OVERWATERED: return "ALL_OVERWATERED";
    case OSCILLATING: return "OSCILLATING";
    default: return "UNKNOWN";
  }
}

void readSoilSensors() {
  soilValues[0] = analogRead(SOIL_PIN_1);
  soilValues[1] = analogRead(SOIL_PIN_2);
  soilValues[2] = analogRead(SOIL_PIN_3);

  static int prevValues[3] = {0, 0, 0};
  for (int i = 0; i < 3; i++) {
    soilValues[i] = (soilValues[i] + prevValues[i]) / 2;
    prevValues[i] = soilValues[i];
  }
}

SystemState determineSystemState() {
  bool sensor1Dry = soilValues[0] > DRY_THRESHOLD;
  bool sensor2Dry = soilValues[1] > DRY_THRESHOLD;
  bool sensor3Dry = soilValues[2] > DRY_THRESHOLD;

  bool sensor1Overwatered = soilValues[0] < WET_THRESHOLD;
  bool sensor2Overwatered = soilValues[1] < WET_THRESHOLD;
  bool sensor3Overwatered = soilValues[2] < WET_THRESHOLD;

  if (sensor1Dry && sensor2Dry && sensor3Dry) return ALL_DRY;
  if (sensor1Overwatered && sensor2Overwatered && sensor3Overwatered) return ALL_OVERWATERED;
  if (sensor1Dry || sensor2Dry || sensor3Dry) return WATERING;
  if (sensor1Overwatered || sensor2Overwatered || sensor3Overwatered) return DRAINING;

  return MONITORING;
}

void controlServo() {
  int targetPosition = SERVO_NEUTRAL;
  String action = "MONITORING";

  switch (currentState) {
    case ALL_DRY:
      Serial.println(">>> ALL DRY - AUTO WATERING CYCLE");
      waterDirectionServo.write(SERVO_10_OCLOCK);
      delay(3000);
      waterDirectionServo.write(SERVO_2_OCLOCK);
      delay(3000);
      waterDirectionServo.write(SERVO_6_OCLOCK);
      delay(3000);
      waterDirectionServo.write(SERVO_NEUTRAL);
      Serial.println(">>> AUTO_WATERING_CYCLE_COMPLETE");
      return;

    case WATERING:
      if (soilValues[0] > DRY_THRESHOLD) {
        targetPosition = SERVO_10_OCLOCK;
        action = "AUTO_WATERING_SECTOR_1";
      } else if (soilValues[1] > DRY_THRESHOLD) {
        targetPosition = SERVO_2_OCLOCK;
        action = "AUTO_WATERING_SECTOR_2";
      } else if (soilValues[2] > DRY_THRESHOLD) {
        targetPosition = SERVO_6_OCLOCK;
        action = "AUTO_WATERING_SECTOR_3";
      }
      break;

    case MONITORING:
    default:
      targetPosition = SERVO_NEUTRAL;
      action = "MONITORING";
      break;
  }

  waterDirectionServo.write(targetPosition);
  Serial.println(">>> " + action);
}

void handleOscillation() {
  // Simplified oscillation handling
  static unsigned long lastOscillateUpdate = 0;
  static int oscillatePosition = 90;
  static bool oscillateDirection = true;

  if (millis() - lastOscillateUpdate > 1000) {
    if (oscillateDirection) {
      oscillatePosition += 30;
      if (oscillatePosition >= 180) {
        oscillatePosition = 180;
        oscillateDirection = false;
      }
    } else {
      oscillatePosition -= 30;
      if (oscillatePosition <= 0) {
        oscillatePosition = 0;
        oscillateDirection = true;
      }
    }

    waterDirectionServo.write(oscillatePosition);
    lastOscillateUpdate = millis();
  }
}

void displaySensorReadings() {
  Serial.print("Soil Moisture - A: ");
  Serial.print(soilValues[0]);
  printMoistureStatus(soilValues[0]);
  Serial.print(" | B: ");
  Serial.print(soilValues[1]);
  printMoistureStatus(soilValues[1]);
  Serial.print(" | C: ");
  Serial.print(soilValues[2]);
  printMoistureStatus(soilValues[2]);
  Serial.print(" | State: ");
  Serial.print(getStateString(currentState));
  
  if (manualWateringActive) {
    unsigned long remaining = (manualWateringDuration * 1000) - (millis() - manualWateringStart);
    Serial.print(" | Manual: " + String(remaining / 1000) + "s");
  }
  
  Serial.println();
}

void printMoistureStatus(int value) {
  if (value > DRY_THRESHOLD) {
    Serial.print(" (DRY)");
  } else if (value < WET_THRESHOLD) {
    Serial.print(" (WET)");
  } else {
    Serial.print(" (OK)");
  }
}

void updateStatusLED() {
  // LED behavior based on state
  if (manualWateringActive) {
    // Fast blink during manual watering
    digitalWrite(LED_PIN, (millis() / 250) % 2);
  } else if (currentState == WATERING) {
    // Slow blink during auto watering
    digitalWrite(LED_PIN, (millis() / 500) % 2);
  } else if (currentState != MONITORING) {
    // Solid on for other states
    digitalWrite(LED_PIN, HIGH);
  } else {
    // Off when monitoring
    digitalWrite(LED_PIN, LOW);
  }
}