#!/usr/bin/env python3
"""
Generate the synthetic product catalog at data/catalog/products.jsonl.

The catalog is synthetic but internally coherent: real brand and line names,
specs that match what that line actually ships with, prices drawn from the
street-price range for that tier, and a spread of stock levels including zeros.
Nothing here is scraped and no SKU corresponds to a real listing.

Coherence is the point, not decoration. Stage 3 evaluates spec-constrained
retrieval ("16GB RAM under $1200") and exact model lookups against this file,
so a ThinkPad X1 Carbon carrying an RTX 4090, or three different products all
called "Dell XPS 13", would make the relevance labels meaningless. Each model
line is therefore restricted to the tiers it plausibly ships in, Apple lines
only ever get Apple silicon, and repeated lines are disambiguated by their
configuration the way a retailer would list them.

Deterministic: a fixed seed means the same catalog every run, so eval numbers
stay comparable. Re-running overwrites the file.

    python scripts/generate_catalog.py
    python scripts/generate_catalog.py --count 200 --seed 20260918
"""
import argparse
import json
import os
import random

# ---------------------------------------------------------------------------
# Laptops
# ---------------------------------------------------------------------------
# (brand, line, allowed tiers). A line only appears in tiers it really ships in:
# IdeaPad Slim is never a workstation, Legion Pro is never a budget machine.

LAPTOP_LINES = [
    ("Dell", "Inspiron 14", ["budget"]),
    ("Dell", "Inspiron 15", ["budget", "mainstream"]),
    ("Dell", "Latitude 7450", ["mainstream", "premium"]),
    ("Dell", "XPS 13", ["premium"]),
    ("Dell", "XPS 15", ["premium", "workstation"]),
    ("Dell", "G15 Gaming", ["mainstream", "gaming"]),
    ("Dell", "Alienware m16", ["gaming", "workstation"]),
    ("Lenovo", "IdeaPad Slim 3", ["budget"]),
    ("Lenovo", "IdeaPad Slim 5", ["budget", "mainstream"]),
    ("Lenovo", "Yoga 7i", ["mainstream", "premium"]),
    ("Lenovo", "ThinkPad T14", ["mainstream", "premium"]),
    ("Lenovo", "ThinkPad X1 Carbon", ["premium"]),
    ("Lenovo", "ThinkPad P16", ["workstation"]),
    ("Lenovo", "Legion Pro 5", ["gaming"]),
    ("Lenovo", "Legion Pro 7", ["gaming", "workstation"]),
    ("HP", "Pavilion 15", ["budget", "mainstream"]),
    ("HP", "Envy 14", ["mainstream", "premium"]),
    ("HP", "Spectre x360", ["premium"]),
    ("HP", "EliteBook 840", ["mainstream", "premium"]),
    ("HP", "Omen 16", ["gaming", "workstation"]),
    ("HP", "ZBook Power 16", ["workstation"]),
    ("ASUS", "Vivobook 15", ["budget"]),
    ("ASUS", "Vivobook 16", ["budget", "mainstream"]),
    ("ASUS", "ZenBook 14", ["mainstream", "premium"]),
    ("ASUS", "TUF Gaming A15", ["gaming"]),
    ("ASUS", "ROG Zephyrus G14", ["gaming", "workstation"]),
    ("ASUS", "ROG Strix SCAR 18", ["workstation"]),
    ("Acer", "Aspire 3", ["budget"]),
    ("Acer", "Aspire 5", ["budget", "mainstream"]),
    ("Acer", "Swift Go 14", ["mainstream", "premium"]),
    ("Acer", "Nitro V 15", ["gaming"]),
    ("Acer", "Predator Helios 16", ["gaming", "workstation"]),
    ("MSI", "Modern 14", ["budget", "mainstream"]),
    ("MSI", "Prestige 13", ["premium"]),
    ("MSI", "Katana 15", ["gaming"]),
    ("MSI", "Raider GE78", ["workstation"]),
]

# Apple is kept separate: its lines never take Intel/AMD/NVIDIA parts, and the
# chip determines the tier rather than the other way round.
APPLE_LAPTOPS = [
    ("MacBook Air 13", "Apple M3", "Apple 10-core GPU",
     ['13.6" Liquid Retina'], ["8GB unified", "16GB unified"],
     ["256GB SSD", "512GB SSD"], ["52.6Wh"], (1049, 1449)),
    ("MacBook Air 15", "Apple M3", "Apple 10-core GPU",
     ['15.3" Liquid Retina'], ["16GB unified", "24GB unified"],
     ["512GB SSD", "1TB SSD"], ["66.5Wh"], (1249, 1699)),
    ("MacBook Pro 14", "Apple M3 Pro", "Apple 18-core GPU",
     ['14.2" Liquid Retina XDR 120Hz'], ["18GB unified", "36GB unified"],
     ["512GB SSD", "1TB SSD"], ["72.4Wh"], (1899, 2599)),
    ("MacBook Pro 16", "Apple M3 Max", "Apple 40-core GPU",
     ['16.2" Liquid Retina XDR 120Hz'], ["36GB unified", "48GB unified", "64GB unified"],
     ["1TB SSD", "2TB SSD"], ["100Wh"], (2699, 3899)),
]

