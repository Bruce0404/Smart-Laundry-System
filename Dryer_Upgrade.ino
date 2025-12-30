/*
 * 專案名稱：IoT 工業乾燥機升級控制系統 (IoT Industrial Dryer Upgrade)
 * 硬體核心：NodeMCU D1 Mini (ESP8266)
 * 功能：
 * 1. MQTT 遠端控制 3 路繼電器 (總電源、熱風、冷風)
 * 2. MAX6675 讀取 K 型熱電偶溫度並上傳
 * 3. 狀態指示燈：
 *    - Wi-Fi 狀態：D4 (內建 LED)
 *    - MQTT 狀態：D7 (外接 LED) ★★★
 * 作者：Gemini (協助生成)
 * 日期：2025
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <max6675.h>
// ================= 1. Wi-Fi 與 MQTT 設定 =================
const char* ssid = "Pixel_3169"; 
const char* password = "ar3mafj92tq3twf"; 

const char* mqtt_server = "broker.hivemq.com"; 
const int mqtt_port = 1883;
const char* mqtt_user = "hivemq.webclient.1764919445852"; 
const char* mqtt_pass = "6?q<80pUdgrFLX5>%lHY";

// 定義 MQTT 主題
const char* topic_control_power = "dryer/control/power"; 
const char* topic_control_hot = "dryer/control/hot";     
const char* topic_control_cool = "dryer/control/cool";   
const char* topic_status_temp = "dryer/status/temp";     
const char* topic_system_log = "dryer/system/log";       

// ================= 2. 腳位定義 (Pin Definitions) =================
#define RELAY_POWER_PIN D1  
#define RELAY_HOT_PIN   D2  
#define RELAY_COOL_PIN  D0  

// --- 狀態指示燈 ---
#define WIFI_LED_PIN    D4  // Wi-Fi 燈 (內建 LED, Low Active)
#define MQTT_LED_PIN    D7  // ★★★ 新增：MQTT 燈 (外接 LED, 假設 High Active)
// 註：D7 是 MOSI，但 MAX6675 只用 MISO/SCK/CS，所以 D7 空著可以用

// --- MAX6675 溫度模組 ---
#define MAX6675_SCK_PIN D5
#define MAX6675_CS_PIN  D8  
#define MAX6675_SO_PIN  D6  

// ================= 3. 物件初始化 =================
WiFiClient espClient;
PubSubClient client(espClient); 
MAX6675 thermocouple(MAX6675_SCK_PIN, MAX6675_CS_PIN, MAX6675_SO_PIN); 

// ================= 4. 變數宣告 =================
unsigned long lastMsgTime = 0;
const long interval = 2000; 

void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
void reconnect();

// ================= 6. 程式初始化 (Setup) =================
void setup() {
  Serial.begin(115200);
  
  // 設定繼電器
  pinMode(RELAY_POWER_PIN, OUTPUT);
  pinMode(RELAY_HOT_PIN, OUTPUT);
  pinMode(RELAY_COOL_PIN, OUTPUT); 

  // --- 設定 LED 腳位 ---
  pinMode(WIFI_LED_PIN, OUTPUT);
  digitalWrite(WIFI_LED_PIN, HIGH); // Wi-Fi 燈預設滅 (內建是 HIGH 滅)

  pinMode(MQTT_LED_PIN, OUTPUT);    // ★★★ 設定 MQTT 燈為輸出
  digitalWrite(MQTT_LED_PIN, LOW);  // ★★★ MQTT 燈預設滅 (外接是 LOW 滅)

  // 初始化繼電器 (預設關閉)
  digitalWrite(RELAY_POWER_PIN, HIGH);
  digitalWrite(RELAY_HOT_PIN, HIGH); 
  digitalWrite(RELAY_COOL_PIN, HIGH);

  // 設定 Wi-Fi
  setup_wifi();

  // 設定 MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback); 
}

// ================= 7. 主迴圈 (Loop) =================
void loop() {
  // 檢查 MQTT 連線
  if (!client.connected()) {
    // ★★★ 如果斷線，確保燈是滅的
    digitalWrite(MQTT_LED_PIN, LOW); 
    reconnect(); 
  } else {
    // ★★★ 如果連線中，確保燈是亮的
    digitalWrite(MQTT_LED_PIN, HIGH);
  }
  
  client.loop(); 

  // 讀取溫度
  unsigned long now = millis();
  if (now - lastMsgTime > interval) { 
    lastMsgTime = now;
    
    float tempCelsius = thermocouple.readCelsius(); 
    
    if (isnan(tempCelsius)) {
      Serial.println("錯誤：無法讀取熱電偶！");
      // client.publish(topic_system_log, "Error: Thermocouple read failed"); 
    } else {
      Serial.print("目前溫度: ");
      Serial.print(tempCelsius); 
      Serial.println(" C");

      char tempString[8];
      dtostrf(tempCelsius, 1, 2, tempString); 
      client.publish(topic_status_temp, tempString);
    } 
  }
}

// ================= 8. 副程式：Wi-Fi 連線 =================
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("正在連線至 Wi-Fi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA); 
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    // Wi-Fi 連線中：閃爍 D4
    digitalWrite(WIFI_LED_PIN, LOW);  
    delay(250);                       
    digitalWrite(WIFI_LED_PIN, HIGH); 
    delay(250);                       
    Serial.print(".");
  }

  // Wi-Fi 連線成功：D4 恆亮
  digitalWrite(WIFI_LED_PIN, LOW); 

  Serial.println("");
  Serial.println("Wi-Fi 已連線"); 
  Serial.print("IP 位址: ");
  Serial.println(WiFi.localIP());
}

// ================= 9. 副程式：MQTT 訊息處理 =================
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) { 
    message += (char)payload[i];
  } 

  Serial.print("收到訊息 [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);

  // 控制邏輯
  if (String(topic) == topic_control_power) {
    if (message == "ON") digitalWrite(RELAY_POWER_PIN, LOW);
    else if (message == "OFF") digitalWrite(RELAY_POWER_PIN, HIGH);
  }
  else if (String(topic) == topic_control_hot) {
    if (message == "ON") digitalWrite(RELAY_HOT_PIN, LOW);
    else if (message == "OFF") digitalWrite(RELAY_HOT_PIN, HIGH);
  }
  else if (String(topic) == topic_control_cool) {
    if (message == "ON") digitalWrite(RELAY_COOL_PIN, LOW);
    else if (message == "OFF") digitalWrite(RELAY_COOL_PIN, HIGH);
  }
}
// ================= 10. 副程式：MQTT 重連機制 =================
void reconnect() {
  // ★★★ 進入重連迴圈
  while (!client.connected()) {
    Serial.print("正在嘗試連線 MQTT...");
    
    // ★★★ 嘗試連線時，讓 MQTT 燈 (D7) 快閃，表示「正在努力連線中」
    digitalWrite(MQTT_LED_PIN, HIGH);
    delay(100);
    digitalWrite(MQTT_LED_PIN, LOW);
    
    String clientId = "ESP8266Client-";
    clientId += String(random(0xffff), HEX); 
    
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) { 
      Serial.println("已連線");
      // ★★★ 連線成功，燈號在 Loop 迴圈會被鎖定為恆亮，這裡先亮起來
      digitalWrite(MQTT_LED_PIN, HIGH); 
      
      client.subscribe(topic_control_power);
      client.subscribe(topic_control_hot);
      client.subscribe(topic_control_cool); 
    } else {
      Serial.print("失敗, rc=");
      Serial.print(client.state());
      Serial.println(" 5秒後重試");
      
      // ★★★ 失敗等待時，燈滅
      digitalWrite(MQTT_LED_PIN, LOW);
      delay(5000);
    }
  }
}
