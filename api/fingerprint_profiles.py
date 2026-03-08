#!/usr/bin/env python3
"""
Enhanced Device Fingerprint Profiles for SheerID Verification

This module provides 70+ realistic hardware fingerprint profiles for bypassing
IPQS (IPQualityScore) fraud detection during SheerID student verification.

Features:
- 70+ real device configurations (gaming PCs, laptops, MacBooks, workstations)
- OS-specific font lists (Windows 70+ fonts, macOS 55+ fonts)
- Proper GPU renderer strings for NVIDIA, AMD, Intel, Apple
- US timezone rotation (6 timezones)
- Weighted profile selection (common devices appear more often)
"""

import random
import hashlib
import json
import time

# =============================================================================
# REALISTIC HARDWARE FINGERPRINT PROFILES - 70+ Real Device Configurations
# =============================================================================

# Desktop Gaming PCs - High End
GAMING_HIGH_END = [
    {'name': 'Gaming PC - RTX 4090', 'screen': [2560, 1440], 'gpu': 'NVIDIA GeForce RTX 4090', 'gpu_id': '0x00002684', 'cores': 16, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 4080 SUPER', 'screen': [3440, 1440], 'gpu': 'NVIDIA GeForce RTX 4080 SUPER', 'gpu_id': '0x00002702', 'cores': 16, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 4080', 'screen': [2560, 1440], 'gpu': 'NVIDIA GeForce RTX 4080', 'gpu_id': '0x00002704', 'cores': 12, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 4070 Ti SUPER', 'screen': [2560, 1440], 'gpu': 'NVIDIA GeForce RTX 4070 Ti SUPER', 'gpu_id': '0x00002782', 'cores': 12, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 4070 Ti', 'screen': [2560, 1440], 'gpu': 'NVIDIA GeForce RTX 4070 Ti', 'gpu_id': '0x00002782', 'cores': 12, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 7900 XTX', 'screen': [2560, 1440], 'gpu': 'AMD Radeon RX 7900 XTX', 'gpu_id': '0x0000744C', 'cores': 16, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 7900 XT', 'screen': [2560, 1440], 'gpu': 'AMD Radeon RX 7900 XT', 'gpu_id': '0x0000744C', 'cores': 12, 'memory': 32, 'platform': 'Win32'},
]

