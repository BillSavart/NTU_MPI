import subprocess
import csv
import time
import os
from collections import OrderedDict

def scan_wifi():
    """
    使用 nmcli 工具掃描 Wi-Fi 網路，並回傳一個包含 {BSSID: RSSI} 的字典。
    (此函式與前一版相同)
    """
    print("📡  正在掃描 Wi-Fi 網路...")
    try:
        scan_result = subprocess.check_output(
            ['nmcli', '-f', 'BSSID,SIGNAL', 'dev', 'wifi', 'list', '--rescan', 'yes'],
            encoding='utf-8'
        ).strip()

        wifi_data = {}
        lines = scan_result.split('\n')[1:]

        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                bssid = parts[0]
                rssi = parts[1]
                wifi_data[bssid] = int(rssi)
        
        print(f"✅  掃描完成，偵測到 {len(wifi_data)} 個存取點。")
        return wifi_data

    except subprocess.CalledProcessError:
        print("❌  錯誤：無法執行 'nmcli'。請確認 NetworkManager 正在運行。")
        return {}
    except FileNotFoundError:
        print("❌  錯誤：'nmcli' 指令未找到。請確認已安裝。")
        return {}


def main():
    """
    主程式，負責獲取使用者輸入、執行掃描並寫入 CSV。
    此版本會持續運行，直到使用者選擇退出。
    """
    output_filename = 'wifi_data.csv'
    
    # --- 主要修改：加入無限迴圈 ---
    while True:
        print("\n" + "="*40)
        print("      新的測量點 (New Measurement Point)")
        print("="*40)
        
        # 1. 獲取使用者輸入的座標，並提供退出選項
        try:
            x_coord = input("請輸入 X 座標 (cm) [或輸入 'q' 結束]: ")
            # --- 主要修改：檢查是否要退出 ---
            if x_coord.lower() == 'q':
                break

            y_coord = input("請輸入 Y 座標 (cm) [或輸入 'q' 結束]: ")
            # --- 主要修改：檢查是否要退出 ---
            if y_coord.lower() == 'q':
                break

        except KeyboardInterrupt:
            print("\n操作已取消。")
            break

        # 2. 獲取當前 Unix timestamp
        current_timestamp = int(time.time())

        # 3. 執行 Wi-Fi 掃描
        rssi_values = scan_wifi()
        if not rssi_values:
            print("未掃描到任何 Wi-Fi 訊號，請移動到訊號更好的位置再試。")
            continue # 繼續下一次迴圈

        # 4. 準備要寫入 CSV 的資料列
        row_data = OrderedDict()
        row_data['timestamp'] = current_timestamp
        row_data['x'] = x_coord
        row_data['y'] = y_coord
        
        for bssid, rssi in rssi_values.items():
            row_data[bssid] = rssi

        # 5. 寫入 CSV 檔案 (處理動態欄位的邏輯與前一版相同)
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
            print("📝  偵測到新的 BSSID，正在更新 CSV 檔案結構...")
            with open(output_filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                old_data = list(reader)
            
            # 建立所有欄位的聯集
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
    main()