LAPTOP_TIERS = {
    "budget": {
        "cpu": ["Intel Core i3-1315U", "AMD Ryzen 3 7320U", "Intel Core i5-1235U"],
        "ram": ["8GB LPDDR5", "16GB DDR4"],
        "storage": ["256GB NVMe SSD", "512GB NVMe SSD"],
        "display": ['14" FHD (1920x1080) 60Hz', '15.6" FHD (1920x1080) 60Hz'],
        "gpu": ["Integrated Intel UHD", "Integrated AMD Radeon"],
        "battery": ["41Wh", "54Wh"],
        "base_price": (299, 399),
        "audience": "everyday study and office work",
    },
    "mainstream": {
        "cpu": ["Intel Core Ultra 5 125H", "AMD Ryzen 5 8645HS", "Intel Core i7-1355U"],
        "ram": ["16GB LPDDR5X", "16GB DDR5"],
        "storage": ["512GB NVMe SSD", "1TB NVMe SSD"],
        "display": ['14" WUXGA IPS 60Hz', '15.6" FHD+ IPS 120Hz', '16" WUXGA IPS 60Hz'],
        "gpu": ["Integrated Intel Arc", "Integrated AMD Radeon 780M"],
        "battery": ["63Wh", "70Wh"],
        "base_price": (549, 699),
        "audience": "hybrid work and light creative projects",
    },
    "premium": {
        "cpu": ["Intel Core Ultra 7 155H", "AMD Ryzen 7 8845HS"],
        "ram": ["16GB LPDDR5X", "32GB LPDDR5X"],
        "storage": ["512GB NVMe SSD", "1TB NVMe SSD"],
        "display": ['14" 2.8K OLED 120Hz', '13.4" FHD+ InfinityEdge', '14" 3K OLED 120Hz'],
        "gpu": ["Integrated Intel Arc", "NVIDIA GeForce RTX 3050 6GB"],
        "battery": ["70Wh", "75Wh"],
        "base_price": (899, 1150),
        "audience": "professionals who travel and need battery life",
    },
    "gaming": {
        "cpu": ["Intel Core i7-14650HX", "AMD Ryzen 7 8845HS", "Intel Core i5-13500HX"],
        "ram": ["16GB DDR5", "32GB DDR5"],
        "storage": ["512GB NVMe SSD", "1TB NVMe SSD"],
        "display": ['15.6" FHD 144Hz', '16" QHD+ 165Hz', '15.6" QHD 240Hz'],
        "gpu": ["NVIDIA GeForce RTX 4050 6GB", "NVIDIA GeForce RTX 4060 8GB",
                "NVIDIA GeForce RTX 4070 8GB", "NVIDIA GeForce RTX 4080 12GB"],
        "battery": ["70Wh", "80Wh"],
        "base_price": (799, 1099),
        "audience": "gaming at high refresh rates",
    },
    "workstation": {
        "cpu": ["Intel Core i9-14900HX", "AMD Ryzen 9 8945HS"],
        "ram": ["32GB DDR5", "64GB DDR5"],
        "storage": ["1TB NVMe SSD", "2TB NVMe SSD"],
        "display": ['16" QHD+ Mini LED 240Hz', '18" QHD+ 165Hz', '16" 4K OLED 120Hz'],
        "gpu": ["NVIDIA GeForce RTX 4080 12GB", "NVIDIA GeForce RTX 4090 16GB",
                "NVIDIA RTX 3500 Ada 12GB"],
        "battery": ["90Wh", "99.9Wh"],
        "base_price": (1150, 1500),
        "audience": "video editing, 3D rendering and sustained compute loads",
    },
}

# Laptop price is built from a tier base plus spec premiums rather than drawn
# at random inside a wide band. Spec-constrained retrieval queries ("16GB RAM
# under $1200") only carry signal if price actually tracks the specs; with a
# random price, the correct answer set would be arbitrary.
GPU_PREMIUM = [
    ("RTX 4090", 1350), ("RTX 4080", 900), ("RTX 3500 Ada", 820),
    ("RTX 4070", 620), ("RTX 4060", 400), ("RTX 4050", 240),
    ("RTX 3050", 150), ("Integrated", 0),
]
RAM_PREMIUM = [("64GB", 780), ("48GB", 560), ("36GB", 400), ("32GB", 330),
               ("24GB", 200), ("18GB", 150), ("16GB", 90), ("8GB", 0), ("4GB", 0)]
