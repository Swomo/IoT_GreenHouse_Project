/*
 * IoT Greenhouse - Node 3: Light & Growth Monitoring System (3 Plants)
 * SIMPLIFIED CONTINUOUS MONITORING VERSION
 * 
 * This system continuously monitors plant heights and ambient light.
 * If dark for 30 seconds, all LEDs turn on automatically.
 * 
 * Hardware Requirements:
 * - Arduino Uno
 * - 3x HC-SR04 Ultrasonic Sensors (individual plant height)
 * - 1x LDR with 10kΩ resistor (ambient light sensing)
 * - 3x LEDs (grow lights for each plant)
 * - 3x 220Ω resistors for LEDs
 * 
 * Author: IoT Greenhouse Team - Node 3 (Simplified)
 * Date: 2025
 */

// Pin Definitions
#define TRIG_1 2
#define ECHO_1 3
#define TRIG_2 4
#define ECHO_2 7
#define TRIG_3 8
#define ECHO_3 12
#define LDR_PIN A3
#define LED_1 5
#define LED_2 6
#define LED_3 9

// Thresholds - Updated for your LDR readings
#define LIGHT_THRESHOLD 30      // Above this = bright, below = dark
#define LED_BRIGHTNESS 200      // LED brightness when on (0-255)
//#define DARK_DELAY 5000       // 5 second dark delay for testing
#define DARK_DELAY 5000        // 30 seconds in milliseconds in practice, 5 seconds for testing purposes
#define SENSOR_HEIGHT 50.0      // Height of sensors from ground (cm)
#define POT_HEIGHT 10.0         // Height of plant pots (cm)

// Timing
#define SENSOR_READ_INTERVAL 2000   // Read sensors every 2 seconds
#define STATUS_DISPLAY_INTERVAL 5000 // Display status every 5 seconds

// Plant data
float plantHeight[3] = {0, 0, 0};
int lightLevel = 0;
bool ledsOn = false;

// Timing variables
unsigned long lastSensorRead = 0;
unsigned long lastStatusDisplay = 0;
unsigned long darkStartTime = 0;
bool isDark = false;
bool darkTimerStarted = false;

void setup() {
  Serial.begin(9600);
  Serial.println(F("=== IoT Greenhouse Node 3 - Continuous Monitor ==="));
  Serial.println(F("Monitoring 3 plants with automatic lighting"));
  Serial.println(F("LEDs activate after 30 seconds of darkness"));
  Serial.println();
  
  // Initialize pins
  pinMode(TRIG_1, OUTPUT);
  pinMode(ECHO_1, INPUT);
  pinMode(TRIG_2, OUTPUT);
  pinMode(ECHO_2, INPUT);
  pinMode(TRIG_3, OUTPUT);
  pinMode(ECHO_3, INPUT);
  pinMode(LED_1, OUTPUT);
  pinMode(LED_2, OUTPUT);
  pinMode(LED_3, OUTPUT);
  
  // Turn off LEDs initially
  analogWrite(LED_1, 0);
  analogWrite(LED_2, 0);
  analogWrite(LED_3, 0);
  
  Serial.println(F("System initialized - Starting continuous monitoring..."));
  Serial.println(F("Light threshold: < 30 = dark"));
  Serial.println(F("Expected readings: Lit room ~50, Covered ~10-15, Flashlight ~100-240"));
  Serial.println(F("Dark delay: 30 seconds"));
  Serial.println(F("LED brightness: 200/255"));
  Serial.println();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Read sensors every 2 seconds
  if (currentTime - lastSensorRead >= SENSOR_READ_INTERVAL) {
    readAllSensors();
    checkLightConditions();
    lastSensorRead = currentTime;
  }
  
  // Display status every 5 seconds
  if (currentTime - lastStatusDisplay >= STATUS_DISPLAY_INTERVAL) {
    displayStatus();
    lastStatusDisplay = currentTime;
  }
  
  delay(100); // Small delay for stability
}

void readAllSensors() {
  // Read ambient light level
  lightLevel = analogRead(LDR_PIN);
  
  // Read plant heights with delays to avoid sensor interference
  plantHeight[0] = readPlantHeight(TRIG_1, ECHO_1);
  delay(60);
  
  plantHeight[1] = readPlantHeight(TRIG_2, ECHO_2);
  delay(60);
  
  plantHeight[2] = readPlantHeight(TRIG_3, ECHO_3);
}

float readPlantHeight(byte trigPin, byte echoPin) {
  // Send ultrasonic pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Read echo duration with timeout
  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return -1; // No echo received
  
  // Calculate distance in cm
  float distance = (duration * 0.034) / 2;
  
  // Convert to plant height
  float height = SENSOR_HEIGHT - distance - POT_HEIGHT;
  
  // Return valid height or -1 for invalid reading
  return (height > 0 && height < 50) ? height : -1;
}

