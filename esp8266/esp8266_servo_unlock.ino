#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

#define SERVO_PIN D2   // GPIO4

ESP8266WebServer server(80);
Servo doorServo;

const char* ssid = "Door_Lock_AP";
const char* password = "12345678";

// Adjust these angles for your lock
#define LOCK_ANGLE   0
#define UNLOCK_ANGLE 110

bool doorUnlocked = false;
unsigned long unlockStartTime = 0;
const unsigned long UNLOCK_DURATION = 5000; // 5 seconds

// ---------- UNLOCK HANDLER ----------
void handleUnlock() {
  if (!doorUnlocked) {
    doorServo.write(UNLOCK_ANGLE);
    doorUnlocked = true;
    unlockStartTime = millis();

    Serial.println("DOOR UNLOCKED (Servo)");
  }
  server.send(200, "text/plain", "DOOR UNLOCKED");
}

// ---------- STATUS HANDLER ----------
void handleStatus() {
  server.send(200, "text/plain",
              doorUnlocked ? "DOOR UNLOCKED" : "DOOR LOCKED");
}

void setup() {
  Serial.begin(9600);

  // Servo setup
  doorServo.attach(SERVO_PIN);
  doorServo.write(LOCK_ANGLE);   // Start locked
  Serial.println("DOOR LOCKED (Servo)");

  // Wi-Fi AP
  WiFi.softAP(ssid, password);

  Serial.print("ESP IP: ");
  Serial.println(WiFi.softAPIP());  // 192.168.4.1

  // HTTP routes
  server.on("/unlock", handleUnlock);
  server.on("/status", handleStatus);

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();

  // ---------- AUTO-LOCK ----------
  if (doorUnlocked && millis() - unlockStartTime >= UNLOCK_DURATION) {
    doorServo.write(LOCK_ANGLE);
    doorUnlocked = false;
    Serial.println("DOOR LOCKED (Servo)");
  }
}