STORAGE_PREMIUM = [("2TB", 420), ("1TB", 180), ("512GB", 80),
                   ("256GB", 0), ("128GB", 0), ("64GB", 0)]


def _premium(value: str, table) -> int:
    for token, amount in table:
        if token in (value or ""):
            return amount
    return 0


def spec_priced(rng: random.Random, base_range, specs: dict) -> float:
    """Tier base price plus what the chosen components are worth."""
    total = rng.uniform(*base_range)
    total += _premium(specs.get("gpu", ""), GPU_PREMIUM)
    total += _premium(specs.get("ram", ""), RAM_PREMIUM)
    total += _premium(specs.get("storage", ""), STORAGE_PREMIUM)
    total *= rng.uniform(0.96, 1.04)  # street-price variation between retailers
    rounded = round(total / 10) * 10
    return float(rounded - 0.01) if rng.random() < 0.7 else float(rounded)

# ---------------------------------------------------------------------------
# Smartphones
# ---------------------------------------------------------------------------

PHONE_LINES = [
    ("Samsung", "Galaxy A16", ["budget"]),
    ("Samsung", "Galaxy A55", ["budget", "mainstream"]),
    ("Samsung", "Galaxy S24", ["flagship"]),
    ("Samsung", "Galaxy S24+", ["flagship"]),
    ("Samsung", "Galaxy S24 Ultra", ["flagship"]),
    ("Google", "Pixel 8a", ["mainstream"]),
    ("Google", "Pixel 8", ["mainstream", "flagship"]),
    ("Google", "Pixel 8 Pro", ["flagship"]),
    ("OnePlus", "Nord CE4", ["budget", "mainstream"]),
    ("OnePlus", "OnePlus 12R", ["mainstream"]),
    ("OnePlus", "OnePlus 12", ["flagship"]),
    ("Xiaomi", "Redmi Note 13", ["budget"]),
    ("Xiaomi", "Redmi Note 13 Pro", ["budget", "mainstream"]),
    ("Xiaomi", "Poco X6 Pro", ["mainstream"]),
    ("Xiaomi", "Xiaomi 14", ["flagship"]),
    ("Nothing", "Phone (2a)", ["mainstream"]),
    ("Nothing", "Phone (2)", ["mainstream", "flagship"]),
    ("Motorola", "Moto G54", ["budget"]),
    ("Motorola", "Edge 50 Pro", ["mainstream"]),
]

APPLE_PHONES = [
    ("iPhone SE", "Apple A15 Bionic", ['4.7" Retina HD'], ["4GB"],
     ["64GB", "128GB"], ["2018mAh"], "12MP wide", (429, 529)),
    ("iPhone 15", "Apple A16 Bionic", ['6.1" Super Retina XDR'], ["6GB"],
     ["128GB", "256GB"], ["3349mAh"], "48MP main + 12MP ultrawide", (799, 999)),
    ("iPhone 15 Plus", "Apple A16 Bionic", ['6.7" Super Retina XDR'], ["6GB"],
     ["128GB", "256GB"], ["4383mAh"], "48MP main + 12MP ultrawide", (899, 1099)),
    ("iPhone 15 Pro", "Apple A17 Pro", ['6.1" Super Retina XDR 120Hz'], ["8GB"],
     ["128GB", "256GB", "512GB"], ["3274mAh"],
     "48MP main + 12MP ultrawide + 12MP telephoto", (999, 1399)),
    ("iPhone 15 Pro Max", "Apple A17 Pro", ['6.7" Super Retina XDR 120Hz'], ["8GB"],
     ["256GB", "512GB", "1TB"], ["4441mAh"],
     "48MP main + 12MP ultrawide + 12MP 5x telephoto", (1199, 1799)),
]

PHONE_TIERS = {
    "budget": {
        "cpu": ["MediaTek Dimensity 7025", "Snapdragon 4 Gen 2", "Exynos 1330"],
        "ram": ["4GB", "6GB", "8GB"],
        "storage": ["64GB", "128GB"],
        "display": ['6.6" LCD 90Hz', '6.67" AMOLED 90Hz'],
        "battery": ["5000mAh"],
        "camera": ["50MP main + 2MP depth", "64MP main + 8MP ultrawide"],
        "price": (149, 379),
    },
    "mainstream": {
        "cpu": ["Snapdragon 7+ Gen 3", "Google Tensor G3", "Dimensity 8300"],
        "ram": ["8GB", "12GB"],
        "storage": ["128GB", "256GB"],
        "display": ['6.1" OLED 120Hz', '6.67" AMOLED 120Hz'],
        "battery": ["4500mAh", "5000mAh"],
        "camera": ["50MP main + 12MP ultrawide", "64MP main + 8MP ultrawide + 2MP macro"],
        "price": (399, 749),
    },
    "flagship": {
        "cpu": ["Snapdragon 8 Gen 3", "Google Tensor G3"],
        "ram": ["12GB", "16GB"],
        "storage": ["256GB", "512GB", "1TB"],
        "display": ['6.7" LTPO AMOLED 120Hz', '6.8" QHD+ AMOLED 120Hz'],
        "battery": ["4400mAh", "5000mAh"],
        "camera": ["50MP main + 12MP ultrawide + 10MP telephoto",
                   "200MP main + 12MP ultrawide + 10MP periscope"],
        "price": (799, 1499),
    },
}

