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
const int SOIL_PIN_1 = A0;      // Soil moisture sensor 1 (Section A)
const int SOIL_PIN_2 = A1;      // Soil moisture sensor 2 (Section B)
const int SOIL_PIN_3 = A2;      // Soil moisture sensor 3 (Section C)
const int SERVO_PIN = 9;        // Servo control pin (PWM) - water flow direction
const int LED_PIN = 13;         // Status LED

// Servo object
Servo waterDirectionServo;

// Servo positions using clock analogy (Modified - No Conflicts)
const int SERVO_10_OCLOCK = 60;    // 10 o'clock - Sensor 1 dry
const int SERVO_12_OCLOCK = 90;    // 12 o'clock - Sensor 2 dry
const int SERVO_2_OCLOCK = 120;    // 2 o'clock - Sensor 3 dry
const int SERVO_4_OCLOCK = 150;    // 4 o'clock - Sensor 1 overwatered
const int SERVO_6_OCLOCK = 180;    // 6 o'clock - All sensors dry
const int SERVO_8_OCLOCK = 30;     // 8 o'clock - Sensor 2 overwatered
const int SERVO_7_OCLOCK = 210;    // 7 o'clock - Sensor 3 overwatered (extended range)
const int SERVO_NEUTRAL = 0;       // Neutral position (all optimal)

// Soil moisture thresholds (updated based on calibration)
const int DRY_THRESHOLD = 700;       // Above this value = dry soil (needs water)
const int WET_THRESHOLD = 300;       // Below this value = overwatered (needs drainage)
const int OPTIMAL_RANGE_LOW = 300;   // Lower bound of optimal range
const int OPTIMAL_RANGE_HIGH = 700;  // Upper bound of optimal range

// Timing variables
unsigned long lastReading = 0;
unsigned long lastWatering = 0;
const unsigned long READING_INTERVAL = 5000;    // Read sensors every 5 seconds
const unsigned long WATERING_DURATION = 10000;  // Water for 10 seconds
const unsigned long WATERING_COOLDOWN = 30000;  // Wait 30 seconds between waterings

// System state variables
enum SystemState {
  MONITORING,           // All sensors in optimal range
  WATERING,            // One or more sensors dry
  DRAINING,            // One or more sensors overwatered  
  ALL_DRY,             // All sensors dry
  ALL_OVERWATERED,     // All sensors overwatered
  OSCILLATING          // All overwatered - gentle oscillation instead of spinning
};

SystemState currentState = MONITORING;
bool systemActive = true;
int soilValues[3] = {0, 0, 0};
unsigned long oscillateStartTime = 0;
bool oscillateDirection = true;
int oscillatePosition = 90;

// Plant growth tracking
int plantGrowthCounter = 0;
const int GROWTH_THRESHOLD = 100; // Number of readings before considering growth

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("=== IoT Greenhouse Node 1: Soil Health System ===");
  Serial.println("Initializing system...");
  
  // Initialize pins
  pinMode(LED_PIN, OUTPUT);
  
  // Initialize servo (represents water flow direction control)
  waterDirectionServo.attach(SERVO_PIN);
  waterDirectionServo.write(SERVO_NEUTRAL);
  
  // Turn off LED initially
  digitalWrite(LED_PIN, LOW);
  
  Serial.println("System initialized successfully!");
  Serial.println("Soil Moisture Thresholds (Calibrated):");
  Serial.print("Dry Threshold: >"); Serial.println(DRY_THRESHOLD);
  Serial.print("Optimal Range: "); Serial.print(OPTIMAL_RANGE_LOW); 
  Serial.print(" - "); Serial.println(OPTIMAL_RANGE_HIGH);
  Serial.print("Overwatered: <"); Serial.println(WET_THRESHOLD);
  Serial.println("Monitoring soil moisture levels...");
  Serial.println("=========================================");
  
  delay(2000); // Allow system to stabilize
}

void loop() {
  // Read sensors at regular intervals
  if (millis() - lastReading >= READING_INTERVAL) {
    readSoilSensors();
    displaySensorReadings();
    
    if (systemActive) {
      SystemState newState = determineSystemState();
      if (newState != currentState) {
        currentState = newState;
        controlServo();
      }
      
      // Handle gentle oscillation for all overwatered
      if (currentState == OSCILLATING) {
        handleOscillation();
      }
    }
    
    lastReading = millis();
    plantGrowthCounter++;
  }
  
  // Handle system state changes
  handleSystemState();
  
  // Handle serial commands
  handleSerialCommands();
  
  // Update status LED
  updateStatusLED();
  
  delay(100); // Small delay for stability
}

