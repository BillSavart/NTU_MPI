import re
import logging
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s %(levelname)s]: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NetworkInfo:
  """Data class to represent WiFi network information."""
  bssid: str
  signal_strength: int
  essid: Optional[str] = None
  encryption: Optional[str] = None
  frequency: Optional[str] = None
  last_seen: datetime = None
  
  def __post_init__(self):
    if self.last_seen is None:
      self.last_seen = datetime.now()

class WiFiScanner:
  """WiFi scanner with improved error handling and structure."""
  
  def __init__(self, interface: str = None, scan_interval: float = 10.0):
    self.interface = interface
    self.scan_interval = scan_interval
    self.wifi_data: Dict[str, NetworkInfo] = {}
    self._scan_task: Optional[asyncio.Task] = None
    self._running = False
    
  async def scan_wifi_once(self) -> Dict[str, NetworkInfo]:
      """
      Perform a single WiFi scan and return network information.
      
      Returns:
          Dictionary mapping BSSID to NetworkInfo objects
      """
      loop = asyncio.get_event_loop()
      return await loop.run_in_executor(None, self._scan_wifi_sync)
  
  def _scan_wifi_sync(self) -> Dict[str, NetworkInfo]:
    """
    Synchronous WiFi scanning function.
    
    Returns:
      Dictionary mapping BSSID to NetworkInfo objects
    """
    try:
      # Build command
      cmd = ['sudo', 'iwlist']
      if self.interface:
        cmd.append(self.interface)
      cmd.append('scan')
      
      # Execute scan
      result = subprocess.check_output(
        cmd, 
        stderr=subprocess.STDOUT, 
        timeout=30  # Add timeout
      ).decode('utf-8', errors='replace')
      
      return self._parse_scan_results(result)
        
    except subprocess.CalledProcessError as e:
      logger.error(f"[WiFiScanner] WiFi scan command failed: {e}")
      return {}
    except subprocess.TimeoutExpired:
      logger.error(f"[WiFiScanner] WiFi scan timed out")
      return {}
    except Exception as e:
      logger.error(f"[WiFiScanner] Unexpected error during WiFi scan: {e}")
      return {}
  
  def _parse_scan_results(self, scan_output: str) -> Dict[str, NetworkInfo]:
    """
    Parse iwlist scan output into structured data.
    
    Args:
      scan_output: Raw output from iwlist scan
        
    Returns:
      Dictionary mapping BSSID to NetworkInfo objects
    """
    networks = {}
    
    # Split into cells
    cells = re.split(r'Cell \d+ - ', scan_output)[1:]
    
    for cell in cells:
      try:
        network_info = self._parse_cell(cell)
        if network_info and network_info.bssid:
          networks[network_info.bssid] = network_info
      except Exception as e:
        logger.warning(f"[WiFiScanner] Failed to parse cell data: {e}")
        continue
    
    return networks
  
  def _parse_cell(self, cell_data: str) -> Optional[NetworkInfo]:
    """
    Parse individual cell data into NetworkInfo object.
    
    Args:
      cell_data: Raw cell data from iwlist
        
    Returns:
      NetworkInfo object or None if parsing fails
    """
    # Extract BSSID (MAC address)
    bssid_match = re.search(r'Address: ([0-9A-Fa-f:]{17})', cell_data)
    if not bssid_match:
      return None
    bssid = bssid_match.group(1)
    
    # Extract signal strength
    signal_match = re.search(r'Signal level=(-?\d+)', cell_data)
    signal_strength = int(signal_match.group(1)) if signal_match else -100
    
    # Extract ESSID (network name)
    essid_match = re.search(r'ESSID:"([^"]*)"', cell_data)
    essid = essid_match.group(1) if essid_match else None
    
    # Extract encryption info
    encryption = "Open"
    if re.search(r'Encryption key:on', cell_data):
      if re.search(r'IE:.*WPA2', cell_data):
        encryption = "WPA2"
      elif re.search(r'IE:.*WPA', cell_data):
        encryption = "WPA"
      else:
        encryption = "WEP"
    
    # Extract frequency
    freq_match = re.search(r'Frequency:([\d.]+) GHz', cell_data)
    frequency = f"{freq_match.group(1)} GHz" if freq_match else None
    
    return NetworkInfo(
      bssid=bssid,
      signal_strength=signal_strength,
      essid=essid,
      encryption=encryption,
      frequency=frequency
    )
  
  async def start_continuous_scan(self):
    """Start continuous WiFi scanning in the background."""
    if self._running:
      logger.warning("[WiFiScanner] WiFi scanner is already running")
      return
    
    self._running = True
    self._scan_task = asyncio.create_task(self._scan_loop())
    logger.info(f"[WiFiScanner] Started WiFi scanning with {self.scan_interval}s interval")

  async def stop_continuous_scan(self):
    """Stop continuous WiFi scanning."""
    if not self._running or not self._scan_task:
      return
    
    self._running = False
    self._scan_task.cancel()
    
    try:
      await self._scan_task
    except asyncio.CancelledError:
      pass
    
    logger.info("[WiFiScanner] Stopped WiFi scanning")
  
  async def _scan_loop(self):
    """Main scanning loop that runs continuously."""
    while self._running:
      try:
        scan_results = await self.scan_wifi_once()
        if scan_results:
          self.wifi_data.update(scan_results)
          logger.debug(f"[WiFiScanner] Found {len(scan_results)} networks")
        else:
          logger.warning("[WiFiScanner] WiFi scan returned no results")
        
        # Wait before next scan
        await asyncio.sleep(self.scan_interval)
          
      except asyncio.CancelledError:
        break
      except Exception as e:
        logger.error(f"[WiFiScanner] Error in scan loop: {e}")
        await asyncio.sleep(self.scan_interval)
  
  def get_networks(self, min_signal: int = -100) -> Dict[str, NetworkInfo]:
    """
    Get current network data filtered by signal strength.
    
    Args:
      min_signal: Minimum signal strength to include
        
    Returns:
      Dictionary of networks meeting signal threshold
    """
    return {
      bssid: info for bssid, info in self.wifi_data.items()
      if info.signal_strength >= min_signal
    }
  
  def get_strongest_networks(self, count: int = 5) -> Dict[str, NetworkInfo]:
    """
    Get the strongest networks by signal strength.
    
    Args:
      count: Number of networks to return
        
    Returns:
      Dictionary of strongest networks
    """
    sorted_networks = sorted(
      self.wifi_data.items(),
      key=lambda x: x[1].signal_strength,
      reverse=True
    )
    return dict(sorted_networks[:count])
