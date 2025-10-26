/*
  arduino_pid.ino
  Simple PID controller sketch for a MEMS piezo stage.
  Serial command protocol (ASCII):
    - SET Kp Ki Kd         -> set PID gains (floats)
    - SETPOINT <value>     -> set desired position (float)
    - START                -> start control loop
    - STOP                 -> stop control loop (output 0)
    - READ                 -> request one telemetry line
  Telemetry output (CSV): timestamp_ms,setpoint,measurement,output
  Hardware assumptions:
    - sensor connected to A0 (analogRead)
    - actuator on PWM pin 9 (analogWrite)
    - sensor range and actuator mapping are simplified; adapt scaling for your hardware
*/

const int sensorPin = A0;
const int actuatorPin = 9;

volatile bool running = false;

// PID parameters
double Kp = 2.0;
double Ki = 0.0;
double Kd = 0.0;

double setpoint = 0.0;      // desired measurement (in sensor units)
double integrator = 0.0;
double lastError = 0.0;
unsigned long lastTime = 0;

unsigned long telemetryIntervalMs = 20; // telemetry every 20 ms
unsigned long lastTelemetry = 0;

void setup() {
  Serial.begin(115200);
  pinMode(actuatorPin, OUTPUT);
  analogWrite(actuatorPin, 0);
  lastTime = millis();
  Serial.println("ARDUINO_PID_READY");
}

double readMeasurement() {
  int raw = analogRead(sensorPin); // 0..1023
  // Map to a physical unit if available; for now return raw as double
  return (double)raw;
}

void stopControl() {
  running = false;
  integrator = 0.0;
  lastError = 0.0;
  analogWrite(actuatorPin, 0);
}

void setActuatorOutput(double u) {
  // Map control output u (which we assume is roughly in -255..255) to PWM 0..255
  // Clip and map to 0..255 (if your actuator expects bipolar drive, adjust externally)
  int pwm = (int)round(u);
  if (pwm > 255) pwm = 255;
  if (pwm < 0) pwm = 0;
  analogWrite(actuatorPin, pwm);
}

void loop() {
  // handle serial input commands
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) {
      // Parse
      if (line.startsWith("SET ")) {
        // e.g. "SET 1.2 0.01 0.1" or "SET Kp Ki Kd" handled below
        String rest = line.substring(4);
        rest.trim();
        // Two flavors: numeric triple or named
        if (rest.indexOf(' ') != -1) {
          // numeric triple?
          double a = 0, b = 0, c = 0;
          int n = sscanf(rest.c_str(), "%lf %lf %lf", &a, &b, &c);
          if (n == 3) {
            Kp = a; Ki = b; Kd = c;
            Serial.println("OK SET GAINS");
          } else {
            Serial.println("ERR SET FORMAT");
          }
        } else {
          Serial.println("ERR SET FORMAT");
        }
      } else if (line.startsWith("SETPOINT ")) {
        String rest = line.substring(9);
        rest.trim();
        double sp = rest.toDouble();
        setpoint = sp;
        Serial.println("OK SETPOINT");
      } else if (line == "START") {
        running = true;
        integrator = 0.0;
        lastError = 0.0;
        lastTime = millis();
        Serial.println("OK START");
      } else if (line == "STOP") {
        stopControl();
        Serial.println("OK STOP");
      } else if (line == "READ") {
        double meas = readMeasurement();
        unsigned long t = millis();
        double out = 0.0; // not running => 0
        if (running) {
          // compute one step quickly
          double error = setpoint - meas;
          unsigned long now = millis();
          double dt = (now - lastTime) / 1000.0;
          if (dt <= 0.0) dt = 0.001;
          integrator += error * dt;
          double deriv = (error - lastError) / dt;
          out = Kp*error + Ki*integrator + Kd*deriv;
          // map out to 0..255 range for PWM
          double mapped = out;
          if (mapped < 0) mapped = 0;
          if (mapped > 255) mapped = 255;
          setActuatorOutput(mapped);
        }
        Serial.print(t); Serial.print(",");
        Serial.print(setpoint); Serial.print(",");
        Serial.print(meas); Serial.print(",");
        Serial.println((int)round(out));
      } else {
        Serial.println("ERR UNKNOWN_CMD");
      }
    }
  }

  // control loop regular update (simple timing)
  unsigned long now = millis();
  double dt = (now - lastTime) / 1000.0;
  if (running && dt >= 0.005) { // run at ~200 Hz
    double meas = readMeasurement();
    double error = setpoint - meas;
    integrator += error * dt;
    double deriv = (error - lastError) / dt;
    double u = Kp*error + Ki*integrator + Kd*deriv;
    // For a single-sided PWM actuator, map to 0..255
    double mapped = u;
    if (mapped < 0) mapped = 0;
    if (mapped > 255) mapped = 255;
    setActuatorOutput(mapped);
    lastError = error;
    lastTime = now;
  }

  // periodic telemetry
  if (now - lastTelemetry >= telemetryIntervalMs) {
    double meas = readMeasurement();
    int outVal = 0;
    // approximate last output reading as lastError-based controller output:
    double lastCon = Kp*lastError + Ki*integrator + Kd*0.0;
    if (lastCon < 0) lastCon = 0;
    if (lastCon > 255) lastCon = 255;
    outVal = (int)round(lastCon);
    Serial.print(now); Serial.print(",");
    Serial.print(setpoint); Serial.print(",");
    Serial.print(meas); Serial.print(",");
    Serial.println(outVal);
    lastTelemetry = now;
  }
}
