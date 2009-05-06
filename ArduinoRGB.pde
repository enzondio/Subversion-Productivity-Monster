int bluePin = 11;
int greenPin = 10;
int redPin = 9;
int userInput[3];   // raw input from serial buffer, 3 bytes
int startbyte = 0;
int i = 0;
int pulse = -30;
int red, green, blue = 0;
int direction = 1;
void setup()
{
  Serial.begin(9600);
}

void loop()
{
  if (Serial.available() > 3) 
  {
    //read the first byte
    startbyte = Serial.read();
    // if it's really the startbyte (255)
    if (startbyte == 255) {
      // then get the next three bytes
      for (i=0;i<3;i++) {
        userInput[i] = Serial.read();
      }
      red = userInput[0]/2;
      green = userInput[1];
      blue = userInput[2];
    }
   
  }
    if (pulse == 0) {
      direction = -1;
    } else if (pulse == -30) {
      direction = 1;
    }
    //Note, since I'm using a common anode RGB LED, high voltage means the LED
    //is off, hence the 254 - color business.
    if (red + pulse > 0 && red > 0) {
      analogWrite(redPin, 254 - (red + pulse));
    } else {
      analogWrite(redPin, 254);
    }
    if (green + pulse > 0 && green > 0 ) {
      analogWrite(greenPin, 254 - (green + pulse));
    } else {
      analogWrite(greenPin, 254);
    }
    if (blue + pulse > 0 && blue > 0 ) {
       analogWrite(bluePin, 254 - (blue + pulse));
    } else {
      analogWrite(bluePin,254);
    }
    pulse = pulse + direction;
    delay(50);
}
 
