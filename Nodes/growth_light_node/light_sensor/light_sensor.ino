/*
 * IoT Greenhouse - Node 3: Light & Growth Monitoring System (3 Plants)
 * MEMORY-OPTIMIZED VERSION for Arduino Uno
 * 
 * This system monitors individual plant heights using 3 ultrasonic sensors,
 * ambient light levels, and automatically controls grow lights.
 * Optimized for Arduino Uno's limited memory (2KB SRAM).
 * 
 * Hardware Requirements:
 * - Arduino Uno
 * - 3x HC-SR04 Ultrasonic Sensors (individual plant height)
 * - 1x LDR with 10kΩ resistor (ambient light sensing)
 * - 3x LEDs (grow lights for each plant)
 * - 3x 220Ω resistors for LEDs
 * 
 * Author: IoT Greenhouse Team - Node 3 (Memory Optimized)
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

// Thresholds
#define LIGHT_LOW 300
#define LIGHT_HIGH 500
#define MAX_BRIGHTNESS 255
#define MIN_BRIGHTNESS 80
#define SEEDLING_HEIGHT 5.0
#define VEGETATIVE_HEIGHT 15.0
#define MATURE_HEIGHT 25.0
#define SENSOR_HEIGHT 50.0
#define POT_HEIGHT 10.0

// Timing
#define READ_INTERVAL 5000
#define LOG_INTERVAL 30000
#define TIMEOUT 10000

// Plant data (using separate arrays to save memory)
float plantHeight[3] = {0, 0, 0};
float prevHeight[3] = {0, 0, 0};
byte plantStage[3] = {0, 0, 0};
byte ledBrightness[3] = {0, 0, 0};
bool needsLight[3] = {false, false, false};

// System variables
int lightLevel = 0;
bool lightsActive = false;
unsigned long lastRead = 0;
unsigned long lastLog = 0;
unsigned long time0 = 0;
char menuOption = 0;

void setup() {
  Serial.begin(9600);
  Serial.println(F("IoT Greenhouse Node 3 - Memory Optimized"));
  
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
  
  // Turn off LEDs
  analogWrite(LED_1, 0);
  analogWrite(LED_2, 0);
  analogWrite(LED_3, 0);
  
  Serial.println(F("System ready"));
  menuOption = menu();
}

void loop() {
  if (menuOption == '1') {
    // Full monitoring
    if (millis() - lastRead >= READ_INTERVAL) {
      readAllSensors();
      controlLights();
      displayStatus();
      lastRead = millis();
    }
    
    if (millis() - lastLog >= LOG_INTERVAL) {
      logData();
      lastLog = millis();
    }
  }
  else if (menuOption == '2') {
    testPlants();
    menuOption = menu();
  }
  else if (menuOption == '3') {
    testLight();
    menuOption = menu();
  }
  else if (menuOption == '4') {
    testLEDs();
    menuOption = menu();
  }
  
  // Menu timeout
  if (millis() - time0 > TIMEOUT) {
    menuOption = menu();
  }
  
  delay(100);
}

void readAllSensors() {
  // Read light level
  lightLevel = analogRead(LDR_PIN);
  
  // Read plant heights
  plantHeight[0] = readHeight(TRIG_1, ECHO_1);
  delay(50);
  plantHeight[1] = readHeight(TRIG_2, ECHO_2);
  delay(50);
  plantHeight[2] = readHeight(TRIG_3, ECHO_3);
  
  // Update growth stages
  for (byte i = 0; i < 3; i++) {
    if (plantHeight[i] > 0) {
      plantStage[i] = getGrowthStage(plantHeight[i]);
    }
  }
}

float readHeight(byte trigPin, byte echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return -1;
  
  float distance = (duration * 0.034) / 2;
  float height = SENSOR_HEIGHT - distance - POT_HEIGHT;
  
  return (height > 0 && height < 40) ? height : -1;
}

byte getGrowthStage(float height) {
  if (height <= SEEDLING_HEIGHT) return 0;
  else if (height <= VEGETATIVE_HEIGHT) return 1;
  else if (height <= MATURE_HEIGHT) return 2;
  else return 3;
}

void controlLights() {
  // Global lighting decision
  lightsActive = (lightLevel < LIGHT_LOW);
  
  // Control individual LEDs
  byte pins[] = {LED_1, LED_2, LED_3};
  
  for (byte i = 0; i < 3; i++) {
    byte targetBrightness = 0;
    
    if (lightsActive && plantHeight[i] > 0) {
      // Base brightness from light deficit
      int deficit = LIGHT_HIGH - lightLevel;
      byte baseBright = map(deficit, 0, LIGHT_HIGH, MIN_BRIGHTNESS, MAX_BRIGHTNESS);
      
      // Adjust for growth stage
      switch (plantStage[i]) {
        case 0: targetBrightness = baseBright * 0.6; break; // Seedling
        case 1: targetBrightness = baseBright; break;       // Vegetative
        case 2: targetBrightness = baseBright * 0.8; break; // Mature
        case 3: targetBrightness = baseBright * 0.5; break; // Overgrown
      }
      
      targetBrightness = constrain(targetBrightness, MIN_BRIGHTNESS, MAX_BRIGHTNESS);
    }
    
    // Update LED if significant change
    if (abs(targetBrightness - ledBrightness[i]) > 10) {
      fadeLED(i, pins[i], targetBrightness);
    }
    
    needsLight[i] = (targetBrightness > 0);
  }
}

void fadeLED(byte index, byte pin, byte target) {
  byte current = ledBrightness[index];
  int step = (target > current) ? 5 : -5;
  
  while (abs(current - target) > 5) {
    current += step;
    analogWrite(pin, current);
    delay(20);
  }
  
  analogWrite(pin, target);
  ledBrightness[index] = target;
}

void displayStatus() {
  Serial.print(F("Light: "));
  Serial.print(lightLevel);
  Serial.print(F(" | Lights: "));
  Serial.println(lightsActive ? F("ON") : F("OFF"));
  
  for (byte i = 0; i < 3; i++) {
    Serial.print(F("P"));
    Serial.print(i + 1);
    Serial.print(F(": "));
    
    if (plantHeight[i] > 0) {
      Serial.print(plantHeight[i], 1);
      Serial.print(F("cm "));
      Serial.print(getStageText(plantStage[i]));
      Serial.print(F(" LED:"));
      Serial.print((ledBrightness[i] * 100) / 255);
      Serial.print(F("%"));
    } else {
      Serial.print(F("No reading"));
    }
    
    if (i < 2) Serial.print(F(" | "));
  }
  Serial.println();
}

const char* getStageText(byte stage) {
  switch (stage) {
    case 0: return "Seed";
    case 1: return "Veg";
    case 2: return "Mat";
    case 3: return "Over";
    default: return "Unk";
  }
}

void logData() {
  Serial.println(F("=== LOG ==="));
  for (byte i = 0; i < 3; i++) {
    Serial.print(F("Plant"));
    Serial.print(i + 1);
    Serial.print(F(": "));
    Serial.print(plantHeight[i], 1);
    Serial.print(F("cm "));
    Serial.println(getStageText(plantStage[i]));
  }
  Serial.println(F("==========="));
}

void testPlants() {
  Serial.println(F("Testing plants..."));
  
  for (byte i = 0; i < 3; i++) {
    Serial.print(F("Plant "));
    Serial.print(i + 1);
    Serial.print(F(": "));
    
    float height = -1;
    if (i == 0) height = readHeight(TRIG_1, ECHO_1);
    else if (i == 1) height = readHeight(TRIG_2, ECHO_2);
    else height = readHeight(TRIG_3, ECHO_3);
    
    if (height > 0) {
      Serial.print(height, 1);
      Serial.print(F("cm "));
      Serial.println(getStageText(getGrowthStage(height)));
    } else {
      Serial.println(F("Invalid"));
    }
    
    delay(500);
  }
}

void testLight() {
  Serial.println(F("Testing light sensor..."));
  
  for (byte i = 0; i < 5; i++) {
    int reading = analogRead(LDR_PIN);
    Serial.print(F("Reading "));
    Serial.print(i + 1);
    Serial.print(F(": "));
    Serial.print(reading);
    
    if (reading < LIGHT_LOW) Serial.println(F(" (DARK)"));
    else if (reading > LIGHT_HIGH) Serial.println(F(" (BRIGHT)"));
    else Serial.println(F(" (MED)"));
    
    delay(500);
  }
}

void testLEDs() {
  Serial.println(F("Testing LEDs..."));
  byte pins[] = {LED_1, LED_2, LED_3};
  
  for (byte i = 0; i < 3; i++) {
    Serial.print(F("LED "));
    Serial.println(i + 1);
    
    // Fade up
    for (byte b = 0; b <= 255; b += 25) {
      analogWrite(pins[i], b);
      delay(50);
    }
    
    delay(500);
    
    // Fade down
    for (int b = 255; b >= 0; b -= 25) {
      analogWrite(pins[i], b);
      delay(50);
    }
    
    delay(200);
  }
  
  Serial.println(F("LED test complete"));
}

char menu() {
  Serial.println(F("\n=== MENU ==="));
  Serial.println(F("1) Monitor"));
  Serial.println(F("2) Test Plants"));
  Serial.println(F("3) Test Light"));
  Serial.println(F("4) Test LEDs"));
  Serial.println(F("============"));

  while (!Serial.available());

  while (Serial.available()) {
    char c = Serial.read();
    if (c >= '1' && c <= '4') {
      switch(c) {
        case '1': Serial.println(F("Starting monitor...")); break;
        case '2': Serial.println(F("Testing plants...")); break;
        case '3': Serial.println(F("Testing light...")); break;
        case '4': Serial.println(F("Testing LEDs...")); break;
      }
      time0 = millis();
      return c;
    }
  }
  
  Serial.println(F("Invalid! Use 1-4"));
  return 0;
}