# ---------------------------------------------------------------------------
# Tablets
# ---------------------------------------------------------------------------

TABLET_LINES = [
    ("Samsung", "Galaxy Tab A9+", ["budget"]),
    ("Samsung", "Galaxy Tab S9 FE", ["budget", "premium"]),
    ("Samsung", "Galaxy Tab S9", ["premium"]),
    ("Samsung", "Galaxy Tab S9 Ultra", ["premium"]),
    ("Lenovo", "Tab M11", ["budget"]),
    ("Lenovo", "Tab P12", ["budget", "premium"]),
    ("Microsoft", "Surface Go 4", ["budget"]),
    ("Microsoft", "Surface Pro 9", ["premium"]),
]

APPLE_TABLETS = [
    ("iPad 10th gen", "Apple A14 Bionic", ['10.9" Liquid Retina'], ["4GB"],
     ["64GB", "256GB"], ["28.6Wh"], (349, 499)),
    ("iPad mini", "Apple A15 Bionic", ['8.3" Liquid Retina'], ["4GB"],
     ["64GB", "256GB"], ["19.3Wh"], (499, 649)),
    ("iPad Air 11", "Apple M2", ['11" Liquid Retina'], ["8GB"],
     ["128GB", "256GB", "512GB"], ["28.9Wh"], (599, 899)),
    ("iPad Pro 11", "Apple M4", ['11" Ultra Retina XDR 120Hz'], ["8GB", "16GB"],
     ["256GB", "512GB", "1TB"], ["31.3Wh"], (999, 1599)),
    ("iPad Pro 13", "Apple M4", ['13" Ultra Retina XDR 120Hz'], ["8GB", "16GB"],
     ["256GB", "512GB", "1TB"], ["38.9Wh"], (1299, 1899)),
]

TABLET_TIERS = {
    "budget": {
        "cpu": ["MediaTek Helio G99", "Snapdragon 695", "Intel Processor N200"],
        "ram": ["4GB", "8GB"],
        "storage": ["64GB", "128GB"],
        "display": ['10.9" LCD 60Hz', '11" LCD 90Hz'],
        "battery": ["7040mAh", "8000mAh"],
        "price": (179, 429),
    },
    "premium": {
        "cpu": ["Snapdragon 8 Gen 2", "Intel Core i5-1235U", "Snapdragon 8 Gen 1"],
        "ram": ["8GB", "12GB", "16GB"],
        "storage": ["128GB", "256GB", "512GB"],
        "display": ['12.4" Dynamic AMOLED 2X 120Hz', '14.6" Dynamic AMOLED 2X 120Hz',
                    '13" PixelSense Flow 120Hz'],
        "battery": ["8400mAh", "11200mAh"],
        "price": (549, 1399),
    },
}

# ---------------------------------------------------------------------------
# Accessories and software: fixed products, so price is the only variable.
# ---------------------------------------------------------------------------

