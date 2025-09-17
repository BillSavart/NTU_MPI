#cd /home/team8
#python3 -m venv .venv
#source .venv/bin/activate
#(.venv) team8@team8:~ $ pip install adafruit-blinka adafruit-circuitpython-as7341

import time
import csv
import os
import board
import adafruit_as7341

def setup_sensor():
    """初始化並回傳 AS7341 感測器物件。"""
    try:
        i2c = board.I2C()  # 使用預設的 I2C
        sensor = adafruit_as7341.AS7341(i2c)
        print("✅  AS7341 感測器連接成功！")
        return sensor
    except ValueError:
        print("❌  錯誤：找不到 I2C 設備。請檢查感測器接線與 I2C 是否已啟用。")
        return None
    except Exception as e:
        print(f"❌  發生未知錯誤：{e}")
        return None

def main():
    """主程式，執行資料收集流程。"""
    sensor = setup_sensor()
    if not sensor:
        return # 如果感測器設定失敗，則結束程式

    output_filename = 'light_data.csv'

    # --- 主要程式迴圈，可持續測量 ---
    while True:
        print("\n" + "="*40)
        print("      新的光譜測量點 (New Light Measurement)")
        print("="*40)
        
        try:
            # 1. 獲取使用者輸入的座標
            x_coord_str = input("請輸入 X 座標 (cm) [或輸入 'q' 結束]: ")
            if x_coord_str.lower() == 'q':
                break

            y_coord_str = input("請輸入 Y 座標 (cm) [或輸入 'q' 結束]: ")
            if y_coord_str.lower() == 'q':
                break
                
            x_coord = int(x_coord_str)
            y_coord = int(y_coord_str)

        except ValueError:
            print("❌  座標輸入無效，請輸入數字。")
            continue # 重新開始迴圈
        except KeyboardInterrupt:
            break # 允許使用 Ctrl+C 中斷

        # 2. 獲取當前 Unix timestamp
        current_timestamp = int(time.time())
        
        print("💡  正在讀取光譜數據...")

        # 3. 準備要寫入的資料列
        # 欄位名稱完全依照您的要求
        headers = [
            'timestamp', 'x', 'y', 
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 
            'clear', 'nir'
        ]
        
        # 將感測器讀值對應到 f1-f8 等欄位
        row_data = {
            'timestamp': current_timestamp,
            'x': x_coord,
            'y': y_coord,
            'f1': sensor.channel_415nm, # Violet
            'f2': sensor.channel_445nm, # Indigo
            'f3': sensor.channel_480nm, # Blue
            'f4': sensor.channel_515nm, # Cyan
            'f5': sensor.channel_555nm, # Green
            'f6': sensor.channel_590nm, # Yellow
            'f7': sensor.channel_630nm, # Orange
            'f8': sensor.channel_680nm, # Red
            'clear': sensor.channel_clear,
            'nir': sensor.channel_nir,
        }

        # 4. 將資料寫入 CSV 檔案
        try:
            # 檢查檔案是否存在，若不存在則先寫入標頭
            file_exists = os.path.isfile(output_filename)
            
            with open(output_filename, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                
                if not file_exists or os.path.getsize(output_filename) == 0:
                    writer.writeheader()  # 如果檔案是空的或剛建立，寫入標頭
                
                writer.writerow(row_data)
            
            print(f"🎉  成功將資料儲存至 {output_filename}！")

        except IOError:
            print(f"❌  錯誤：無法寫入檔案 {output_filename}。請檢查權限。")

    print("\n程式已結束，所有資料均已儲存。")


if __name__ == '__main__':
    main()

#timestamp: 1758085813
# 意義：這是 Unix 時間戳，代表從 1970 年 1 月 1 日午夜到測量當下的總秒數。
# 換算成人類可讀時間：這個時間戳對應到 2025年 9月 17日 星期三 13:10:13。這證明了您的程式成功獲取了當下的時間。

# x: 1 和 y: 1
# 意義：這是您在程式提示時所輸入的 X 和 Y 座標。它記錄了這次光譜測量的物理位置是在 (1 cm, 1 cm)。

# f1 到 f8: 光譜數據
# 意義：這些是 AS7341 感測器的核心讀數，代表不同顏色（波長）光線的強度。數值越大，代表該顏色的光線越強。

# 各通道對應：
# f1: 1302 → 415nm (紫色光)
# f2: 10469 → 445nm (靛色光)
# f3: 9157 → 480nm (藍色光)
# f4: 10811 → 515nm (青色光)
# f5: 15633 → 555nm (綠色光)
# f6: 17140 → 590nm (黃色光)
# f7: 12434 → 630nm (橘色光)
# f8: 7685 → 680nm (紅色光)

# 從數據看：在這次測量中，環境光線的黃綠色部分 (f5, f6) 的強度最高。
# clear: 48996

# 意義：這是「Clear」通道的讀數，它測量的是不經過任何濾光片的總可見光強度。您可以把它看作是環境的整體亮度。48996 是一個相當高的數值，表示當時環境是明亮的。
# nir: 3009
# 意義：這是「Near-Infrared (NIR)」通道的讀數，代表近紅外線的強度。這是人眼看不到，但感測器可以偵測到的光線。