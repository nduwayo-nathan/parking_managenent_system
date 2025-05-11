#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9
#define SS_PIN 10

MFRC522 rfid(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

enum Mode { IDLE, READ_UID, WRITE_DATA, READ_DATA, PROCESS_PAYMENT };
Mode currentMode = IDLE;

void setup() {
  Serial.begin(9600);
  while (!Serial); // Wait for serial to initialize
  SPI.begin();
  rfid.PCD_Init();
  
  // Prepare the default key
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;
  }
  
  showMenu();
}

void loop() {
  // Check for mode selection
  if (Serial.available() > 0) {
    processUserInput();
  }
  
  // If in IDLE mode, don't process RFID
  if (currentMode == IDLE) {
    return;
  }
  
  // Check for RFID card only if a mode is selected
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Execute the selected mode
  switch(currentMode) {
    case READ_UID:
      readUIDMode();
      break;
    case WRITE_DATA:
      writeDataMode();
      break;
    case READ_DATA:
      readDataMode();
      break;
    case PROCESS_PAYMENT:
      processPaymentMode();
      break;
    default:
      break;
  }

  // Halt PICC and stop encryption
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  delay(500);
  
  // Return to menu after operation
  currentMode = IDLE;
  showMenu();
}

void processUserInput() {
  char input = Serial.read();
  switch(input) {
    case '1':
      currentMode = READ_UID;
      Serial.println("\nSelected: Read UID Mode");
      Serial.println("Scan an RFID card to read its UID...");
      break;
    case '2':
      currentMode = WRITE_DATA;
      Serial.println("\nSelected: Write Data Mode");
      Serial.println("Enter data to write (16 chars max):");
      while (!Serial.available()); // Wait for input
      break;
    case '3':
      currentMode = READ_DATA;
      Serial.println("\nSelected: Read Data Mode");
      Serial.println("Scan an RFID card to read its data...");
      break;
    case '4':
      currentMode = PROCESS_PAYMENT;
      Serial.println("\nSelected: Payment Processing Mode");
      Serial.println("Scan an RFID card to process payment...");
      break;
    case 'm':
      currentMode = IDLE;
      showMenu();
      break;
    default:
      Serial.println("Invalid option!");
      showMenu();
      break;
  }
}

void showMenu() {
  Serial.println("\n--------------------------------");
  Serial.println("    RFID Parking System");
  Serial.println("--------------------------------");
  Serial.println("1. Read Card UID");
  Serial.println("2. Write Data to Card");
  Serial.println("3. Read Data from Card");
  Serial.println("4. Process Payment");
  Serial.println("m. Show this menu");
  Serial.println("--------------------------------");
  Serial.print("Enter your choice (1-4 or m): ");
}

void readUIDMode() {
  Serial.print("Card UID:");
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i] < 0x10 ? " 0" : " ");
    Serial.print(rfid.uid.uidByte[i], HEX);
  }
  Serial.println();
}

void writeDataMode() {
  String dataToWrite = Serial.readStringUntil('\n');
  dataToWrite.trim();
  if (dataToWrite.length() > 16) {
    dataToWrite = dataToWrite.substring(0, 16);
    Serial.println("Truncated to 16 characters");
  }

  // Authenticate for sector 1
  byte blockAddr = 4;
  MFRC522::StatusCode status = rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(rfid.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Authentication failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }

  // Write data to block 4
  byte buffer[16];
  for (byte i = 0; i < 16; i++) {
    buffer[i] = (i < dataToWrite.length()) ? dataToWrite[i] : ' ';
  }
  
  Serial.print("Writing data to card...");
  status = rfid.MIFARE_Write(blockAddr, buffer, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Write failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }
  Serial.println(" Done");
  Serial.println("Data written successfully!");
}

void readDataMode() {
  // Authenticate for sector 1
  byte blockAddr = 4;
  MFRC522::StatusCode status = rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(rfid.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Authentication failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }

  // Read data from block 4
  byte buffer[18];
  byte size = 18;
  status = rfid.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Read failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }
  
  Serial.print("Card Data: ");
  for (byte i = 0; i < 16; i++) {
    Serial.print((char)buffer[i]);
  }
  Serial.println();
}

void processPaymentMode() {
  // Authenticate for sector 1
  byte blockAddr = 4;
  MFRC522::StatusCode status = rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, blockAddr, &key, &(rfid.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Authentication failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }

  // Read current balance from block 4
  byte buffer[18];
  byte size = 18;
  status = rfid.MIFARE_Read(blockAddr, buffer, &size);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Read failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }
  
  String balanceStr = "";
  for (byte i = 0; i < 16; i++) {
    if (buffer[i] != ' ') balanceStr += (char)buffer[i];
  }
  long currentBalance = balanceStr.toInt();

  Serial.print("Current Balance: ");
  Serial.println(currentBalance);
  
  Serial.println("Enter payment amount:");
  while (!Serial.available()); // Wait for input
  long payment = Serial.parseInt();
  
  if (payment <= 0) {
    Serial.println("Invalid payment amount!");
    return;
  }

  if (payment > currentBalance) {
    Serial.println("Insufficient funds!");
    return;
  }

  // Calculate new balance
  long newBalance = currentBalance - payment;
  
  // Write new balance to card
  String newBalanceStr = String(newBalance);
  for (byte i = 0; i < 16; i++) {
    buffer[i] = (i < newBalanceStr.length()) ? newBalanceStr[i] : ' ';
  }
  
  status = rfid.MIFARE_Write(blockAddr, buffer, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Write failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }

  Serial.println("Payment processed successfully!");
  Serial.print("New Balance: ");
  Serial.println(newBalance);
}