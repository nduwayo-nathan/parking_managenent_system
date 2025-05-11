import cv2
import time
import serial
import csv
from datetime import datetime
from collections import Counter
from plate_utils import detect_plate

# Configuration
CSV_FILE = 'plates_log.csv'

# Arduino connection (same as entry)
arduino = connect_arduino()  # Using same function from car_entry.py

def verify_payment(plate):
    """Check if plate has paid and not yet exited"""
    if not os.path.exists(CSV_FILE):
        return False
    
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row['Plate Number'] == plate and 
                row['Payment Status'] == '1' and 
                row['Exit Timestamp'] == ''):
                return True
    return False

def log_exit(plate):
    """Log vehicle exit to CSV"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = []
    
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Plate Number'] == plate and row['Exit Timestamp'] == '':
                row['Exit Timestamp'] = timestamp
            rows.append(row)
    
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# Main loop
cap = cv2.VideoCapture(0)
plate_buffer = []

print("[EXIT SYSTEM] Ready. Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Mock distance sensor
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
                plate_buffer.clear()
                
                if verify_payment(most_common):
                    print(f"[ACCESS GRANTED] Payment verified for {most_common}")
                    log_exit(most_common)
                    control_gate('1')  # Open gate
                    time.sleep(15)
                    control_gate('0')  # Close gate
                else:
                    print(f"[ACCESS DENIED] Payment not verified for {most_common}")
                    if arduino:
                        arduino.write(b'2')  # Sound buzzer
                        print("[ALERT] Buzzer activated")

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if arduino:
    arduino.close()
cv2.destroyAllWindows()