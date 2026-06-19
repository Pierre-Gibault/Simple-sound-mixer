/*
  Stream Deck - Arduino Nano
  ─────────────────────────────────────────────
  POT 0 → A0  : Discord volume
  POT 1 → A1  : Global (system) volume
  POT 2 → A2  : Spotify volume
  BTN 0 → D2  : Simulate F10
  BTN 1 → D3  : Simulate F12

  Serial protocol at 115200 baud:
    POT:0:512   → pot index (0-2), raw value 0-1023
    BTN:0:1     → button index (0-1), 1=pressed 0=released
*/

const int POT_PINS[3] = {A0, A1, A2};
const int BTN_PINS[2] = {2, 3};

const int  POT_DEADZONE   = 6;
const int  POT_SEND_MS    = 25;
const int  DEBOUNCE_MS    = 30;

int  potLast[3]       = {-1, -1, -1};
int  btnLast[2]       = {HIGH, HIGH};
int  btnState[2]      = {HIGH, HIGH};
unsigned long btnTime[2]   = {0, 0};
unsigned long lastPotSend  = 0;

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 3; i++) pinMode(POT_PINS[i], INPUT);
  for (int i = 0; i < 2; i++) pinMode(BTN_PINS[i], INPUT_PULLUP);
  delay(200);
  Serial.println("STREAMDECK:READY");
}

void loop() {
  unsigned long now = millis();

  // Potentiometers
  if (now - lastPotSend >= POT_SEND_MS) {
    lastPotSend = now;
    for (int i = 0; i < 3; i++) {
      int val = analogRead(POT_PINS[i]);
      if (abs(val - potLast[i]) > POT_DEADZONE) {
        potLast[i] = val;
        Serial.print("POT:"); Serial.print(i);
        Serial.print(":"); Serial.println(val);
      }
    }
  }

  // Buttons (debounced)
  for (int i = 0; i < 2; i++) {
    int reading = digitalRead(BTN_PINS[i]);
    if (reading != btnLast[i]) btnTime[i] = now;
    if ((now - btnTime[i]) >= DEBOUNCE_MS && reading != btnState[i]) {
      btnState[i] = reading;
      Serial.print("BTN:"); Serial.print(i);
      Serial.print(":"); Serial.println(reading == LOW ? 1 : 0);
    }
    btnLast[i] = reading;
  }
}