ACCESSORIES = [
    ("Anker", "PowerCore 20K Power Bank", "portable charger", 49, 89,
     "20000mAh capacity with 65W USB-C Power Delivery."),
    ("Anker", "Nano II 65W Charger", "charger", 29, 55,
     "Compact GaN charger for laptops and phones."),
    ("Belkin", "BoostCharge Pro 3-in-1", "wireless charger", 89, 149,
     "MagSafe-compatible stand charging phone, watch and buds together."),
    ("Sony", "WH-1000XM5 Headphones", "headphones", 279, 399,
     "Over-ear active noise cancelling with 30-hour battery."),
    ("Bose", "QuietComfort Ultra Headphones", "headphones", 299, 429,
     "Over-ear noise cancelling with spatial audio."),
    ("Apple", "AirPods Pro 2", "earbuds", 189, 249,
     "In-ear ANC with USB-C charging case."),
    ("Samsung", "Galaxy Buds3 Pro", "earbuds", 149, 219,
     "In-ear ANC tuned for Galaxy devices."),
    ("Logitech", "MX Master 3S Mouse", "mouse", 79, 119,
     "Wireless productivity mouse with quiet clicks and 8K DPI."),
    ("Logitech", "MX Keys S Keyboard", "keyboard", 89, 129,
     "Low-profile backlit wireless keyboard for multi-device work."),
    ("Keychron", "K2 Mechanical Keyboard", "keyboard", 79, 109,
     "75% hot-swappable mechanical keyboard with Bluetooth."),
    ("Dell", "UltraSharp U2723QE Monitor", "monitor", 429, 649,
     '27-inch 4K IPS Black monitor with USB-C hub and 90W power delivery.'),
    ("LG", "UltraGear 27GP850 Monitor", "monitor", 319, 499,
     '27-inch QHD Nano IPS gaming monitor at 165Hz with 1ms response.'),
    ("Samsung", "T7 Shield Portable SSD", "external storage", 89, 179,
     "Rugged USB 3.2 Gen 2 external SSD rated IP65."),
    ("SanDisk", "Extreme Pro microSD", "memory card", 24, 89,
     "UHS-I microSD card for cameras, drones and handhelds."),
    ("UGREEN", "Revodok USB-C Hub", "docking station", 39, 99,
     "USB-C hub with HDMI 4K60, Ethernet and 100W pass-through."),
    ("Spigen", "Rugged Armor Case", "phone case", 14, 29,
     "Shock-absorbing TPU case with raised camera lip."),
    ("Peak Design", "Everyday Backpack 20L", "laptop bag", 179, 279,
     "Weatherproof backpack with a padded 16-inch laptop sleeve."),
    ("Targus", "CityGear Laptop Sleeve", "laptop bag", 29, 59,
     "Padded sleeve sized for 14 to 15.6-inch laptops."),
    ("Jabra", "Evolve2 65 Headset", "headset", 149, 229,
     "Wireless on-ear headset with boom mic, certified for video calls."),
    ("Elgato", "Facecam MK.2 Webcam", "webcam", 129, 179,
     "1080p60 webcam with a fixed-focus prime lens for streaming."),
    ("Sennheiser", "Momentum 4 Headphones", "headphones", 249, 379,
     "Over-ear noise cancelling with 60-hour battery life."),
    ("JBL", "Tune 770NC Headphones", "headphones", 89, 149,
     "Budget over-ear noise cancelling with multipoint pairing."),
    ("Anker", "Soundcore Liberty 4", "earbuds", 79, 129,
     "In-ear buds with adaptive ANC and wireless charging."),
    ("Google", "Pixel Buds Pro", "earbuds", 129, 199,
     "In-ear ANC buds tuned for Android and Pixel devices."),
    ("Razer", "DeathAdder V3 Mouse", "mouse", 59, 99,
     "Lightweight ergonomic gaming mouse with a 30K optical sensor."),
    ("Microsoft", "Surface Arc Mouse", "mouse", 49, 79,
     "Flat-folding Bluetooth mouse for travel."),
    ("Logitech", "K380 Multi-Device Keyboard", "keyboard", 29, 49,
     "Compact Bluetooth keyboard pairing with three devices."),
    ("Das Keyboard", "4Q Mechanical Keyboard", "keyboard", 129, 199,
     "Full-size mechanical keyboard with cherry switches and a media wheel."),
    ("Samsung", "ViewFinity S8 Monitor", "monitor", 349, 549,
     "27-inch 4K IPS monitor with USB-C and a height-adjustable stand."),
    ("BenQ", "PD2705U DesignVue Monitor", "monitor", 449, 699,
     "27-inch 4K monitor factory-calibrated for sRGB and Display P3."),
    ("ASUS", "ProArt PA278CV Monitor", "monitor", 279, 429,
     "27-inch QHD monitor for colour-critical design work."),
    ("Crucial", "X9 Pro Portable SSD", "external storage", 79, 199,
     "Compact USB-C external SSD with 1050MB/s sequential reads."),
    ("WD", "My Passport SSD", "external storage", 99, 219,
     "Shock-resistant portable SSD with hardware encryption."),
    ("Kingston", "Canvas React Plus microSD", "memory card", 29, 99,
     "V90 microSD card for 8K video capture."),
    ("Anker", "575 USB-C Docking Station", "docking station", 129, 249,
     "12-in-1 dock driving dual 4K displays with 85W charging."),
    ("CalDigit", "TS4 Thunderbolt Dock", "docking station", 299, 429,
     "Thunderbolt 4 dock with 18 ports and 98W host charging."),
    ("OtterBox", "Defender Series Case", "phone case", 39, 69,
     "Multi-layer rugged case with a port-blocking cover."),
    ("Apple", "Silicone Case with MagSafe", "phone case", 39, 59,
     "Soft-touch silicone case with magnetic alignment."),
    ("Nomad", "Modern Leather Folio", "phone case", 59, 99,
     "Horween leather folio with card slots."),
    ("Incase", "Compass Backpack", "laptop bag", 89, 139,
     "Everyday backpack with a fleece-lined 16-inch laptop compartment."),
    ("tomtoc", "Defender-A14 Laptop Sleeve", "laptop bag", 25, 49,
     "Corner-armoured sleeve sized for 14-inch laptops."),
    ("Anker", "Prime 27650 Power Bank", "portable charger", 129, 199,
     "27650mAh bank delivering 250W across three ports."),
    ("Baseus", "Blade 100W Power Bank", "portable charger", 69, 119,
     "Slim 20000mAh laptop power bank with 100W USB-C output."),
    ("Satechi", "165W GaN Charger", "charger", 89, 139,
     "Four-port desktop GaN charger for laptop and phone together."),
]