void readSoilSensors() {
  soilValues[0] = analogRead(SOIL_PIN_1);
  soilValues[1] = analogRead(SOIL_PIN_2);
  soilValues[2] = analogRead(SOIL_PIN_3);
  
  // Simple filtering to reduce noise
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
  
  // Check for all dry condition first
  if (sensor1Dry && sensor2Dry && sensor3Dry) {
    return ALL_DRY;
  }
  
  // Check for all overwatered condition
  if (sensor1Overwatered && sensor2Overwatered && sensor3Overwatered) {
    return ALL_OVERWATERED;
  }
  
  // Check for any dry sensors (priority: individual dry sensors)
  if (sensor1Dry || sensor2Dry || sensor3Dry) {
    return WATERING;
  }
  
  // Check for any overwatered sensors
  if (sensor1Overwatered || sensor2Overwatered || sensor3Overwatered) {
    return DRAINING;
  }
  
  // All sensors in optimal range
  return MONITORING;
}

void controlServo() {
  int targetPosition = SERVO_NEUTRAL;
  String action = "MONITORING";
  
  switch (currentState) {
    case ALL_DRY:
      targetPosition = SERVO_6_OCLOCK;
      action = "ALL DRY - 6 O'CLOCK (180°)";
      break;
      
    case ALL_OVERWATERED:
      // Start gentle oscillation instead of spinning
      currentState = OSCILLATING;
      oscillateStartTime = millis();
      oscillatePosition = 90; // Start from center
      action = "ALL OVERWATERED - STARTING OSCILLATION";
      Serial.println(">>> " + action);
      return; // Don't set position, start oscillating instead
      
    case WATERING:
      // Priority system for dry sensors (first detected takes priority)
      if (soilValues[0] > DRY_THRESHOLD) {
        targetPosition = SERVO_10_OCLOCK;
        action = "SENSOR 1 DRY - 10 O'CLOCK (60°)";
      } else if (soilValues[1] > DRY_THRESHOLD) {
        targetPosition = SERVO_12_OCLOCK;
        action = "SENSOR 2 DRY - 12 O'CLOCK (90°)";
      } else if (soilValues[2] > DRY_THRESHOLD) {
        targetPosition = SERVO_2_OCLOCK;
        action = "SENSOR 3 DRY - 2 O'CLOCK (120°)";
      }
      break;
      
    case DRAINING:
      // Priority system for overwatered sensors (first detected takes priority)
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
  // Gentle back-and-forth oscillation instead of continuous spinning
  static unsigned long lastOscillateUpdate = 0;
  
  if (millis() - lastOscillateUpdate > 1000) { // Update every 1 second for gentle movement
    if (oscillateDirection) {
      oscillatePosition += 30; // Move 30 degrees clockwise
      if (oscillatePosition >= 180) {
        oscillatePosition = 180;
        oscillateDirection = false; // Change direction
      }
    } else {
      oscillatePosition -= 30; // Move 30 degrees counter-clockwise
      if (oscillatePosition <= 0) {
        oscillatePosition = 0;
        oscillateDirection = true; // Change direction
      }
    }
    
    waterDirectionServo.write(oscillatePosition);
    Serial.print(">>> OSCILLATING - Position: ");
    Serial.print(oscillatePosition);
    Serial.println("°");
    lastOscillateUpdate = millis();
  }
  
  // Check if we should stop oscillating (sensors no longer all overwatered)
  if (!(soilValues[0] < WET_THRESHOLD && soilValues[1] < WET_THRESHOLD && soilValues[2] < WET_THRESHOLD)) {
    currentState = MONITORING; // Will be re-evaluated in next cycle
    Serial.println(">>> OSCILLATION STOPPED - Sensors improved");
  }
}

void handleSystemState() {
  // This function can be used for additional state-specific logic if needed
  // Currently, main logic is handled in the main loop
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
  
  // Display plant growth estimation
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
  }
}

