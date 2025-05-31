// Pin Definitions
const int LED_PIN = 7;         // PWM capable pin
const int SERVO_PIN = 2;       // Servo signal pin
const int SOIL_PIN_1 = A0;
const int SOIL_PIN_2 = A1;
const int SOIL_PIN_3 = A2;

// Menu vars
const int timeout = 10000;     // 10 second timeout
char menuOption = 0;
long time0;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  Serial.println("start");

  pinMode(LED_PIN, OUTPUT);
  pinMode(SERVO_PIN, OUTPUT);

  menuOption = menu();
}

void loop() {
  if (menuOption == '1') {
    // Fade Red LED
    for (int i = 255; i > 0; i -= 5) {
      analogWrite(LED_PIN, i);
      delay(15);
    }
    digitalWrite(LED_PIN, LOW);
  } 
  else if (menuOption == '2') {
    // Servo Test without library
    // Send PWM-style pulse to servo manually
    rotateServo(180); // CW full speed
    delay(2000);
    rotateServo(0);   // CCW full speed
    delay(2000);
    rotateServo(90);  // Stop
    delay(2000);
  }
  else if (menuOption == '3') {
    int val = analogRead(SOIL_PIN_1);
    Serial.print("Soil Sensor #1: "); Serial.println(val);
  }
  else if (menuOption == '4') {
    int val = analogRead(SOIL_PIN_2);
    Serial.print("Soil Sensor #2: "); Serial.println(val);
  }
  else if (menuOption == '5') {
    int val = analogRead(SOIL_PIN_3);
    Serial.print("Soil Sensor #3: "); Serial.println(val);
  }

  if (millis() - time0 > timeout) {
    menuOption = menu();
  }
}

// Manually simulate PWM control for continuous rotation servo
void rotateServo(int angle) {
  // angle between 0 - 180
  int pulseWidth = map(angle, 0, 180, 360, 2000); // microseconds
  for (int i = 0; i < 50; i++) {
    digitalWrite(SERVO_PIN, HIGH);
    delayMicroseconds(pulseWidth);
    digitalWrite(SERVO_PIN, LOW);
    delay(20);
  }
}

// Menu function
char menu() {
  Serial.println("\nWhich component would you like to test?");
  Serial.println("(1) Basic Red LED 5mm");
  Serial.println("(2) Continuous Rotation Micro Servo - FS90R");
  Serial.println("(3) Soil Moisture Sensor #1");
  Serial.println("(4) Soil Moisture Sensor #2");
  Serial.println("(5) Soil Moisture Sensor #3");
  Serial.println("(menu) Send anything else or reset");

  while (!Serial.available());

  while (Serial.available()) {
    char c = Serial.read();
    if (isAlphaNumeric(c)) {
      if (c == '1') Serial.println("Now Testing Basic Red LED 5mm");
      else if (c == '2') Serial.println("Now Testing Continuous Rotation Micro Servo - FS90R");
      else if (c == '3') Serial.println("Now Testing Soil Moisture Sensor #1");
      else if (c == '4') Serial.println("Now Testing Soil Moisture Sensor #2");
      else if (c == '5') Serial.println("Now Testing Soil Moisture Sensor #3");
      else {
        Serial.println("Illegal input!");
        return 0;
      }
      time0 = millis();
      return c;
    }
  }
  return 0;
}
