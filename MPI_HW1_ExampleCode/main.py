import board
import logging
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
from adafruit_as7341 import AS7341
from WiFiScanner import WiFiScanner
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='[%(asctime)s %(levelname)s]: %(message)s')
logger = logging.getLogger(__name__)

COORDINATES = (0, 0)
COLLECTION_INTERVAL = 60  # seconds
WIFI_SCAN_INTERVAL = 30  # seconds
BASE_FOLDER = Path("./data/") 
MODALITY = {
  "light": "light_data.csv",
  "wifi": "wifi_data.csv",
  # "ble": "ble_data.csv",
}

BASE_FOLDER.mkdir(exist_ok=True)
try:
  i2c = board.I2C()
  lightSensor = AS7341(i2c)
  logger.info("Light sensor initialized successfully.")
except Exception as e:
  lightSensor = None
  logger.error(f"Failed to initialize light sensor: {e}")

wifiScanner = WiFiScanner(interface='wlan0', scan_interval=WIFI_SCAN_INTERVAL)

def loadData(file: str) -> pd.DataFrame:
  """Load existing data from CSV file."""
  filepath = BASE_FOLDER / file
  try:
    df = pd.read_csv(filepath)
    logger.info(f"Loaded {len(df)} rows from {file}.")
    return df
  except FileNotFoundError:
    logger.info(f"Creating new file: {file}.")
    return pd.DataFrame()
  except Exception as e:
    logger.error(f"Error loading {file}: {e}")
    return pd.DataFrame()

def saveData(file: str, df: pd.DataFrame) -> bool:
  """Save DataFrame to CSV file."""
  filepath = BASE_FOLDER / file
  try:
    df.to_csv(filepath, index=False)
    logger.debug(f"Saved {len(df)} rows to {file}")
    return True
  except Exception as e:
    logger.error(f"Error saving {file}: {e}")
    return False

def appendData(file: str, data: pd.Series | dict) -> bool:
  """Append new data row to existing CSV file."""
  if data is None:
    return False
  
  try:
    df = loadData(file)
    new_row = pd.DataFrame([data])
    df = pd.concat([df, new_row], ignore_index=True)
    return saveData(file, df)
  except Exception as e:
    logger.error(f"Error appending data to {file}: {e}")
    return False

async def read_light() -> Optional[Dict[str, int]]:
  """Read data from light sensor."""
  if not lightSensor:
    logger.warning("Light sensor not available")
    return None
  
  try:
    channels = lightSensor.all_channels
    return {f"f{i}": val for i, val in enumerate(channels, 1)}
  except Exception as e:
    logger.error(f"Error reading light sensor: {e}")
    return None

async def read_wifi() -> Optional[Dict[str, int]]:
  """Read WiFi signal strength data."""
  try:
    networks = wifiScanner.get_networks()

    # Optional: Limit to strongest networks to avoid huge datasets
    # networks = wifiScanner.get_strongest_networks(20)

    if not networks:
      logger.warning("No WiFi networks detected")
      return {}
    
    return {bssid: info.signal_strength for bssid, info in networks.items()}
  except Exception as e:
    logger.error(f"Error reading WiFi data: {e}")
    return None

def add_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
  """Add timestamp and coordinates to data."""
  if data is None:
    return None
  
  data.update({
    "timestamp": pd.Timestamp.now().isoformat(),
    "x": COORDINATES[0],
    "y": COORDINATES[1],
  })
  return data

async def collect_reading(collection_count: int) -> Dict[str, bool]:
  """Collect one reading from all sensors."""
  results = {}
  
  # Read light sensor
  light_data = await read_light()
  if light_data:
    light_data = add_metadata(light_data)
    results['light'] = appendData(MODALITY["light"], light_data)
    logger.debug("Light data collected")
  else:
    results['light'] = False
  
  # Read WiFi data
  wifi_data = await read_wifi()
  if wifi_data is not None:
    wifi_data = add_metadata(wifi_data)
    results['wifi'] = appendData(MODALITY["wifi"], wifi_data)
    logger.debug(f"WiFi data collected ({len(wifi_data)-3} networks)")
  else:
    results['wifi'] = False
  
  success_count = sum(results.values())
  logger.info(f"Reading #{collection_count}: {success_count}/{len(results)} sensors successful")
  
  return results

async def main():
  """Main function to run the sensor data collector."""
  logger.info(f"Starting sensor data collection (interval: {COLLECTION_INTERVAL}s)")
  logger.info(f"Coordinates: {COORDINATES}")
  logger.info(f"Data folder: {BASE_FOLDER.absolute()}")
  
  collection_count = 0
  start_time = datetime.now()

  try:
    await wifiScanner.start_continuous_scan()
    logger.info("WiFi scanner started")

    await asyncio.sleep(10)  # Give it a moment for the first scan to complete

    while True:
      try:
        collection_count += 1
        await collect_reading(collection_count)
                
        # Sleep until next reading
        await asyncio.sleep(COLLECTION_INTERVAL)
                
      except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping collection...")
        break
      except Exception as e:
        logger.error(f"Error during data collection: {e}")
        await asyncio.sleep(COLLECTION_INTERVAL)  # Continue after errors

  finally:        
    total_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Collection stopped. Total readings: {collection_count}, "
                f"Total time: {total_time:.0f}s")
    
    await wifiScanner.stop_continuous_scan()
    logger.info("WiFi scanner stopped")

if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    print("\nShutdown complete.")
  except Exception as e:
    logger.error(f"Fatal error: {e}")
    raise