SOFTWARE = [
    ("Microsoft", "Microsoft 365 Personal (1yr)", 69, 99,
     "Annual subscription: Word, Excel, PowerPoint, Outlook and 1TB OneDrive."),
    ("Microsoft", "Microsoft 365 Family (1yr)", 99, 139,
     "Annual subscription covering up to six people, 6TB total OneDrive."),
    ("Microsoft", "Windows 11 Pro License", 139, 199,
     "Retail licence key for a single device, including BitLocker."),
    ("Adobe", "Creative Cloud All Apps (1yr)", 599, 779,
     "Annual plan covering Photoshop, Illustrator, Premiere Pro and more."),
    ("Adobe", "Photoshop Single App (1yr)", 239, 299,
     "Annual single-app plan with 100GB cloud storage."),
    ("Bitdefender", "Total Security (5 devices, 1yr)", 39, 89,
     "Cross-platform antivirus and ransomware protection for five devices."),
    ("Norton", "360 Deluxe (5 devices, 1yr)", 34, 99,
     "Antivirus with VPN, password manager and 50GB cloud backup."),
    ("JetBrains", "All Products Pack (1yr)", 289, 359,
     "Annual individual licence for the full JetBrains IDE suite."),
    ("Parallels", "Desktop 19 for Mac (1yr)", 99, 129,
     "Run Windows on Apple silicon Macs without rebooting."),
    ("Affinity", "Affinity V2 Universal Licence", 99, 169,
     "Perpetual licence for Designer, Photo and Publisher on all platforms."),
    ("Microsoft", "Microsoft 365 Business Standard (1yr)", 149, 199,
     "Annual per-user plan with Teams, Exchange and desktop Office apps."),
    ("Adobe", "Acrobat Pro (1yr)", 155, 239,
     "Annual plan for editing, signing and converting PDF documents."),
    ("Adobe", "Lightroom Photography Plan (1yr)", 119, 179,
     "Annual plan with Lightroom, Lightroom Classic and 1TB storage."),
    ("Kaspersky", "Premium (5 devices, 1yr)", 45, 99,
     "Antivirus suite with unlimited VPN and identity monitoring."),
    ("Malwarebytes", "Premium Security (3 devices, 1yr)", 39, 79,
     "Real-time malware and ransomware protection for three devices."),
    ("CorelDRAW", "Graphics Suite (1yr)", 269, 369,
     "Annual subscription for vector illustration and page layout."),
    ("Autodesk", "Fusion 360 (1yr)", 495, 679,
     "Annual licence for cloud-based CAD, CAM and CAE."),
    ("VMware", "Workstation Pro Licence", 149, 199,
     "Perpetual licence to run virtual machines on Windows and Linux."),
    ("Nero", "Platinum Suite", 59, 99,
     "Perpetual multimedia suite for disc authoring and video conversion."),
]

# Stock is deliberately uneven so "is it in stock" is a real question.
STOCK_WEIGHTS = [(0, 0, 0.12), (1, 4, 0.18), (5, 25, 0.40), (26, 120, 0.30)]


def pick_stock(rng: random.Random) -> int:
    roll, cumulative = rng.random(), 0.0
    for low, high, weight in STOCK_WEIGHTS:
        cumulative += weight
        if roll <= cumulative:
            return rng.randint(low, high)
    return rng.randint(5, 25)


def price_in(rng: random.Random, low: float, high: float) -> float:
    """A price in range, landing on a realistic .99 / .00 ending."""
    rounded = round(rng.uniform(low, high) / 10) * 10
    return float(rounded - 0.01) if rng.random() < 0.7 else float(rounded)


def make_laptop(rng):
    brand, line, tiers = rng.choice(LAPTOP_LINES)
    tier_name = rng.choice(tiers)
    tier = LAPTOP_TIERS[tier_name]
    specs = {
        "cpu": rng.choice(tier["cpu"]),
        "ram": rng.choice(tier["ram"]),
        "storage": rng.choice(tier["storage"]),
        "display": rng.choice(tier["display"]),
        "gpu": rng.choice(tier["gpu"]),
        "battery": rng.choice(tier["battery"]),
    }
    description = (
        f"The {brand} {line} is a {tier_name} laptop built for {tier['audience']}. "
        f"It pairs a {specs['cpu']} with {specs['ram']} of memory and a "
        f"{specs['storage']}, behind a {specs['display']} panel. Graphics are "
        f"handled by {specs['gpu']}, with a {specs['battery']} battery."
    )
    price = spec_priced(rng, tier["base_price"], specs)
    return brand, f"{brand} {line}", "laptops", price, specs, description


