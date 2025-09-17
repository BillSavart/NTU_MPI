# python3 -m venv ble_env
# source ble_env/bin/activate
# pip install bleak
#sudo apt update
#sudo apt install bluetooth bluez libglib2.0-dev

#sudo /home/team8/ble_env/bin/python3 ble.py
import asyncio
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import csv
import time
import os
from collections import OrderedDict
import sys

# --- 這是主要修正的部分 ---
async def scan_ble(scan_duration: int = 5):
    """
    使用 bleak 函式庫和 callback 機制來非同步掃描 BLE 裝置。
    這個版本能正確獲取 RSSI。
    """
    print(f"📡  正在掃描 BLE 裝置 (持續 {scan_duration} 秒)...")
    
    ble_data = {}

    # 我們需要一個 callback 函式來處理每一個收到的廣播封包
    # 這是 bleak 函式庫推薦的、最可靠的掃描方式
    def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
        # 注意：RSSI 在 advertisement_data 中，而不是 device 物件中！
        # 這就是之前錯誤的根源。
        ble_data[device.address] = advertisement_data.rssi

    try:
        # 建立掃描器並註冊我們的 callback 函式
        scanner = BleakScanner(detection_callback=detection_callback)
        
        # 手動啟動、等待、停止掃描
        await scanner.start()
        await asyncio.sleep(scan_duration)
        await scanner.stop()
        
        if ble_data:
            print(f"✅  掃描完成，偵測到 {len(ble_data)} 個 BLE 裝置。")
        else:
            # 如果 scanner.discovered_devices 有東西但 ble_data 是空的，
            # 表示可能藍牙服務有問題，沒有回傳 advertisement_data
            if scanner.discovered_devices:
                print("⚠️  偵測到裝置，但無法獲取 RSSI。請檢查藍牙服務或權限。")
            else:
                print("✅  掃描完成，周圍未發現 BLE 裝置。")

        return ble_data

    except Exception as e:
        print(f"❌  掃描 BLE 時發生錯誤: {e}")
        print("    請嘗試使用 'sudo' 執行此腳本，或檢查藍牙服務是否已啟用。")
        return {}
# --- 修正部分結束 ---


def main():
    """
    主程式，負責獲取使用者輸入、執行 BLE 掃描並寫入 CSV。
    (此函式無需修改)
    """
    output_filename = 'ble_data.csv'
    
    while True:
        print("\n" + "="*40)
        print("      新的 BLE 測量點 (New Measurement Point)")
        print("="*40)
        
        try:
            x_coord = input("請輸入 X 座標 (cm) [或輸入 'q' 結束]: ")
            if x_coord.lower() == 'q':
                break
            y_coord = input("請輸入 Y 座標 (cm) [或輸入 'q' 結束]: ")
            if y_coord.lower() == 'q':
                break
        except KeyboardInterrupt:
            print("\n操作已取消。")
            break

        current_timestamp = int(time.time())
        rssi_values = asyncio.run(scan_ble())
        
        if not rssi_values:
            print("本次掃描未記錄任何數據。")
            continue

        # (CSV 寫入邏輯與之前相同，無需修改)
        row_data = OrderedDict()
        row_data['timestamp'] = current_timestamp
        row_data['x'] = x_coord
        row_data['y'] = y_coord
        for address, rssi in rssi_values.items():
            row_data[address] = rssi

        file_exists = os.path.isfile(output_filename)
        all_headers = []
        if file_exists and os.path.getsize(output_filename) > 0:
            with open(output_filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                try:
                    all_headers = next(reader)
                except StopIteration:
                    file_exists = False
        else:
            file_exists = False

        current_headers = list(row_data.keys())
        new_headers_found = any(h not in all_headers for h in current_headers)

        if new_headers_found and file_exists:
            print("📝  偵測到新的 BLE 裝置，正在更新 CSV 檔案結構...")
            with open(output_filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                old_data = list(reader)
            
            final_headers = all_headers + [h for h in current_headers if h not in all_headers]
            old_data.append(row_data)

            with open(output_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=final_headers)
                writer.writeheader()
                writer.writerows(old_data)
        else:
            final_headers = all_headers if file_exists else current_headers
            with open(output_filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=final_headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row_data)

        print(f"🎉  成功將資料儲存至 {output_filename}！")
    
    print("\n程式已結束，所有資料均已儲存。")


if __name__ == '__main__':
    if os.geteuid() != 0:
        print("警告：建議使用 'sudo' 執行此腳本，以確保有足夠的權限掃描藍牙。")
        print(f"嘗試執行: sudo {sys.executable} {' '.join(sys.argv)}")
    main()