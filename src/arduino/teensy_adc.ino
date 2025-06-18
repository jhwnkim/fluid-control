// Teensy 3.2 code for fluid control
// Teensy information: https://www.pjrc.com/teensy/teensy31.html

void setup()   {                
  Serial.begin(38400);

  pinMode(20, INPUT); // A6 Pin
  pinMode(LED_BUILTIN, OUTPUT);
}

int val;

void loop()                     
{
  val = analogRead(A6);
  Serial.print("analog A6 is: ");
  Serial.println(val);
  delay(500);
  digitalWrite(LED_BUILTIN, HIGH);
  delay(500);
  digitalWrite(LED_BUILTIN, LOW);

}