# Desktop Gaming PCs - Mid Range
GAMING_MID = [
    {'name': 'Gaming PC - RTX 4070 SUPER', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 4070 SUPER', 'gpu_id': '0x00002783', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 4070', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 4070', 'gpu_id': '0x00002786', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 4060 Ti', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 4060 Ti', 'gpu_id': '0x00002803', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 4060', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 4060', 'gpu_id': '0x00002882', 'cores': 6, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 3080', 'screen': [2560, 1440], 'gpu': 'NVIDIA GeForce RTX 3080', 'gpu_id': '0x00002206', 'cores': 16, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 3070 Ti', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3070 Ti', 'gpu_id': '0x00002482', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 3070', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3070', 'gpu_id': '0x00002484', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 7800 XT', 'screen': [1920, 1080], 'gpu': 'AMD Radeon RX 7800 XT', 'gpu_id': '0x00007480', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 7700 XT', 'screen': [1920, 1080], 'gpu': 'AMD Radeon RX 7700 XT', 'gpu_id': '0x00007480', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 6800 XT', 'screen': [1920, 1080], 'gpu': 'AMD Radeon RX 6800 XT', 'gpu_id': '0x000073BF', 'cores': 12, 'memory': 16, 'platform': 'Win32'},
]

# Desktop Gaming PCs - Budget
GAMING_BUDGET = [
    {'name': 'Gaming PC - RTX 3060 Ti', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3060 Ti', 'gpu_id': '0x00002486', 'cores': 6, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RTX 3060', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3060', 'gpu_id': '0x00002503', 'cores': 6, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - GTX 1660 SUPER', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce GTX 1660 SUPER', 'gpu_id': '0x000021C4', 'cores': 8, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Gaming PC - GTX 1660 Ti', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce GTX 1660 Ti', 'gpu_id': '0x00002182', 'cores': 6, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - GTX 1650 SUPER', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce GTX 1650 SUPER', 'gpu_id': '0x00002187', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 6700 XT', 'screen': [1920, 1080], 'gpu': 'AMD Radeon RX 6700 XT', 'gpu_id': '0x000073DF', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 6650 XT', 'screen': [1920, 1080], 'gpu': 'AMD Radeon RX 6650 XT', 'gpu_id': '0x000073EF', 'cores': 6, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Gaming PC - RX 6600', 'screen': [1920, 1080], 'gpu': 'AMD Radeon RX 6600', 'gpu_id': '0x000073FF', 'cores': 6, 'memory': 8, 'platform': 'Win32'},
]

# Gaming Laptops - High End
LAPTOP_GAMING_HIGH = [
    {'name': 'Laptop - RTX 4090 Mobile', 'screen': [2560, 1600], 'gpu': 'NVIDIA GeForce RTX 4090 Laptop GPU', 'gpu_id': '0x00002717', 'cores': 14, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 4080 Mobile', 'screen': [2560, 1440], 'gpu': 'NVIDIA GeForce RTX 4080 Laptop GPU', 'gpu_id': '0x00002757', 'cores': 12, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 4070 Mobile', 'screen': [1920, 1200], 'gpu': 'NVIDIA GeForce RTX 4070 Laptop GPU', 'gpu_id': '0x00002820', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 4060 Mobile', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 4060 Laptop GPU', 'gpu_id': '0x000028A0', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 3080 Ti Mobile', 'screen': [2560, 1440], 'gpu': 'NVIDIA GeForce RTX 3080 Ti Laptop GPU', 'gpu_id': '0x00002420', 'cores': 8, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 3080 Mobile', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3080 Laptop GPU', 'gpu_id': '0x0000249C', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
]

# Gaming Laptops - Mid/Budget
LAPTOP_GAMING_MID = [
    {'name': 'Laptop - RTX 3070 Mobile', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3070 Laptop GPU', 'gpu_id': '0x000024DC', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 3060 Mobile', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3060 Laptop GPU', 'gpu_id': '0x00002560', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 3050 Ti Mobile', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3050 Ti Laptop GPU', 'gpu_id': '0x000025A0', 'cores': 6, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - RTX 3050 Mobile', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce RTX 3050 Laptop GPU', 'gpu_id': '0x000025A2', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - GTX 1650 Mobile', 'screen': [1920, 1080], 'gpu': 'NVIDIA GeForce GTX 1650 Mobile', 'gpu_id': '0x00001F99', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - RX 6700M', 'screen': [1920, 1080], 'gpu': 'AMD Radeon RX 6700M', 'gpu_id': '0x000073A3', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
]

# Business/Ultrabook Laptops - Intel
LAPTOP_INTEL = [
    {'name': 'Laptop - Intel Arc A770M', 'screen': [2560, 1600], 'gpu': 'Intel(R) Arc(TM) A770M Graphics', 'gpu_id': '0x000056A1', 'cores': 14, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - Intel Arc A730M', 'screen': [1920, 1200], 'gpu': 'Intel(R) Arc(TM) A730M Graphics', 'gpu_id': '0x000056A5', 'cores': 12, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - Intel Arc A370M', 'screen': [1920, 1080], 'gpu': 'Intel(R) Arc(TM) A370M Graphics', 'gpu_id': '0x00005693', 'cores': 8, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - Intel Iris Xe MAX', 'screen': [1920, 1200], 'gpu': 'Intel(R) Iris(R) Xe MAX Graphics', 'gpu_id': '0x00004905', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - Intel Iris Xe', 'screen': [1920, 1080], 'gpu': 'Intel(R) Iris(R) Xe Graphics', 'gpu_id': '0x00009A49', 'cores': 8, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - Intel Iris Plus', 'screen': [1920, 1080], 'gpu': 'Intel(R) Iris(R) Plus Graphics', 'gpu_id': '0x00008A52', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - Intel UHD 770', 'screen': [1920, 1080], 'gpu': 'Intel(R) UHD Graphics 770', 'gpu_id': '0x00004680', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Laptop - Intel UHD 730', 'screen': [1920, 1080], 'gpu': 'Intel(R) UHD Graphics 730', 'gpu_id': '0x00004692', 'cores': 6, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - Intel UHD 630', 'screen': [1920, 1080], 'gpu': 'Intel(R) UHD Graphics 630', 'gpu_id': '0x00003E92', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Laptop - Intel UHD 620', 'screen': [1366, 768], 'gpu': 'Intel(R) UHD Graphics 620', 'gpu_id': '0x00003EA0', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
]

# MacBooks - Apple Silicon
MACBOOK_APPLE = [
    {'name': 'MacBook Pro M3 Max', 'screen': [3456, 2234], 'gpu': 'Apple M3 Max', 'gpu_id': 'Apple', 'cores': 16, 'memory': 36, 'platform': 'MacIntel'},
    {'name': 'MacBook Pro M3 Pro', 'screen': [3024, 1964], 'gpu': 'Apple M3 Pro', 'gpu_id': 'Apple', 'cores': 12, 'memory': 18, 'platform': 'MacIntel'},
    {'name': 'MacBook Pro M3', 'screen': [2560, 1664], 'gpu': 'Apple M3', 'gpu_id': 'Apple', 'cores': 8, 'memory': 8, 'platform': 'MacIntel'},
    {'name': 'MacBook Pro M2 Max', 'screen': [3456, 2234], 'gpu': 'Apple M2 Max', 'gpu_id': 'Apple', 'cores': 12, 'memory': 32, 'platform': 'MacIntel'},
    {'name': 'MacBook Pro M2 Pro', 'screen': [3024, 1964], 'gpu': 'Apple M2 Pro', 'gpu_id': 'Apple', 'cores': 10, 'memory': 16, 'platform': 'MacIntel'},
    {'name': 'MacBook Pro M2', 'screen': [2560, 1664], 'gpu': 'Apple M2', 'gpu_id': 'Apple', 'cores': 8, 'memory': 8, 'platform': 'MacIntel'},
    {'name': 'MacBook Air M3', 'screen': [2560, 1664], 'gpu': 'Apple M3', 'gpu_id': 'Apple', 'cores': 8, 'memory': 8, 'platform': 'MacIntel'},
    {'name': 'MacBook Air M2', 'screen': [2560, 1664], 'gpu': 'Apple M2', 'gpu_id': 'Apple', 'cores': 8, 'memory': 8, 'platform': 'MacIntel'},
    {'name': 'MacBook Air M1', 'screen': [2560, 1600], 'gpu': 'Apple M1', 'gpu_id': 'Apple', 'cores': 8, 'memory': 8, 'platform': 'MacIntel'},
    {'name': 'iMac M3', 'screen': [4480, 2520], 'gpu': 'Apple M3', 'gpu_id': 'Apple', 'cores': 8, 'memory': 8, 'platform': 'MacIntel'},
]

# Office/Workstation PCs
WORKSTATION = [
    {'name': 'Workstation - RTX A6000', 'screen': [3840, 2160], 'gpu': 'NVIDIA RTX A6000', 'gpu_id': '0x00002230', 'cores': 32, 'memory': 64, 'platform': 'Win32'},
    {'name': 'Workstation - RTX A5000', 'screen': [2560, 1440], 'gpu': 'NVIDIA RTX A5000', 'gpu_id': '0x00002231', 'cores': 16, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Workstation - RTX A4000', 'screen': [2560, 1440], 'gpu': 'NVIDIA RTX A4000', 'gpu_id': '0x000024B0', 'cores': 12, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Workstation - Quadro RTX 5000', 'screen': [2560, 1440], 'gpu': 'NVIDIA Quadro RTX 5000', 'gpu_id': '0x00001E81', 'cores': 16, 'memory': 32, 'platform': 'Win32'},
    {'name': 'Workstation - Quadro P2200', 'screen': [1920, 1080], 'gpu': 'NVIDIA Quadro P2200', 'gpu_id': '0x00001E89', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Workstation - AMD Pro W7900', 'screen': [3840, 2160], 'gpu': 'AMD Radeon Pro W7900', 'gpu_id': '0x00007448', 'cores': 32, 'memory': 64, 'platform': 'Win32'},
    {'name': 'Workstation - AMD Pro W6800', 'screen': [2560, 1440], 'gpu': 'AMD Radeon Pro W6800', 'gpu_id': '0x000073A5', 'cores': 16, 'memory': 32, 'platform': 'Win32'},
]

# Budget/Office PCs - Integrated Graphics
OFFICE_INTEGRATED = [
    {'name': 'Office PC - AMD Vega 8', 'screen': [1920, 1080], 'gpu': 'AMD Radeon(TM) Vega 8 Graphics', 'gpu_id': '0x000015D8', 'cores': 6, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Office PC - AMD Vega 7', 'screen': [1920, 1080], 'gpu': 'AMD Radeon(TM) Vega 7 Graphics', 'gpu_id': '0x000015DD', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Office PC - AMD 780M', 'screen': [1920, 1080], 'gpu': 'AMD Radeon(TM) 780M Graphics', 'gpu_id': '0x000015BF', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Office PC - AMD 680M', 'screen': [1920, 1080], 'gpu': 'AMD Radeon(TM) 680M Graphics', 'gpu_id': '0x00001681', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Office PC - Intel UHD 770', 'screen': [1920, 1080], 'gpu': 'Intel(R) UHD Graphics 770', 'gpu_id': '0x00004680', 'cores': 8, 'memory': 16, 'platform': 'Win32'},
    {'name': 'Office PC - Intel UHD 730', 'screen': [1920, 1080], 'gpu': 'Intel(R) UHD Graphics 730', 'gpu_id': '0x00004692', 'cores': 6, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Office PC - Intel UHD 630', 'screen': [1920, 1080], 'gpu': 'Intel(R) UHD Graphics 630', 'gpu_id': '0x00003E92', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
    {'name': 'Office PC - Intel HD 530', 'screen': [1920, 1080], 'gpu': 'Intel(R) HD Graphics 530', 'gpu_id': '0x00001912', 'cores': 4, 'memory': 8, 'platform': 'Win32'},
]

# Combine all profiles with weights (more common devices have higher weight)
ALL_PROFILES = (
    GAMING_MID * 3 +           # Most common gaming PCs
    GAMING_BUDGET * 3 +        # Budget gaming very common
    LAPTOP_GAMING_MID * 3 +    # Common gaming laptops
    LAPTOP_INTEL * 4 +         # Very common business laptops
    OFFICE_INTEGRATED * 3 +    # Common office PCs
    GAMING_HIGH_END * 1 +      # Less common high-end
    LAPTOP_GAMING_HIGH * 1 +   # Less common high-end laptops
    MACBOOK_APPLE * 2 +        # MacBooks fairly common
    WORKSTATION * 1            # Rare workstations
)


# =============================================================================
# REALISTIC FONT SETS - Different OS have different fonts
# =============================================================================

FONTS_WINDOWS = [
    "Arial", "Arial Black", "Arial Narrow", "Book Antiqua", "Bookman Old Style",
    "Calibri", "Cambria", "Cambria Math", "Candara", "Century", "Century Gothic",
    "Comic Sans MS", "Consolas", "Constantia", "Corbel", "Courier", "Courier New",
    "Ebrima", "Franklin Gothic Medium", "Gabriola", "Gadugi", "Georgia",
    "Impact", "Ink Free", "Javanese Text", "Leelawadee UI", "Lucida Console",
    "Lucida Sans Unicode", "Malgun Gothic", "Marlett", "Microsoft Himalaya",
    "Microsoft JhengHei", "Microsoft New Tai Lue", "Microsoft PhagsPa",
    "Microsoft Sans Serif", "Microsoft Tai Le", "Microsoft YaHei",
    "Microsoft Yi Baiti", "MingLiU-ExtB", "Mongolian Baiti", "MS Gothic",
    "MS PGothic", "MS UI Gothic", "MV Boli", "Myanmar Text", "Nirmala UI",
    "Palatino Linotype", "Segoe MDL2 Assets", "Segoe Print", "Segoe Script",
    "Segoe UI", "Segoe UI Emoji", "Segoe UI Historic", "Segoe UI Symbol",
    "SimSun", "Sitka Banner", "Sitka Display", "Sitka Heading", "Sitka Small",
    "Sitka Subheading", "Sitka Text", "Sylfaen", "Symbol", "Tahoma",
    "Times New Roman", "Trebuchet MS", "Verdana", "Webdings", "Wingdings",
    "Yu Gothic", "Yu Gothic UI"
]

FONTS_MAC = [
    "American Typewriter", "Andale Mono", "Arial", "Arial Black", "Arial Narrow",
    "Arial Rounded MT Bold", "Arial Unicode MS", "Avenir", "Avenir Next",
    "Avenir Next Condensed", "Baskerville", "Big Caslon", "Bodoni 72",
    "Bodoni 72 Oldstyle", "Bodoni 72 Smallcaps", "Bradley Hand", "Brush Script MT",
    "Chalkboard", "Chalkboard SE", "Chalkduster", "Charter", "Cochin", "Comic Sans MS",
    "Copperplate", "Courier", "Courier New", "DIN Alternate", "DIN Condensed",
    "Didot", "Futura", "Geneva", "Georgia", "Gill Sans", "Helvetica",
    "Helvetica Neue", "Herculanum", "Hoefler Text", "Impact", "Lucida Grande",
    "Luminari", "Marker Felt", "Menlo", "Microsoft Sans Serif", "Monaco",
    "Noteworthy", "Optima", "Palatino", "Papyrus", "Phosphate", "Rockwell",
    "Savoye LET", "SignPainter", "Skia", "Snell Roundhand", "Tahoma",
    "Times", "Times New Roman", "Trattatello", "Trebuchet MS", "Verdana", "Zapfino"
]

# US Timezones for student verification
US_TIMEZONES = [
    (-300, "America/New_York"),      # EST
    (-360, "America/Chicago"),        # CST
    (-420, "America/Denver"),         # MST
    (-480, "America/Los_Angeles"),    # PST
    (-540, "America/Anchorage"),      # AKST
    (-600, "Pacific/Honolulu"),       # HST
]

# Chrome versions (recent)
CHROME_VERSIONS = ['120', '121', '122', '123', '124', '125', '126', '127', '128', '129', '130', '131']


def get_random_profile():
    """Get a random hardware profile with weighted selection."""
    return random.choice(ALL_PROFILES)


def get_fonts_for_platform(platform: str) -> list:
    """Get appropriate font list based on platform."""
    if platform == 'MacIntel':
        return random.sample(FONTS_MAC, min(len(FONTS_MAC), random.randint(40, 55)))
    else:
        return random.sample(FONTS_WINDOWS, min(len(FONTS_WINDOWS), random.randint(50, 70)))


def get_gpu_renderer_string(profile: dict) -> str:
    """Build GPU renderer string based on vendor."""
    gpu = profile['gpu']
    gpu_id = profile.get('gpu_id', '0x00000000')
    
    if 'NVIDIA' in gpu or 'GeForce' in gpu or 'RTX' in gpu or 'GTX' in gpu or 'Quadro' in gpu:
        return f"NVIDIA, {gpu} ({gpu_id}) Direct3D11 vs_5_0 ps_5_0, D3D11"
    elif 'AMD' in gpu or 'Radeon' in gpu:
        return f"AMD, {gpu} ({gpu_id}) Direct3D11 vs_5_0 ps_5_0, D3D11"
    elif 'Intel' in gpu:
        return f"Intel Inc., {gpu} ({gpu_id}), OpenGL 4.6"
    elif 'Apple' in gpu:
        return f"Apple Inc., {gpu}, OpenGL 4.1"
    else:
        return f"{gpu} ({gpu_id}) Direct3D11 vs_5_0 ps_5_0, D3D11"


def generate_fingerprint_data(verification_id: str, url: str = None) -> dict:
    """
    Generate complete fingerprint data for SheerID verification.
    
    Args:
        verification_id: The SheerID verification ID
        url: Optional verification URL for referer
        
    Returns:
        dict with fingerprint_data, headers, and profile info
    """
    # Select random profile
    profile = get_random_profile()
    platform = profile.get('platform', 'Win32')
    is_mac = platform == 'MacIntel'
    
    sw, sh = profile['screen']
    
    # Realistic taskbar/dock heights vary by OS and settings
    taskbar_height = random.choice([30, 40, 48]) if not is_mac else random.choice([70, 80, 90])
    aw, ah = sw, sh - taskbar_height
    
    # Browser window size varies realistically
    browser_width_offset = random.randint(0, 100)
    browser_height_offset = random.randint(100, 200)
    iw, ih = sw - browser_width_offset, sh - browser_height_offset
    
    # Generate unique hashes based on hardware
    canvas_seed = f"{profile['gpu']}_{profile['screen']}_{random.randint(10000, 99999)}"
    canvas_hash = hashlib.md5(canvas_seed.encode()).hexdigest()
    
    audio_seed = f"audio_{profile['cores']}_{profile['memory']}_{random.randint(10000, 99999)}"
    audio_hash = hashlib.md5(audio_seed.encode()).hexdigest()
    
    # 18-digit device ID
    ipqsd = str(random.randint(100000000000000000, 999999999999999999))
    
    # Get appropriate fonts for platform
    fonts = get_fonts_for_platform(platform)
    
    # Get GPU renderer string
    gpu_renderer = get_gpu_renderer_string(profile)
    
    # Select timezone
    tz_offset, tz_name = random.choice(US_TIMEZONES)
    
    # Select Chrome version
    chrome_version = random.choice(CHROME_VERSIONS)
    
    # Generate user agent based on platform
    if is_mac:
        user_agent = f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36'
    else:
        user_agent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36'
    
    # Color depth - most modern displays
    color_depth = random.choice([24, 24, 24, 30, 32])
    
    # Device pixel ratio - varies by display
    if sw >= 2560:
        dpr = random.choice([1, 1.25, 1.5, 2])
    else:
        dpr = random.choice([1, 1, 1.25])
    
    # Network connection type
    connection = {
        "downlink": round(random.uniform(5, 100), 2),
        "effectiveType": "4g",
        "rtt": random.randint(10, 100)
    }
    
    # WebGL parameters vary by GPU
    gpu = profile['gpu']
    if 'RTX 40' in gpu or 'RTX 30' in gpu or 'RX 7' in gpu:
        max_texture = 32768
        max_viewport = [32767, 32767]
    elif 'RTX' in gpu or 'GTX 16' in gpu or 'RX 6' in gpu:
        max_texture = 16384
        max_viewport = [32767, 32767]
    elif 'Apple M3' in gpu or 'Apple M2' in gpu:
        max_texture = 16384
        max_viewport = [16384, 16384]
    else:
        max_texture = 16384
        max_viewport = [16384, 16384]
    
    # Supported codecs
    codecs = ["webm", "vp9", "vp8", "mp3", "flac", "ogg", "wav", "aac"]
    supported_codecs = random.sample(codecs, random.randint(5, 8))
    
    # Plugins
    plugins = [
        {"name": "PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer"},
        {"name": "Chrome PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer"},
    ]
    
    # Language sets
    language_sets = [
        ['en-US', 'en'], ['en-GB', 'en', 'en-US'], ['en-US', 'en', 'es'],
        ['en-US', 'en', 'fr'], ['en-CA', 'en', 'en-US'], ['en-AU', 'en', 'en-US']
    ]
    selected_langs = random.choice(language_sets)
    
    # Build fingerprint data
    fingerprint_data = {
        'fast': '1',
        'ipqsd': ipqsd,
        'dtb': user_agent,
        'dtc': selected_langs[0],
        'dtd': str(color_depth),
        'dte': str(dpr),
        'dtf': str(color_depth),
        'dtg': json.dumps([sw, sh]),
        'dth': json.dumps([aw, ah]),
        'dti': str(tz_offset),
        'dtj': '1',
        'dtk': '1',
        'dtl': '1',
        'dtn': 'unknown',
        'dto': platform,
        'dtp': 'unknown',
        'dtr': canvas_hash,
        'dts': gpu_renderer,
        'dtt': audio_hash,
        'dtu': 'false',
        'dtv': 'false',
        'dtw': 'false',
        'dtx': 'false',
        'dty': 'false',
        'dtz': json.dumps([0, False, False]),
        'dtaa[]': fonts,
        'dtee': 'true',
        'dtgg': 'false',
        'dthh': f"{iw}x{ih}",
        'dthhB': f"{iw}x{ih}",
        'dtxx': 'true',
        'dtyy': 'false',
        'dtrr': 'false',
        'dtss': 'false',
        'dtqq': 'false',
        'dttt': 'c',
        'dtuu': 'false',
        'dtdp': '96',
        'dtdt': json.dumps({"locale": selected_langs[0], "calendar": "gregory", "numberingSystem": "latn", "timeZone": tz_name}),
        'dtme': str(profile['cores']),
        'dtam': str(profile['memory']),
        'dtcd': json.dumps(supported_codecs),
        'dtct': json.dumps(connection),
        'dtfc': '0',
        'dtfr': str(random.randint(-999999999, 999999999)),
        'dtsss': '0',
        'dtsfs': str(random.randint(-99999999, 99999999)),
        'dtfl': 'true',
        'dtsc': 'z17',
        'dtmt': str(random.randint(1000000000, 9999999999)),
        'dtoo': hashlib.md5(f"obj_{random.randint(1, 99999)}".encode()).hexdigest(),
        'dtff': 'true',
        'dtll': hashlib.md5(f"ll_{random.randint(1, 99999)}".encode()).hexdigest(),
        'dtsp': 'microphone',
        'dtsv': 'webcam',
        'dtsps': 'speaker',
        'dtpc': json.dumps(["accelerometer", "clipboard-write", "gyroscope"]),
        'dtkk': 'devices',
        'dtxv': json.dumps(max_viewport),
        'dtyv': str(max_texture),
        'dtyvu': '16',
        'dtyvv': '1024',
        'dtyvm': '30',
        'dtyvp': json.dumps([1, 1024]),
        'dtyvw': json.dumps([1, 1]),
        'dtls[]': selected_langs,
        'dta[]': json.dumps({"key": "transactionID", "value": verification_id}),
        'dtq[]': [json.dumps(p) for p in plugins],
    }
    
    # Add cookies
    ga_id = f"GA1.1.{random.randint(1000000000, 9999999999)}.{int(time.time())}"
    fingerprint_data['dtbb'] = f"ipqsd={ipqsd}; _ga={ga_id}; sid-verificationId={verification_id}"
    
    # Build headers
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': f'{selected_langs[0]},{selected_langs[0].split("-")[0]};q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'fn.us.fd.sheerid.com',
        'Origin': 'https://services.sheerid.com',
        'Referer': url or 'https://services.sheerid.com/',
        'Sec-Ch-Ua': f'"Not;A=Brand";v="99", "Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': f'"{("macOS" if is_mac else "Windows")}"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': user_agent
    }
    
    return {
        'fingerprint_data': fingerprint_data,
        'headers': headers,
        'profile': profile,
        'user_agent': user_agent,
        'chrome_version': chrome_version,
        'platform': platform,
        'ipqsd': ipqsd,
        'timezone': tz_name,
        'timezone_offset': tz_offset,
        'screen': [sw, sh],
        'gpu': profile['gpu']
    }


# IPQS Token (static, embedded in SheerID JS)
IPQS_TOKEN = "BJOvvIiNpZnA9XHXIHVc0S4FO87k4eub6NLOfmShTU7nRqamLKTzQixwD7XETz7bvtNHmicHNx9hEtOJ9NPo3kUJBl7o1jpwcbcXeOMDJjvulAWSrRnO7WYq9gxL6xNT0xnfou5UlshUGWQ2g68qBuWajMWbxZ25JELntxaP0neiVUbephG5E79ES89qBo4uIGBDvykdJb75hpo0URvJ0Fm1j6fuEqHQBq64Mi390KC9XoQwiFxyboxQ5lSooY4p"
IPQS_HOST = "https://fn.us.fd.sheerid.com"

def get_fingerprint_url():
    """Get the IPQS fingerprint URL."""
    return f"{IPQS_HOST}/api/*/{IPQS_TOKEN}/learn/fetch"


if __name__ == "__main__":
    # Test the module
    print("=" * 60)
    print("Fingerprint Profiles Test")
    print("=" * 60)
    print(f"Total profiles: {len(ALL_PROFILES)}")
    
    # Test generate fingerprint
    fp = generate_fingerprint_data("test123")
    print(f"\nGenerated fingerprint:")
    print(f"  Profile: {fp['profile']['name']}")
    print(f"  Platform: {fp['platform']}")
    print(f"  GPU: {fp['gpu']}")
    print(f"  Screen: {fp['screen']}")
    print(f"  Chrome: {fp['chrome_version']}")
    print(f"  Timezone: {fp['timezone']}")
    print(f"  IPQSD: {fp['ipqsd']}")
    print(f"  Fonts: {len(fp['fingerprint_data']['dtaa[]'])} fonts")
