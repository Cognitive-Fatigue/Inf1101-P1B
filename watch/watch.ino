// TinyKey watch. Pair A owns this file: the link to the laptop.
// Pairs B and C work in security.ino and remote.ino and only use sendLine() and their *OnLine().
#include <Wire.h>
#include <SPI.h>
#include <TinyScreen.h>

TinyScreen display = TinyScreen(TinyScreenPlus);

const int MAX_LINE = 128;
char lineBuf[MAX_LINE];
int lineLen = 0;
bool lineTooLong = false;

// Sends one message; adds the newline. Same call over USB now and Bluetooth later.
void sendLine(const char *text) {
  if (!SerialUSB) return;  // no laptop listening: don't block
  SerialUSB.print(text);
  SerialUSB.print('\n');
}

void handleLine(const char *line) {
  if (strncmp(line, "ECHO:", 5) == 0) { sendLine(line); return; }  // link test
  if (securityOnLine(line)) return;
  if (remoteOnLine(line)) return;
  // unknown messages are ignored
}

// Collects bytes into whole lines; an overlong line is dropped up to its newline.
void readLink() {
  while (SerialUSB.available()) {
    char c = SerialUSB.read();
    if (c == '\r') continue;
    if (c == '\n') {
      lineBuf[lineLen] = 0;
      if (!lineTooLong && lineLen > 0) handleLine(lineBuf);
      lineLen = 0;
      lineTooLong = false;
    } else if (lineLen < MAX_LINE - 1) {
      lineBuf[lineLen++] = c;
    } else {
      lineTooLong = true;
    }
  }
}

void setup() {
  SerialUSB.begin(115200);
  Wire.begin();
  display.begin();
  display.setFlip(true);
  display.setBrightness(10);
  securitySetup();
  remoteSetup();
}

void loop() {
  readLink();
  securityLoop();
  remoteLoop();
}
