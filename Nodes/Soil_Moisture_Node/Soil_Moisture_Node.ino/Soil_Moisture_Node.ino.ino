/*
 * IoT Greenhouse - Node 1: Soil Health Monitoring and Watering System
 * 
 * This system monitors 3 soil moisture sensors and automatically controls
 * a servo motor to direct water flow to the section that needs it most.
 * 
 * Hardware Requirements:
 * - Arduino Uno/Nano
 * - 3x Soil Moisture Sensors
 * - 1x Servo Motor (SG90 or similar) - represents water flow direction control
 * - 1x LED (status indicator)
 * 
 * Soil Moisture Value Ranges (Verified):
 * 700 - 1023: VERY DRY (little to no moisture) - NEEDS WATER
 * 300 - 700:  MOIST/OPTIMAL (good growing conditions) - STOP WATERING
 * 0 - 300:    VERY WET (too much water) - DRAINAGE NEEDED
 * 
 * Author: IoT Greenhouse Team
 * Date: 2025
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
const int SERVO_10_OCLOCK = 60;
const int SERVO_12_OCLOCK = 90;
const int SERVO_2_OCLOCK = 120;
const int SERVO_4_OCLOCK = 150;
const int SERVO_6_OCLOCK = 180;
const int SERVO_8_OCLOCK = 30;
const int SERVO_7_OCLOCK = 210;
const int SERVO_NEUTRAL = 0;

// Thresholds
const int DRY_THRESHOLD = 700;
const int WET_THRESHOLD = 300;
const int OPTIMAL_RANGE_LOW = 300;
const int OPTIMAL_RANGE_HIGH = 700;

// Timing
unsigned long lastReading = 0;
unsigned long lastWatering = 0;
const unsigned long READING_INTERVAL = 5000;
const unsigned long WATERING_DURATION = 10000;
const unsigned long WATERING_COOLDOWN = 30000;

// System state
enum SystemState {
  MONITORING,
  WATERING,
  DRAINING,
  ALL_DRY,
  ALL_OVERWATERED,
  OSCILLATING
};

SystemState currentState = MONITORING;
bool systemActive = true;
int soilValues[3] = {0, 0, 0};
unsigned long oscillateStartTime = 0;
bool oscillateDirection = true;
int oscillatePosition = 90;

// Growth tracking
int plantGrowthCounter = 0;
const int GROWTH_THRESHOLD = 100;

void setup() {
  Serial.begin(9600);
  Serial.println("=== IoT Greenhouse Node 1: Soil Health System ===");

  pinMode(LED_PIN, OUTPUT);
  waterDirectionServo.attach(SERVO_PIN);
  waterDirectionServo.write(SERVO_NEUTRAL);
  digitalWrite(LED_PIN, LOW);

  delay(2000);
}

void loop() {
  if (millis() - lastReading >= READING_INTERVAL) {
    readSoilSensors();
    displaySensorReadings();

    if (systemActive) {
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

  handleSystemState();
  handleSerialCommands();
  updateStatusLED();
  delay(100);
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
      Serial.println(">>> ALL DRY - ROTATING TO EACH SENSOR");
      waterDirectionServo.write(SERVO_10_OCLOCK);
      Serial.println(">>> A is DRY - 10 O'CLOCK");
      delay(3000);
      waterDirectionServo.write(SERVO_2_OCLOCK);
      Serial.println(">>> B is DRY - 2 O'CLOCK");
      delay(3000);
      waterDirectionServo.write(SERVO_6_OCLOCK);
      Serial.println(">>> C is DRY - 6 O'CLOCK");
      delay(3000);
      waterDirectionServo.write(SERVO_NEUTRAL);
      Serial.println(">>> ALL DRY - DONE CYCLE, RETURNING TO NEUTRAL");
      return;

    case ALL_OVERWATERED:
      currentState = OSCILLATING;
      oscillateStartTime = millis();
      oscillatePosition = 90;
      action = "ALL OVERWATERED - STARTING OSCILLATION";
      Serial.println(">>> " + action);
      return;

    case WATERING:
      if (soilValues[0] > DRY_THRESHOLD) {
        targetPosition = SERVO_10_OCLOCK;
        action = "SENSOR 1 DRY - 10 O'CLOCK";
      } else if (soilValues[1] > DRY_THRESHOLD) {
        targetPosition = SERVO_2_OCLOCK;
        action = "SENSOR 2 DRY - 2 O'CLOCK";
      } else if (soilValues[2] > DRY_THRESHOLD) {
        targetPosition = SERVO_6_OCLOCK;
        action = "SENSOR 3 DRY - 6 O'CLOCK";
      }
      break;

    case DRAINING:
      if (soilValues[0] < WET_THRESHOLD) {
        targetPosition = SERVO_4_OCLOCK;
        action = "SENSOR 1 OVERWATERED - 4 O'CLOCK (150°)";
      } else if (soilValues[1] < WET_THRESHOLD) {
        targetPosition = SERVO_8_OCLOCK;
        action = "SENSOR 2 OVERWATERED - 8 O'CLOCK (30°)";
      } else if (soilValues[2] < WET_THRESHOLD) {
        targetPosition = SERVO_7_OCLOCK;
        action = "SENSOR 3 OVERWATERED - 7 O'CLOCK (210°)";
      }
      break;

    case MONITORING:
    default:
      targetPosition = SERVO_NEUTRAL;
      action = "ALL OPTIMAL - NEUTRAL (0°)";
      break;
  }

  waterDirectionServo.write(targetPosition);
  Serial.println(">>> " + action);
}

void handleOscillation() {
  static unsigned long lastOscillateUpdate = 0;

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
    Serial.print(">>> OSCILLATING - Position: ");
    Serial.print(oscillatePosition);
    Serial.println("°");
    lastOscillateUpdate = millis();
  }

  if (!(soilValues[0] < WET_THRESHOLD && soilValues[1] < WET_THRESHOLD && soilValues[2] < WET_THRESHOLD)) {
    currentState = MONITORING;
    Serial.println(">>> OSCILLATION STOPPED - Sensors improved");
  }
}

void handleSystemState() {
  // Optional additional logic
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
  printSystemState();

  if (plantGrowthCounter >= GROWTH_THRESHOLD) {
    Serial.print(" | Growth Cycle: ");
    Serial.print(plantGrowthCounter / GROWTH_THRESHOLD);
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

void printSystemState() {
  switch (currentState) {
    case MONITORING: Serial.print("MONITORING"); break;
    case WATERING: Serial.print("WATERING"); break;
    case DRAINING: Serial.print("DRAINING"); break;
    case ALL_DRY: Serial.print("ALL DRY"); break;
    case ALL_OVERWATERED: Serial.print("ALL OVERWATERED"); break;
    case OSCILLATING: Serial.print("OSCILLATING"); break;
    default: Serial.print("UNKNOWN"); break;
  }
}

void updateStatusLED() {
  digitalWrite(LED_PIN, (currentState != MONITORING));
}

void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "STATUS") {
      displaySensorReadings();
    } else if (command == "RESET") {
      currentState = MONITORING;
      waterDirectionServo.write(SERVO_NEUTRAL);
      Serial.println(">>> SYSTEM RESET");
    } else if (command == "OFF") {
      systemActive = false;
      Serial.println(">>> SYSTEM DISABLED");
    } else if (command == "ON") {
      systemActive = true;
      Serial.println(">>> SYSTEM ENABLED");
    } else {
      Serial.println(">>> UNKNOWN COMMAND");
    }
  }
}