def make_apple_laptop(rng):
    line, cpu, gpu, displays, rams, storages, batteries, price = rng.choice(APPLE_LAPTOPS)
    specs = {
        "cpu": cpu, "ram": rng.choice(rams), "storage": rng.choice(storages),
        "display": rng.choice(displays), "gpu": gpu, "battery": rng.choice(batteries),
    }
    description = (
        f"The Apple {line} is a premium laptop running on {cpu} with a {gpu}. "
        f"It has {specs['ram']} memory and a {specs['storage']}, behind a "
        f"{specs['display']} display, with a {specs['battery']} battery. "
        f"Suited to professionals who need long battery life and quiet operation."
    )
    return "Apple", f"Apple {line}", "laptops", price_in(rng, *price), specs, description


def make_phone(rng):
    brand, line, tiers = rng.choice(PHONE_LINES)
    tier_name = rng.choice(tiers)
    tier = PHONE_TIERS[tier_name]
    specs = {
        "cpu": rng.choice(tier["cpu"]),
        "ram": rng.choice(tier["ram"]),
        "storage": rng.choice(tier["storage"]),
        "display": rng.choice(tier["display"]),
        "battery": rng.choice(tier["battery"]),
        "camera": rng.choice(tier["camera"]),
    }
    description = (
        f"The {brand} {line} is a {tier_name} smartphone with a {specs['display']} "
        f"screen and a {specs['cpu']} chipset. It carries {specs['ram']} of RAM, "
        f"{specs['storage']} of storage and a {specs['battery']} battery. "
        f"The camera system is {specs['camera']}."
    )
    return brand, f"{brand} {line}", "smartphones", price_in(rng, *tier["price"]), specs, description


def make_apple_phone(rng):
    line, cpu, displays, rams, storages, batteries, camera, price = rng.choice(APPLE_PHONES)
    specs = {
        "cpu": cpu, "ram": rng.choice(rams), "storage": rng.choice(storages),
        "display": rng.choice(displays), "battery": rng.choice(batteries),
        "camera": camera,
    }
    description = (
        f"The Apple {line} is a smartphone with a {specs['display']} screen powered "
        f"by the {cpu}. It has {specs['storage']} of storage and a "
        f"{specs['battery']} battery. The camera system is {camera}."
    )
    return "Apple", f"Apple {line}", "smartphones", price_in(rng, *price), specs, description


def make_tablet(rng):
    brand, line, tiers = rng.choice(TABLET_LINES)
    tier_name = rng.choice(tiers)
    tier = TABLET_TIERS[tier_name]
    specs = {
        "cpu": rng.choice(tier["cpu"]),
        "ram": rng.choice(tier["ram"]),
        "storage": rng.choice(tier["storage"]),
        "display": rng.choice(tier["display"]),
        "battery": rng.choice(tier["battery"]),
    }
    description = (
        f"The {brand} {line} is a {tier_name} tablet with a {specs['display']} display "
        f"and a {specs['cpu']} processor. It has {specs['ram']} of RAM and "
        f"{specs['storage']} of storage, with a {specs['battery']} battery. "
        f"Suited to note-taking, media and light creative work."
    )
    return brand, f"{brand} {line}", "tablets", price_in(rng, *tier["price"]), specs, description


def make_apple_tablet(rng):
    line, cpu, displays, rams, storages, batteries, price = rng.choice(APPLE_TABLETS)
    specs = {
        "cpu": cpu, "ram": rng.choice(rams), "storage": rng.choice(storages),
        "display": rng.choice(displays), "battery": rng.choice(batteries),
    }
    description = (
        f"The Apple {line} is a tablet with a {specs['display']} display powered by "
        f"the {cpu}. It has {specs['ram']} of memory and {specs['storage']} of "
        f"storage, with a {specs['battery']} battery. Works with Apple Pencil."
    )
    return "Apple", f"Apple {line}", "tablets", price_in(rng, *price), specs, description


def make_accessory(rng, pool=None):
    brand, name, kind, low, high, blurb = (pool.pop() if pool else rng.choice(ACCESSORIES))
    description = (
        f"The {brand} {name} is a {kind} accessory. {blurb} "
        f"Compatible with current laptops, tablets and smartphones."
    )
    return brand, f"{brand} {name}", "accessories", price_in(rng, low, high), {"type": kind}, description