void updateStatusLED() {
  switch (currentState) {
    case WATERING:
    case DRAINING:
      // Blink LED when taking action
      digitalWrite(LED_PIN, (millis() / 500) % 2);
      break;
    case OSCILLATING:
    case ALL_OVERWATERED:
      // Continuous fast blink when all overwatered or oscillating
      digitalWrite(LED_PIN, (millis() / 200) % 2);
      break;
    case ALL_DRY:
      // Slow blink for all dry condition
      digitalWrite(LED_PIN, (millis() / 1000) % 2);
      break;
    case MONITORING:
    default:
      // Solid LED when monitoring and all optimal
      if (systemActive) {
        digitalWrite(LED_PIN, HIGH);
      } else {
        digitalWrite(LED_PIN, LOW);
      }
      break;
  }
}

void handleSerialCommands() {
  if (Serial.available()) {
    char command = Serial.read();
    
    switch (command) {
      case 's':
      case 'S':
        // Toggle system on/off
        systemActive = !systemActive;
        Serial.print("System ");
        Serial.println(systemActive ? "ACTIVATED" : "DEACTIVATED");
        if (!systemActive) {
          currentState = MONITORING;
          waterDirectionServo.write(SERVO_NEUTRAL);
        }
        break;
        
      case 'r':
      case 'R':
        // Reset system
        Serial.println("Resetting system...");
        currentState = MONITORING;
        waterDirectionServo.write(SERVO_NEUTRAL);
        plantGrowthCounter = 0;
        Serial.println("System reset complete!");
        break;
        
      case 'i':
      case 'I':
        // Display system info
        displaySystemInfo();
        break;
        
      case 't':
      case 'T':
        // Test mode - water each section briefly
        testWateringSystem();
        break;
        
      default:
        Serial.println("Commands: S=Toggle System, R=Reset, I=Info, T=Test");
        break;
    }
    
    // Clear any remaining characters
    while (Serial.available()) {
      Serial.read();
    }
  }
}

void displaySystemInfo() {
  Serial.println("\n=== SYSTEM STATUS ===");
  Serial.print("System Active: "); Serial.println(systemActive ? "YES" : "NO");
  Serial.print("Current State: "); printSystemState(); Serial.println();
  Serial.print("Growth Cycles: "); Serial.println(plantGrowthCounter / GROWTH_THRESHOLD);
  Serial.println("Recent Soil Readings:");
  
  for (int i = 0; i < 3; i++) {
    Serial.print("  Section "); Serial.print((char)('A' + i)); Serial.print(": ");
    Serial.print(soilValues[i]);
    printMoistureStatus(soilValues[i]);
    Serial.println();
  }
  Serial.println("==================\n");
}

void testWateringSystem() {
  Serial.println("Starting servo position test...");
  
  struct TestPosition {
    int angle;
    String description;
  };
  
  TestPosition positions[] = {
    {SERVO_NEUTRAL, "Neutral (0°)"},
    {SERVO_8_OCLOCK, "8 O'Clock (30°) - Sensor 2 Overwatered"},
    {SERVO_10_OCLOCK, "10 O'Clock (60°) - Sensor 1 Dry"},
    {SERVO_12_OCLOCK, "12 O'Clock (90°) - Sensor 2 Dry"},
    {SERVO_2_OCLOCK, "2 O'Clock (120°) - Sensor 3 Dry"},
    {SERVO_4_OCLOCK, "4 O'Clock (150°) - Sensor 1 Overwatered"},
    {SERVO_6_OCLOCK, "6 O'Clock (180°) - All Dry"},
    {SERVO_7_OCLOCK, "7 O'Clock (210°) - Sensor 3 Overwatered"}
  };
  
  for (int i = 0; i < 8; i++) {
    Serial.print("Testing: ");
    Serial.println(positions[i].description);
    waterDirectionServo.write(positions[i].angle);
    delay(2000); // Hold position for 2 seconds
  }
  
  // Test gentle oscillation
  Serial.println("Testing: Gentle Oscillation (10 seconds)");
  unsigned long oscillateStart = millis();
  bool testDirection = true;
  int testPos = 90;
  
  while (millis() - oscillateStart < 10000) {
    if (testDirection) {
      testPos += 30;
      if (testPos >= 180) {
        testPos = 180;
        testDirection = false;
      }
    } else {
      testPos -= 30;
      if (testPos <= 0) {
        testPos = 0;
        testDirection = true;
      }
    }
    waterDirectionServo.write(testPos);
    Serial.print("Oscillate Position: "); Serial.println(testPos);
    delay(1000);
  }
  
  // Return to neutral
  waterDirectionServo.write(SERVO_NEUTRAL);
  Serial.println("Test complete - Servo returned to neutral position!");
}