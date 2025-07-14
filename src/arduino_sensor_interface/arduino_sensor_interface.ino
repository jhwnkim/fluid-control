// Arduino sensor interface for fluid control
// Interfaces Sensiron SLF3S-0600F flow rate sensor and TT OPB350 
// fluid detection sensor to fluid control GUI via serial port
// Tested on:
//   Teensy 3.2 board (https://www.pjrc.com/teensy/teensy32.html)
//   Arduino Mega 2560 R3 (https://docs.arduino.cc/hardware/mega-2560/)

#include <Arduino.h>
#include <SensirionI2cSf06Lf.h>
#include <Wire.h>

SensirionI2cSf06Lf sensor;

static char errorMessage[64];
static int16_t error;

void print_byte_array(uint8_t* array, uint16_t len) {
    uint16_t i = 0;
    Serial.print("0x");
    for (; i < len; i++) {
        Serial.print(array[i], HEX);
    }
}
//boolean to switch direction
bool directionState;

void setup() {
  // Setup Pin modes
  // pinMode(A0, INPUT_PULLDOWN)
  // pinMode(A1, INPUT_PULLUP)
  // pinMode(14, INPUT); // A0 Pin
  // pinMode(15, INPUT); // A1 Pin
  // pinMode(16, INPUT); // A2 Pin
  // pinMode(17, INPUT); // A3 Pin
  // pinMode(18, INPUT); // A4 Pin
  // pinMode(19, INPUT); // A5 Pin
  
  pinMode(LED_BUILTIN, OUTPUT);

  // Initialize serial communication
  Serial.begin(500000);
  while (!Serial) ;    // Wait for serial port to connect (for Leonardo/Micro)

  // Initialize I2C to flow rate sensor
  Wire.begin();
  sensor.begin(Wire, SLF3S_0600F_I2C_ADDR_08);
  sensor.stopContinuousMeasurement();
  delay(100);
  uint32_t productIdentifier = 0;
  uint8_t serialNumber[8] = {0};
  error = sensor.readProductIdentifier(productIdentifier, serialNumber, 8);
  if (error != NO_ERROR) {
      Serial.print("Error trying to execute readProductIdentifier(): ");
      errorToString(error, errorMessage, sizeof errorMessage);
      Serial.println(errorMessage);
      return;
  }
  Serial.print("productIdentifier: ");
  Serial.print(productIdentifier);
  Serial.print("\t");
  Serial.print("serialNumber: ");
  print_byte_array(serialNumber, 8);
  Serial.println();
  error = sensor.startH2oContinuousMeasurement();
  if (error != NO_ERROR) {
      Serial.print(
          "Error trying to execute startH2oContinuousMeasurement(): ");
      errorToString(error, errorMessage, sizeof errorMessage);
      Serial.println(errorMessage);
      return;
  }

  // Turn on built in LED
  digitalWrite(LED_BUILTIN, HIGH);
}

int val = -1;

void loop() {
  float aFlow = 0;
  float aTemperature = 0.0;
  uint16_t aSignalingFlags = 0u;
  int adcValue = -1;
  
  char start = 'E';
  byte payloadLength = 0;
  byte payload[4];

  delay(10); // Loop delay 10 ms

  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n'); // Read incoming command
    command.trim(); // Remove any trailing newline or spaces

    if (command.startsWith("READ")) {
      if (command.endsWith("A0")) {
        adcValue = analogRead(A0);
        start = 'R';
        payloadLength = sizeof(adcValue);
        memcpy(payload, &adcValue, payloadLength);
      }
      else if (command.endsWith("A1")) {
        adcValue = analogRead(A1);
        start = 'R';
        payloadLength = sizeof(adcValue);
        memcpy(payload, &adcValue, payloadLength);
      }
      else if (command.endsWith("FS")) {
        error = sensor.readMeasurementData(INV_FLOW_SCALE_FACTORS_SLF3S_0600F,
                                       aFlow, aTemperature, aSignalingFlags);
        if (error != NO_ERROR) {
            Serial.println("ERR: Flow sensor readMeasurementData() failed.");
        }
        else {
          start = 'R';
          payloadLength = sizeof(aFlow);
          memcpy(payload, &aFlow, payloadLength);
        }
      }
      
      if (payloadLength > 0) {
        Serial.write(start);
        Serial.write(payloadLength);
        Serial.write(payload, payloadLength);
        Serial.write('\n');
      } else {
        Serial.println("ERR: No payload");
      }
    } 
    else if (command.startsWith("PRINT")) {
      if (command.endsWith("A0")) {
        adcValue = analogRead(A0);
        Serial.print('P');
        Serial.println(adcValue);
      }
      else if (command.endsWith("A1")) {
        adcValue = analogRead(A1);
        Serial.print('P');
        Serial.println(adcValue);
      }
      else if (command.endsWith("FS")) {
        error = sensor.readMeasurementData(INV_FLOW_SCALE_FACTORS_SLF3S_0600F,
                                       aFlow, aTemperature, aSignalingFlags);
        if (error != NO_ERROR) {
            Serial.println("ERR: Flow sensor readMeasurementData() failed.");
        }
        else {
          Serial.print('P');
          Serial.println(aFlow);
        }
      }
    }
    else {
      Serial.println("ERR: Unknown command. Use READ A0, A1, FS.");
    }
  }
}
