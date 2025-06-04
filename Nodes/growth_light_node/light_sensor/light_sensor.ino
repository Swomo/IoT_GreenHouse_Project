/*
 * IoT Greenhouse - Node 3: Enhanced Light & Growth System with Command Interface
 * 
 * This system continuously monitors plant heights and ambient light.
 * 
 * NEW: Accepts commands from Raspberry Pi for manual light control
 * 
 * Commands accepted:
 * - LIGHTS_ON_80     (turn lights on at 80% brightness)
 * - LIGHTS_OFF_0     (turn lights off)
 * - LIGHTS_AUTO_80   (return to automatic mode with 80% brightness)
 * - STATUS           (report current status)
 * 
 * Hardware Requirements:
 * - Arduino Uno
 * - 3x HC-SR04 Ultrasonic Sensors (individual plant height)
 * - 1x LDR with 10kΩ resistor (ambient light sensing)
 * - 3x LEDs (grow lights for each plant)
 * - 3x 220Ω resistors for LEDs
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
#define DEFAULT_LED_BRIGHTNESS 200  // Default LED brightness when on (0-255)
#define DARK_DELAY 5000        // 5 seconds for testing, 30 seconds in practice
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

// NEW: Manual control variables
enum LightControlMode {
  AUTO_MODE,
  MANUAL_ON,
  MANUAL_OFF
};

LightControlMode currentLightMode = AUTO_MODE;
int manualBrightness = DEFAULT_LED_BRIGHTNESS;
int currentBrightness = DEFAULT_LED_BRIGHTNESS;

void setup() {
  Serial.begin(9600);
  Serial.println(F("=== IoT Greenhouse Node 3: Enhanced Light & Growth System ==="));
  Serial.println(F("Command Interface Ready - Listening for Pi commands"));
  Serial.println(F("Monitoring 3 plants with automatic/manual lighting"));
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
  setAllLEDs(0);
  
  Serial.println(F("System initialized - Starting continuous monitoring..."));
  Serial.println(F("Light threshold: < 30 = dark"));
  Serial.println(F("Dark delay: 5 seconds (testing)"));
  Serial.println(F(">>> SYSTEM_READY"));
  Serial.println();
}

void loop() {
  unsigned long currentTime = millis();
  
  // Handle commands from Raspberry Pi (NEW)
  handleSerialCommands();
  
  // Read sensors every 2 seconds
  if (currentTime - lastSensorRead >= SENSOR_READ_INTERVAL) {
    readAllSensors();
    
    // Only check automatic light conditions if in AUTO mode (MODIFIED)
    if (currentLightMode == AUTO_MODE) {
      checkLightConditions();
    }
    
    lastSensorRead = currentTime;
  }
  
  // Display status every 5 seconds
  if (currentTime - lastStatusDisplay >= STATUS_DISPLAY_INTERVAL) {
    displayStatus();
    lastStatusDisplay = currentTime;
  }
  
  delay(100); // Small delay for stability
}

// NEW: Handle commands from Raspberry Pi
void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.length() == 0) return;
    
    // Parse light commands: LIGHTS_ACTION_BRIGHTNESS
    if (command.startsWith("LIGHTS_")) {
      parseLightCommand(command);
    }
    else if (command == "STATUS") {
      reportDetailedStatus();
    }
    else {
      Serial.println(">>> UNKNOWN_COMMAND: " + command);
    }
  }
}

// NEW: Parse light command from Pi
void parseLightCommand(String command) {
  // Parse: LIGHTS_ON_80, LIGHTS_OFF_0, LIGHTS_AUTO_90
  int firstUnderscore = command.indexOf('_', 7);  // After "LIGHTS_"
  int secondUnderscore = command.indexOf('_', firstUnderscore + 1);
  
  if (firstUnderscore > 0 && secondUnderscore > 0) {
    String action = command.substring(7, firstUnderscore);
    int brightness = command.substring(secondUnderscore + 1).toInt();
    
    // Validate brightness (0-100%)
    brightness = constrain(brightness, 0, 100);
    
    if (action == "ON") {
      setManualLightControl(MANUAL_ON, brightness);
      Serial.println(">>> LIGHTS_MANUAL_ON: " + String(brightness) + "%");
    }
    else if (action == "OFF") {
      setManualLightControl(MANUAL_OFF, 0);
      Serial.println(">>> LIGHTS_MANUAL_OFF");
    }
    else if (action == "AUTO") {
      manualBrightness = map(brightness, 0, 100, 0, 255);  // Store preferred brightness
      setManualLightControl(AUTO_MODE, brightness);
      Serial.println(">>> LIGHTS_AUTO_MODE: " + String(brightness) + "%");
    }
    else {
      Serial.println(">>> INVALID_ACTION: Use ON, OFF, or AUTO");
    }
  } else {
    Serial.println(">>> COMMAND_FORMAT_ERROR: Use LIGHTS_ACTION_BRIGHTNESS");
  }
}

// NEW: Set manual light control mode
void setManualLightControl(LightControlMode mode, int brightnessPercent) {
  currentLightMode = mode;
  
  switch (mode) {
    case MANUAL_ON:
      currentBrightness = map(brightnessPercent, 0, 100, 0, 255);
      setAllLEDs(currentBrightness);
      ledsOn = true;
      Serial.println(">>> LIGHTS_FORCED_ON: " + String(brightnessPercent) + "%");
      break;
      
    case MANUAL_OFF:
      setAllLEDs(0);
      ledsOn = false;
      Serial.println(">>> LIGHTS_FORCED_OFF");
      break;
      
    case AUTO_MODE:
      Serial.println(">>> LIGHTS_AUTO_MODE_ACTIVE: " + String(brightnessPercent) + "%");
      // Light control will be handled by checkLightConditions()
      break;
  }
}

// NEW: Set all LEDs to specified brightness
void setAllLEDs(int brightness) {
  analogWrite(LED_1, brightness);
  analogWrite(LED_2, brightness);
  analogWrite(LED_3, brightness);
}

// NEW: Detailed status report for Pi
void reportDetailedStatus() {
  Serial.println(">>> STATUS_REPORT_START");
  Serial.println(">>> LIGHT_MODE: " + getModeString(currentLightMode));
  Serial.println(">>> LEDS_STATUS: " + String(ledsOn ? "ON" : "OFF"));
  Serial.println(">>> LIGHT_LEVEL: " + String(lightLevel));
  Serial.println(">>> LED_BRIGHTNESS: " + String((currentBrightness * 100) / 255) + "%");
  
  // Plant heights
  for (int i = 0; i < 3; i++) {
    Serial.println(">>> PLANT_" + String(i+1) + "_HEIGHT: " + String(plantHeight[i]));
  }
  
  Serial.println(">>> LIGHT_THRESHOLD: " + String(LIGHT_THRESHOLD));
  Serial.println(">>> STATUS_REPORT_END");
}

String getModeString(LightControlMode mode) {
  switch (mode) {
    case AUTO_MODE: return "AUTO";
    case MANUAL_ON: return "MANUAL_ON";
    case MANUAL_OFF: return "MANUAL_OFF";
    default: return "UNKNOWN";
  }
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
      Serial.print(F(">>> DARK_DETECTED (Light: "));
      Serial.print(lightLevel);
      Serial.println(F(") - Starting timer..."));
    } else if (darkTimerStarted) {
      // Still dark - check if delay time has passed
      if (currentTime - darkStartTime >= DARK_DELAY) {
        // Dark delay elapsed - turn on LEDs
        if (!ledsOn) {
          turnOnLEDs();
        }
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
      Serial.print(F(">>> LIGHT_DETECTED (Light: "));
      Serial.print(lightLevel);
      Serial.println(F(") - LEDs turning off"));
    }
  }
}

void turnOnLEDs() {
  setAllLEDs(manualBrightness > 0 ? manualBrightness : DEFAULT_LED_BRIGHTNESS);
  currentBrightness = manualBrightness > 0 ? manualBrightness : DEFAULT_LED_BRIGHTNESS;
  ledsOn = true;
  
  Serial.println(F(">>> AUTO_LIGHTS_ON - Dark delay elapsed"));
  Serial.print(F("    LED Brightness: "));
  Serial.print((currentBrightness * 100) / 255);
  Serial.println(F("%"));
}

void turnOffLEDs() {
  setAllLEDs(0);
  ledsOn = false;
  
  Serial.println(F(">>> AUTO_LIGHTS_OFF - Light detected"));
}

void displayStatus() {
  // Light status
  Serial.print(F("Light: "));
  Serial.print(lightLevel);
  
  if (lightLevel < LIGHT_THRESHOLD) {
    Serial.print(F(" (DARK)"));
    if (darkTimerStarted && currentLightMode == AUTO_MODE) {
      unsigned long timeInDark = millis() - darkStartTime;
      unsigned long remaining = DARK_DELAY - timeInDark;
      if (remaining > 0) {
        Serial.print(F(" - Timer: "));
        Serial.print(remaining / 1000);
        Serial.print(F("s remaining"));
      }
    }
  } else {
    Serial.print(F(" (BRIGHT)"));
  }
  
  Serial.print(F(" | LEDs: "));
  Serial.print(ledsOn ? F("ON") : F("OFF"));
  
  if (ledsOn) {
    Serial.print(F(" ("));
    Serial.print((currentBrightness * 100) / 255);
    Serial.print(F("%)"));
  }
  
  Serial.print(F(" | Mode: "));
  Serial.print(getModeString(currentLightMode));
  
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