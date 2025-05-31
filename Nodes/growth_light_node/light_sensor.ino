// Pin Definitions
#define HCSR04_PIN_TRIG 3
#define HCSR04_PIN_ECHO 2
#define LDR_PIN_SIG     A3

// Threshold for LDR detection (not used in logic here but defined)
#define THRESHOLD_ldr 100

// Variables
int ldrAverageLight;
const int timeout = 10000; // Timeout in milliseconds
char menuOption = 0;
long time0;

void setup() {
  Serial.begin(9600);
  // while (!Serial);

  Serial.println("start");

  pinMode(HCSR04_PIN_TRIG, OUTPUT);
  pinMode(HCSR04_PIN_ECHO, INPUT);

  ldrAverageLight = readAverageLDR();
  menuOption = menu();
}

void loop() {
  if (menuOption == '1') {
    // Ultrasonic sensor reading
    int distance = getDistanceCM();
    Serial.print("Distance: ");
    Serial.print(distance);
    Serial.println(" [cm]");
    delay(500);
  } else if (menuOption == '2') {
    // LDR reading
    int ldrSample = analogRead(LDR_PIN_SIG);
    int ldrDiff = abs(ldrAverageLight - ldrSample);
    Serial.print("Light Diff: ");
    Serial.println(ldrDiff);
    delay(500);
  }

  if (millis() - time0 > timeout) {
    menuOption = menu();
  }
}

// Function to read average LDR value at startup
int readAverageLDR() {
  long sum = 0;
  const int samples = 10;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(LDR_PIN_SIG);
    delay(10);
  }
  return sum / samples;
}

// Function to get distance from HC-SR04
int getDistanceCM() {
  digitalWrite(HCSR04_PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(HCSR04_PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(HCSR04_PIN_TRIG, LOW);

  long duration = pulseIn(HCSR04_PIN_ECHO, HIGH, 30000); // 30 ms timeout
  int distance = duration * 0.034 / 2; // Convert to cm
  return distance;
}

// Serial menu
char menu() {
  Serial.println("\nWhich component would you like to test?");
  Serial.println("(1) Ultrasonic Sensor - HC-SR04");
  Serial.println("(2) LDR - Mini Photocell");
  Serial.println("(menu) Send anything else or press reset\n");

  while (!Serial.available());

  while (Serial.available()) {
    char c = Serial.read();
    if (isAlphaNumeric(c)) {
      if (c == '1') Serial.println("Now Testing Ultrasonic Sensor - HC-SR04");
      else if (c == '2') Serial.println("Now Testing LDR - Mini Photocell");
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
