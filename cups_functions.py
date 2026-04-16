import asyncio
import socket
import usb.core
import usb.util
import time
from pyipp import IPP, Printer
from zeroconf import ServiceBrowser, Zeroconf
import os
import cups
from DB_fun import save_printers


class PrinterScanner:
    def __init__(self):
        self.found_network_printers = []
        self.found_ips = []  # Added this to fix the AttributeError

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            # Convert addresses from bytes to strings
            for addr in info.addresses:
                ip = socket.inet_ntoa(addr)
                if ip not in self.found_ips:
                    self.found_ips.append(ip)

            clean_name = name.replace("._ipp._tcp.local.", "")
            self.found_network_printers.append(clean_name)

    # Added to fix the 'FutureWarning'
    def update_service(self, zc, type_, name):
        pass

    # Added to handle printer removal if needed
    def remove_service(self, zc, type_, name):
        pass


async def get_truly_online_printers():
    print("Searching for live hardware and resources (5s)...")

    # --- 1. NETWORK DISCOVERY ---
    zc = Zeroconf()
    scanner = PrinterScanner()
    browser = ServiceBrowser(zc, "_ipp._tcp.local.", scanner)
    await asyncio.sleep(5)
    zc.close()

    network_results = []
    # Now scanner.found_ips actually exists!
    for ip in scanner.found_ips:
        try:
            async with IPP(host=ip) as ipp:
                printer: Printer = await ipp.printer()
                # Extract ink/toner levels
                resources = {m.name: f"{m.level}%" for m in printer.markers}
                network_results.append({
                    "name": printer.info.name,
                    "ip": ip,
                    "levels": resources
                })
        except Exception as e:
            network_results.append({"name": ip, "levels": f"Offline or Query Failed: {e}"})

    # --- 2. USB BUS ---
    usb_found = []
    devs = usb.core.find(find_all=True)
    if devs:
        for dev in devs:
            try:
                for cfg in dev:
                    if any(intf.bInterfaceClass == 7 for intf in cfg):
                        name = usb.util.get_string(dev, dev.iProduct) or f"USB_Printer_{dev.idVendor:04x}"
                        usb_found.append({"name": name, "levels": "Query via CUPS/Driver"})
            except:
                continue

    save_printers(network_results, usb_found)
    return {"Network": network_results, "USB": usb_found}
import cups

conn = cups.Connection()

conn = cups.Connection()
for name in conn.getPrinters().keys():
    print(name)
def job(filepath, printer_name, color_mode="Color"):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    conn = cups.Connection()

    # Match display name (e.g. "HP DeskJet 4900 series") to CUPS name (e.g. "HP_DeskJet_4900_series__FAF5A3__...")
    normalized = printer_name.replace(' ', '_')
    cups_name = next((n for n in conn.getPrinters() if n.startswith(normalized)), None)
    if not cups_name:
        raise ValueError(f"No CUPS printer found for: {printer_name}")

    cups_color = "monochrome" if color_mode in ("Black & White", "Grayscale") else "color"
    options = {"print-color-mode": cups_color}

    try:
        print(f"Printing '{filepath}' to: {cups_name} [{cups_color}]")
        job_id = conn.printFile(cups_name, filepath, "My Print Job", options)
        print(f"Success! Job ID: {job_id}. Check the printer tray.")
        return job_id
    except cups.IPPError as e:
        error_code, error_msg = e.args
        print(f"Failed to print — IPP Error {error_code}: {error_msg}")
        raise
# --- EXECUTION ---
if __name__ == "__main__":
    results = asyncio.run(get_truly_online_printers())

    print("\n--- RESULTS ---")
    if not results["Network"] and not results["USB"]:
        print("NO PRINTERS DETECTED. Check power and cables.")
    else:
        for p in results["Network"]:
            print(f"[ONLINE] Network: {p['name']} ({p['ip']}) -> Levels: {p['levels']}")
        for p in results["USB"]:
            print(f"[ONLINE] USB: {p['name']} -> Levels: {p['levels']}")