def make_software(rng, pool=None):
    brand, name, low, high, blurb = (pool.pop() if pool else rng.choice(SOFTWARE))
    specs = {
        "licence": "subscription" if "(1yr)" in name else "perpetual",
        "platform": rng.choice(["Windows, macOS", "Windows", "macOS",
                                "Windows, macOS, iOS, Android"]),
    }
    description = (
        f"{brand} {name} is a software licence. {blurb} "
        f"Delivered as a digital key for {specs['platform']}."
    )
    return brand, name, "software", price_in(rng, low, high), specs, description


# Category mix, sized so every category has enough SKUs for per-category
# retrieval queries to mean something. Apple gets its own slice of each
# device category because its lines need separate spec handling.
MIX = [
    (make_laptop, 0.28), (make_apple_laptop, 0.06),
    (make_phone, 0.20), (make_apple_phone, 0.06),
    (make_tablet, 0.09), (make_apple_tablet, 0.05),
    (make_accessory, 0.18),
    (make_software, 0.08),
]


def disambiguate(name: str, specs: dict, seen: dict) -> str:
    """Retailers list repeated model lines by configuration; so do we.

    Without this, several SKUs share a display name and an exact-model-lookup
    eval cannot say which one a query should have returned.
    """
    seen[name] = seen.get(name, 0) + 1
    if seen[name] == 1:
        return name

    # Widen the configuration shown until the name is unique: two SKUs of the
    # same line may share RAM and storage but differ in GPU or CPU, and an
    # exact-model query needs exactly one correct answer.
    for keys in (("ram", "storage"), ("ram", "storage", "gpu"),
                 ("ram", "storage", "cpu"), ("ram", "storage", "gpu", "cpu"),
                 ("ram", "storage", "display")):
        parts = [specs.get(key) for key in keys if specs.get(key)]
        if not parts:
            continue
        candidate = f"{name} ({' / '.join(parts)})"
        if candidate not in seen:
            seen[candidate] = 1
            return candidate

    # Genuinely identical configuration: a counter is the only option left.
    base = f"{name} ({' / '.join(str(v) for v in specs.values())})" if specs else name
    n = 2
    while f"{base} #{n}" in seen:
        n += 1
    final = f"{base} #{n}"
    seen[final] = 1
    return final


def sku_for(rng: random.Random, category: str, brand: str, seen: set) -> str:
    prefix = {"laptops": "LAP", "smartphones": "PHN", "tablets": "TAB",
              "accessories": "ACC", "software": "SFW"}[category]
    brand_code = "".join(c for c in brand.upper() if c.isalpha())[:3].ljust(3, "X")
    while True:
        candidate = f"{prefix}-{brand_code}-{rng.randint(1000, 9999)}"
        if candidate not in seen:
            seen.add(candidate)
            return candidate


def generate(count: int, seed: int) -> list:
    rng = random.Random(seed)
    seen_skus, seen_names = set(), {}

    builders = []
    for builder, share in MIX:
        builders.extend([builder] * max(1, round(share * count)))
    rng.shuffle(builders)
    builders = builders[:count]

    # Fixed-product categories are drawn without replacement so no accessory or
    # licence appears as two different SKUs, which would leave an exact-product
    # query with two equally correct answers.
    accessory_pool = ACCESSORIES[:]
    software_pool = SOFTWARE[:]
    rng.shuffle(accessory_pool)
    rng.shuffle(software_pool)

    products = []
    for builder in builders:
        if builder is make_accessory:
            brand, name, category, price, specs, description = builder(rng, accessory_pool)
        elif builder is make_software:
            brand, name, category, price, specs, description = builder(rng, software_pool)
        else:
            brand, name, category, price, specs, description = builder(rng)
        name = disambiguate(name, specs, seen_names)
        products.append({
            "sku": sku_for(rng, category, brand, seen_skus),
            "name": name,
            "brand": brand,
            "category": category,
            "price_usd": price,
            "stock": pick_stock(rng),
            "specs": specs,
            "description": description,
        })
    return products


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260918)
    parser.add_argument("--out", default=os.path.join("data", "catalog", "products.jsonl"))
    args = parser.parse_args()

    products = generate(args.count, args.seed)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        for product in products:
            handle.write(json.dumps(product, ensure_ascii=False) + "\n")

    by_category = {}
    for product in products:
        by_category[product["category"]] = by_category.get(product["category"], 0) + 1
    prices = [p["price_usd"] for p in products]

    print(f"Wrote {len(products)} SKUs to {args.out} (seed {args.seed})")
    for category, n in sorted(by_category.items()):
        print(f"  {category:<14} {n:>4}")
    print(f"  out of stock   {sum(1 for p in products if p['stock'] == 0):>4}")
    print(f"  low stock (<5) {sum(1 for p in products if 0 < p['stock'] < 5):>4}")
    print(f"  unique names   {len({p['name'] for p in products}):>4}")
    print(f"  price range    ${min(prices):,.2f} - ${max(prices):,.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
