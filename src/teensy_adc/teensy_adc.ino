// Teensy 3.2 code for fluid control
// Teensy information: https://www.pjrc.com/teensy/teensy31.html

void setup() {
  pinMode(14, INPUT); // A0 Pin
  pinMode(15, INPUT); // A1 Pin
  pinMode(16, INPUT); // A2 Pin
  pinMode(17, INPUT); // A3 Pin
  pinMode(18, INPUT); // A4 Pin
  pinMode(19, INPUT); // A5 Pin
  
  pinMode(LED_BUILTIN, OUTPUT);

  Serial.begin(38400);  // Initialize serial communication
  while (!Serial) ;    // Wait for serial port to connect (for Leonardo/Micro)

  digitalWrite(LED_BUILTIN, HIGH);
}

int val = -1;

void loop() {

  // val = analogRead(A0);
  // Serial.println("Hello");
  // digitalWrite(LED_BUILTIN, HIGH);

  // delay(500);
  // digitalWrite(LED_BUILTIN, LOW);
  // delay(500);

  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n'); // Read incoming command
    command.trim(); // Remove any trailing newline or spaces

    if (command.startsWith("READ")) {
      int value = -1;

      if (command.endsWith("A0")) value = analogRead(A0);
      else if (command.endsWith("A1")) value = analogRead(A1);
      else if (command.endsWith("A2")) value = analogRead(A2);
      else if (command.endsWith("A3")) value = analogRead(A3);
      else if (command.endsWith("A4")) value = analogRead(A4);
      else if (command.endsWith("A5")) value = analogRead(A5);

      if (value != -1) {
        // Serial.print("ADC Value = ");
        Serial.println(value);
      } else {
        Serial.println("Invalid pin. Use A0 to A5.");
      }
    } else {
      Serial.println("Unknown command. Use READ A0 to READ A5.");
    }
  }
}
