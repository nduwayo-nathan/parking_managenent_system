import os
import cv2
import time
import serial
import csv
from datetime import datetime
from collections import Counter
from plate_utils import detect_plate

# Configuration
CSV_FILE = 'plates_log.csv'
ENTRY_COOLDOWN = 300  # 5 minutes in seconds

# Initialize CSV if not exists
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Plate Number', 'Entry Timestamp', 'Exit Timestamp', 
                        'Payment Status', 'Payment Timestamp', 'Amount Paid'])

# Arduino connection
def connect_arduino():
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "COM" in port.device or "wchusbmodem" in port.device:
            try:
                arduino = serial.Serial(port.device, 9600, timeout=1)
                time.sleep(2)
                print(f"[CONNECTED] Arduino on {port.device}")
                return arduino
            except:
                continue
    print("[ERROR] Arduino not detected.")
    return None

arduino = connect_arduino()

def log_entry(plate):
    """Log vehicle entry to CSV"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([plate, timestamp, '', 0, '', ''])  # 0 for unpaid

def control_gate(action):
    """Control gate mechanism"""
    if arduino:
        arduino.write(action.encode())
        print(f"[GATE] {'Opening' if action == '1' else 'Closing'} gate")

# Main loop
cap = cv2.VideoCapture(0)
plate_buffer = []
last_plate = None
last_entry_time = 0

print("[ENTRY SYSTEM] Ready. Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Mock distance sensor (replace with actual sensor reading)
    distance = random.choice([random.randint(10, 40)] + [random.randint(60, 150)] * 10)
    print(f"[SENSOR] Distance: {distance} cm")

    if distance <= 50:  # Vehicle detected
        plates = detect_plate(frame)
        
        for plate_data in plates:
            plate = plate_data['plate']
            print(f"[DETECTED] Plate: {plate}")
            plate_buffer.append(plate)
            
            # Show detected plate
            cv2.imshow("Detected Plate", plate_data['image'])
            cv2.imshow("Processed Plate", plate_data['processed'])
            
            # After 3 consistent readings
            if len(plate_buffer) >= 3:
                most_common = Counter(plate_buffer).most_common(1)[0][0]
                current_time = time.time()
                
                # Check if new entry or cooldown passed
                if (most_common != last_plate or 
                    (current_time - last_entry_time) > ENTRY_COOLDOWN):
                    
                    log_entry(most_common)
                    control_gate('1')  # Open gate
                    time.sleep(15)
                    control_gate('0')  # Close gate
                    
                    last_plate = most_common
                    last_entry_time = current_time
                else:
                    print("[SKIPPED] Duplicate within cooldown period")
                
                plate_buffer.clear()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if arduino:
    arduino.close()
cv2.destroyAllWindows()