void checkLightConditions() {
  unsigned long currentTime = millis();
  
  // Check if it's currently dark
  bool currentlyDark = (lightLevel < LIGHT_THRESHOLD);
  
  if (currentlyDark) {
    // It's dark now
    if (!isDark) {
      // Just became dark - start the timer
      isDark = true;
      darkTimerStarted = true;
      darkStartTime = currentTime;
      Serial.print(F(">>> DARK DETECTED (Light: "));
      Serial.print(lightLevel);
      Serial.println(F(") - Starting 30 second timer..."));
    } else if (darkTimerStarted) {
      // Still dark - check if 30 seconds have passed
      if (currentTime - darkStartTime >= DARK_DELAY) {
        // 30 seconds of darkness - turn on LEDs
        if (!ledsOn) {
          turnOnLEDs();
        }
        // Keep timer active - don't set darkTimerStarted = false
        // This allows LEDs to stay on while it remains dark
      }
    }
  } else {
    // It's bright now
    if (isDark) {
      // Just became bright - turn off LEDs and reset timer
      isDark = false;
      darkTimerStarted = false;
      if (ledsOn) {
        turnOffLEDs();
      }
      Serial.print(F(">>> LIGHT DETECTED (Light: "));
      Serial.print(lightLevel);
      Serial.println(F(") - LEDs turning off"));
    }
  }
}

void turnOnLEDs() {
  analogWrite(LED_1, LED_BRIGHTNESS);
  analogWrite(LED_2, LED_BRIGHTNESS);
  analogWrite(LED_3, LED_BRIGHTNESS);
  ledsOn = true;
  
  Serial.println(F(">>> ALL LEDs ACTIVATED - 30 seconds of darkness elapsed"));
  Serial.print(F("    LED Brightness: "));
  Serial.print((LED_BRIGHTNESS * 100) / 255);
  Serial.println(F("%"));
}

void turnOffLEDs() {
  analogWrite(LED_1, 0);
  analogWrite(LED_2, 0);
  analogWrite(LED_3, 0);
  ledsOn = false;
  
  Serial.println(F(">>> ALL LEDs DEACTIVATED - Light detected"));
}

void displayStatus() {
  // Light status
  Serial.print(F("Light: "));
  Serial.print(lightLevel);
  
  if (lightLevel < LIGHT_THRESHOLD) {
    Serial.print(F(" (DARK)"));
    if (darkTimerStarted) {
      unsigned long timeInDark = millis() - darkStartTime;
      unsigned long remaining = DARK_DELAY - timeInDark;
      Serial.print(F(" - Timer: "));
      Serial.print(remaining / 1000);
      Serial.print(F("s remaining"));
    }
  } else {
    Serial.print(F(" (BRIGHT)"));
  }
  
  Serial.print(F(" | LEDs: "));
  Serial.print(ledsOn ? F("ON") : F("OFF"));
  
  if (ledsOn) {
    Serial.print(F(" ("));
    Serial.print((LED_BRIGHTNESS * 100) / 255);
    Serial.print(F("%)"));
  }
  
  Serial.println();
  
  // Plant heights
  for (byte i = 0; i < 3; i++) {
    Serial.print(F("Plant "));
    Serial.print(i + 1);
    Serial.print(F(": "));
    
    if (plantHeight[i] > 0) {
      Serial.print(plantHeight[i], 1);
      Serial.print(F(" cm"));
      
      // Add growth stage
      if (plantHeight[i] <= 5.0) {
        Serial.print(F(" (Seedling)"));
      } else if (plantHeight[i] <= 15.0) {
        Serial.print(F(" (Vegetative)"));
      } else if (plantHeight[i] <= 25.0) {
        Serial.print(F(" (Mature)"));
      } else {
        Serial.print(F(" (Overgrown)"));
      }
    } else {
      Serial.print(F("No reading"));
    }
    
    if (i < 2) Serial.print(F(" | "));
  }
  
  Serial.println();
  Serial.println(F("----------------------------------------"));
}

// Optional: Add a simple command to manually test LEDs
void checkSerialCommands() {
  if (Serial.available()) {
    char command = Serial.read();
    
    switch (command) {
      case 't':
      case 'T':
        // Test LEDs manually
        Serial.println(F("Manual LED test..."));
        analogWrite(LED_1, 255);
        analogWrite(LED_2, 255);
        analogWrite(LED_3, 255);
        delay(2000);
        analogWrite(LED_1, 0);
        analogWrite(LED_2, 0);
        analogWrite(LED_3, 0);
        Serial.println(F("LED test complete"));
        break;
        
      case 's':
      case 'S':
        // Show current sensor readings
        Serial.println(F("=== SENSOR READINGS ==="));
        Serial.print(F("Raw light value: "));
        Serial.println(lightLevel);
        for (byte i = 0; i < 3; i++) {
          Serial.print(F("Plant "));
          Serial.print(i + 1);
          Serial.print(F(" height: "));
          Serial.println(plantHeight[i]);
        }
        Serial.println(F("====================="));
        break;
    }
    
    // Clear remaining characters
    while (Serial.available()) Serial.read();
  }
}