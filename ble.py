import bluepy.btle as btle
import time
import sys

# Specific device address
TARGET_DEVICE = "c9:a3:d9:cb:02:b3"
DEVICE_NAME = "A_Minh"

# LBS Service UUID
LBS_UUID = "00001523-1212-efde-1523-785feabcd123"

class MyDelegate(btle.DefaultDelegate):
    def __init__(self):
        super().__init__()
        print("Delegate is ready to receive notifications")
        
    def handleNotification(self, handle, data):
        value = int.from_bytes(data, byteorder='little')
        print(f"?? Sensor data: {value}")
        
    def handleIndication(self, handle, data):
        value = int.from_bytes(data, byteorder='little')
        print(f"?? Button: {'PRESSED' if value else 'RELEASED'}")
        
def direct_connect():
    print(f"Connecting directly to {DEVICE_NAME} ({TARGET_DEVICE})...")
    
    try:
        dev = btle.Peripheral(TARGET_DEVICE, btle.ADDR_TYPE_RANDOM)
        print("? Successfully connected (random address)")
        return dev
    except:
        try:
            dev = btle.Peripheral(TARGET_DEVICE, btle.ADDR_TYPE_PUBLIC)
            print("? Successfully connected (public address)")
            return dev
        except Exception as e:
            print(f"? Connection error: {e}")
            return None

def setup_characteristics(dev):
    button_char = None
    led_char = None
    sensor_char = None

    print("\n?? Searching for services and characteristics...")

    for service in dev.getServices():
        print(f"Service: {service.uuid}")

        for char in service.getCharacteristics():
            props = []
            if char.properties & 0x02:
                props.append("READ")
            if char.properties & 0x08:
                props.append("WRITE")
            if char.properties & 0x10:
                props.append("NOTIFY")
            if char.properties & 0x20:
                props.append("INDICATE")

            print(f"  Characteristic: {char.uuid}")
            print(f"    Handle: {char.getHandle()}, Properties: {', '.join(props)}")

            if "INDICATE" in props:
                button_char = char
                print("    ? This is the Button characteristic")
            elif "WRITE" in props:
                led_char = char
                print("    ? This is the LED characteristic")
            elif "NOTIFY" in props:
                sensor_char = char
                print("    ? This is the Sensor characteristic")

    return button_char, led_char, sensor_char


def main():
    print("=== Connecting to A_Minh ===")
    
    dev = direct_connect()
    if not dev:
        print("Unable to connect. Exiting program...")
        sys.exit(1)
    
    dev.setDelegate(MyDelegate())
    
    try:
        button_char, led_char, sensor_char = setup_characteristics(dev)
        
        # Enable notifications for sensor
        if sensor_char:
            print("\n>> Enabling notifications for sensor...")
            dev.writeCharacteristic(sensor_char.getHandle() + 1, b"\x01\x00")
        
        # Enable indications for button
        if button_char:
            print(">> Enabling indications for button...")
            dev.writeCharacteristic(button_char.getHandle() + 1, b"\x02\x00")
        
        print("\n>> Setup complete!")
        print(">> Listening for data from the device...")
        print(">> Controlling LED every 3 seconds")
        print(">> Press Ctrl+C to exit")
        
        led_state = False
        counter = 0

        while True:
            if dev.waitForNotifications(1.0):
                continue

            # Keep-alive read every 10 seconds if possible
            if counter % 10 == 0:
                try:
                    if sensor_char and (sensor_char.properties & btle.Characteristic.PROP_READ):
                        value = sensor_char.read()
                        print(f">> Keep-alive read: {value}")
                except Exception as e:
                    print(f">> Keep-alive failed: {e}")

            # Control LED every 3 seconds
            if int(time.time()) % 3 == 0:
                if led_char:
                    led_state = not led_state
                    value = b'\x01' if led_state else b'\x00'
                    dev.writeCharacteristic(led_char.getHandle(), value)
                    print(f">> LED: {'ON' if led_state else 'OFF'}")
                    time.sleep(1)
            
            counter += 1
    
    except KeyboardInterrupt:
        print("\n>> Stopped by user")
    
    except btle.BTLEDisconnectError:
        print("\n>> Device disconnected")
    
    except Exception as e:
        print(f"\n>> Error: {e}")
    
    finally:
        try:
            dev.disconnect()
            print(">> Disconnected successfully")
        except:
            pass

if __name__ == "__main__":
    main()