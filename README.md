# ⚡ Real-ESRGAN Desktop GUI & Engine

แอปพลิเคชัน Desktop GUI (รองรับ Windows และ Linux) สำหรับขยายความคมชัดของรูปภาพด้วย AI โมเดล **Real-ESRGAN NCNN** พร้อมระบบประมวลผลคู่ **Hybrid GPU + Multi-Core CPU**

---

## 📑 สารบัญ (Table of Contents)

1. [🌟 ฟีเจอร์หลัก (Key Features)](#-ฟีเจอร์หลัก-key-features)
   - [🖥️ Desktop GUI Application (PySide6 / Qt6)](#️-desktop-gui-application-pyside6--qt6)
   - [💻 Headless CLI Engine (upscale.py)](#-headless-cli-engine-upscalepy)
2. [🎮 รายการฮาร์ดแวร์ & GPU ที่รองรับ (Supported Hardware & GPUs)](#-รายการฮาร์ดแวร์--gpu-ที่รองรับ-supported-hardware--gpus)
   - [AMD Radeon GPUs](#1--amd-radeon-gpus-รองรับสมบูรณ์แบบ---first-class-support)
   - [NVIDIA GeForce / RTX GPUs](#2--nvidia-geforce--rtx-gpus)
   - [Intel GPUs](#3--intel-gpus)
   - [CPU Mode](#4-⚡-cpu-multi-threading-mode-ไม่จำเป็นต้องมี-gpu)
3. [💻 คู่มือการติดตั้งและใช้งาน CLI Version (upscale.py)](#-คู่มือการติดตั้งและใช้งาน-cli-version-upscalepy)
   - [1. ขั้นตอนเตรียมไดรเวอร์ระบบและ Environment ด้วย uv](#1-ขั้นตอนเตรียมไดรเวอร์ระบบและ-environment-ด้วย-uv)
   - [2. โครงสร้างคำสั่งพื้นฐาน (Basic Syntax)](#2-โครงสร้างคำสั่งพื้นฐาน-basic-syntax)
   - [3. ตารางพารามิเตอร์ทั้งหมด (Command Options)](#3-ตารางพารามิเตอร์ทั้งหมด-command-options)
   - [4. คุณสมบัติของแต่ละโมเดล (Model Comparison)](#4-คุณสมบัติของแต่ละโมเดล-model-comparison)
   - [5. แหล่งจัดเก็บโมเดลและการค้นหา Path (AI Model Storage & Search Paths)](#5-แหล่งจัดเก็บโมเดลและการค้นหา-path-ai-model-storage--search-paths)
   - [6. ตัวอย่างคำสั่งที่ใช้บ่อย (Cheat Sheet: Common Use Cases)](#6-ตัวอย่างคำสั่งที่ใช้บ่อย-cheat-sheet-common-use-cases)
   - [7. การตรวจสอบประสิทธิภาพการทำงาน (Performance Monitoring)](#7-การตรวจสอบประสิทธิภาพการทำงาน-performance-monitoring)
4. [🖥️ การใช้งาน Desktop GUI Application](#️-การใช้งาน-desktop-gui-application)
   - [การเปิดใช้งานแอปพลิเคชัน](#การเปิดใช้งานแอปพลิเคชัน)
   - [ระบบสลับธีม (Theme Switcher)](#ระบบสลับธีม-theme-switcher)
5. [🧪 การทดสอบระบบ (Automated Tests & Quality Gates)](#-การทดสอบระบบ-automated-tests--quality-gates)
6. [📦 การสร้างไฟล์ติดตั้ง (Cross-Platform Standalone Build)](#-การสร้างไฟล์ติดตั้ง-cross-platform-standalone-build)
   - [บน Linux](#บน-linux)
   - [บน Windows](#บน-windows)
   - [สร้างอัตโนมัติผ่าน GitHub Actions CI](#สร้างอัตโนมัติผ่าน-github-actions-ci)
7. [📁 โครงสร้างโปรเจกต์ (Project Architecture)](#-โครงสร้างโปรเจกต์-project-architecture)
8. [📄 License](#-license)

---

## 🌟 ฟีเจอร์หลัก (Key Features)

### 🖥️ Desktop GUI Application (PySide6 / Qt6)
- **🎯 1-Click Photography Presets**: ปรับแต่งค่าอัตโนมัติตามประเภทภาพในคลิกเดียว (Portrait & Studio, Old Film Scan, Landscape, Anime, Low-Light)
- **Drag & Drop & Recursive Batch Queue**: ลากวางไฟล์รูปภาพ หรือกดปุ่ม `📂 Add Folder` เพื่อสแกนค้นหารูปภาพในทุกโฟลเดอร์ย่อยอย่างลึกซึ้ง (`rglob("*")`) พร้อมระบบตรวจจับและป้องกันไฟล์ชื่อซ้ำเขียนทับกันอัตโนมัติ (Collision Protection: `photo_x4.png`, `photo_1_x4.png`)
- **🎯 5-Column Queue & Bulk Destination**: ตารางคิวงานแสดง 5 คอลัมน์ (`#`, `Name`, `Resolution`, `Destination`, `Status`) รองรับการเลือกหลายไฟล์แล้วคลิกขวาเปลี่ยนโฟลเดอร์ปลายทางพร้อมกัน, กดปุ่ม `📁 Destination` บน Toolbar, หรือดับเบิ้ลคลิกช่อง Destination ได้อย่างอิสระ
- **💾 Save & Multi-Queue Session Load (.json)**: บันทึกและโหลดคิวงานเก็บไว้ทำต่อ พร้อมรองรับการเลือกโหลดหลายไฟล์ `.json` พร้อมกันในครั้งเดียว (Multi-File Selection) พร้อมตัวเลือก Append เข้ากับคิวเดิม หรือ Replace คิวใหม่
- **🛡️ Destination Fallback Across PCs**: เมื่อนำไฟล์ Session ไปเปิดบนเครื่องอื่นหรือไดรฟ์ที่ไม่มีอยู่จริง ระบบจะสลับมาใช้ Output Directory ปัจจุบันของโปรแกรมอัตโนมัติ ปลอดภัย ไม่เกิดข้อผิดพลาด
- **🔄 Auto-Save & Crash Recovery**: จดจำรายการคิวและสถานะล่าสุด (`Done`, `Queued`, `Failed`) อัตโนมัติเมื่อปิดหรือเปิดโปรแกรมใหม่
- **⏩ Smart Resume & Context Menu**: เมื่อกด Start Batch ระบบจะประมวลผลต่อเฉพาะไฟล์ที่ยังไม่เสร็จ และข้ามไฟล์ที่เสร็จแล้วอัตโนมัติ พร้อมเมนูคลิกขวา: `🔄 Retry Failed Items`, `🧹 Clear Completed`, `↺ Reset All to Queued`
- **🔍 Interactive Zoom & Pan Before/After Wiper**: ตัวเลื่อนเปรียบเทียบภาพแบบ Split-View Slider พร้อมระบบซูมด้วยล้อเมาส์ (1.0x – 8.0x), คลิกขวา/เมาส์กลางลากเพื่อ Pan, และดับเบิ้ลคลิกเพื่อรีเซ็ต
- **⚡ Smart Instant Preview**: กดปุ่ม Generate Preview เพื่อดูผลลัพธ์โมเดลแบบทันทีและบันทึกลงโฟลเดอร์ผลลัพธ์จริง พร้อมสตรีม Progress การดาวน์โหลดโมเดลเข้าหน้าต่าง Log
- **🌓 Dynamic Theme Switcher**: สลับโหมด Dark Mode (Cyberpunk Dark) และ Light Mode (Clean Slate Light) ได้ทันทีแบบ Real-Time พร้อมจดจำสถานะ
- **🤖 โมเดล AI ครบวงจร (Default: `x4plus` 4x)**:
  - `x4plus` (ค่าเริ่มต้น): โมเดลคุณภาพสูงสุด เก็บรายละเอียดพื้นผิว Texture ภาพถ่าย ทิวทัศน์ บุคคล
  - `x4plus-anime`: ลายเส้นคมกริบ สำหรับงานดิจิทัลอาร์ตและการ์ตูน 4K
  - `animevideov3`: ความเร็วสูงสุด เหมาะกับภาพอนิเมะ การ์ตูน สกรีนช็อต (Native 2x)
- **👤 Face Enhancement (GFPGAN / CodeFormer ONNX)**: กู้คืนรายละเอียดดวงตา ผิว ฟัน และโครงหน้ามนุษย์ด้วย AI (Default: GFPGAN v1.4 ตรึงพิกัดตาแม่นยำ ไร้ปัญหาตาซ้อน) ทำงานผ่าน ONNX Runtime น้ำหนักเบา
- **👄 Preserve Real Smile (มาสก์ฟัน & รอยยิ้มเดิม)**: ระบบ Selective Feature Masking ช่วยเบลนด์ฟันและริมฝีปากจริงของภาพเดิมกลับลงไปอย่างแนบเนียน กำจัดอาการฟันเกิน ฟันหลอกตา (AI Hallucination) และรอยยิ้มปลอม 100% ขณะที่ผิวหน้าและดวงตายังคงคมชัดระดับสตูดิโอ (เปิดอัตโนมัติใน Preset `portrait`)
- **🎞️ Natural Monochromatic Film Grain (0–10%)**: เติมเกรนฟิล์ม 35mm อิงความสว่าง Midtones กำจัดอาการผิวหุ่นขี้ผึ้ง (Waxy Skin) คืนชีวิตชีวาและ Micro-contrast ให้ผิวสมจริง
- **📷 EXIF Metadata & ICC Profile Preservation**: ถ่ายโอนข้อมูลกล้อง เลนส์ วันที่ ค่าเปิดรับแสง และ Color Profile (sRGB, Display P3, Adobe RGB) จากภาพต้นฉบับไปยังไฟล์ผลลัพธ์ 100%
- **🧹 Denoise & Natural Grain Preservation**: แถบเลื่อนปรับระดับลด Noise (0–100) ค่าเริ่มต้น 0% เพื่อรักษา Texture ตามธรรมชาติของผิวมนุษย์
- **⚙️ ควบคุมฮาร์ดแวร์อิสระ**:
  - เลือกเปิด/ปิด GPU Worker (Vulkan Device 0: เช่น NVIDIA GTX 1050)
  - ปรับจำนวน CPU Workers ได้ตามจำนวน Core ของเครื่อง (เช่น AMD Ryzen 4500 = 3 Workers)
  - ปรับขนาด Tile Size (0 = Auto/เร็วสุด, 200-400 = ประหยัด VRAM 2GB)
- **📊 Real-Time Telemetry**: แสดงแถบความคืบหน้า, ความเร็วประมวลผล (Images/sec), เวลาที่เหลือโดยประมาณ (ETA), และ Console แสดง Log แบบแบ่งสี
- **⏹️ Cooperative Cancellation**: ปุ่มยกเลิก (Cancel) หยุดการทำงานของ Worker Processes ได้อย่างปลอดภัยโดยไม่มี Process ค้าง

### 💻 Headless CLI Engine (`upscale.py`)
- เข้ากันได้ 100% (Backward-Compatible) กับคำสั่งสคริปต์เดิม
- รองรับการเรียกใช้ผ่าน Terminal, Cron Job หรือ Automated Pipeline ได้ตามปกติ
- บังคับรันบนสภาพแวดล้อม Python 3.11 เสถียรสูง

---

## 🎮 รายการฮาร์ดแวร์ & GPU ที่รองรับ (Supported Hardware & GPUs)

โปรเจกต์นี้ใช้ **Vulkan API** ร่วมกับเอนจิน **Tencent NCNN** เป็นแกนหลัก จึงรองรับการ์ดจอจาก **ทุกค่าย (Cross-Vendor)** ได้อย่างสมบูรณ์ ไม่ได้จำกัดเฉพาะค่ายใดค่ายหนึ่ง (ไม่ต้องพึ่งพา CUDA):

### 1. 🔴 AMD Radeon GPUs (รองรับสมบูรณ์แบบ - First-Class Support)
* **การ์ดจอแยก (Dedicated Desktop & Laptop GPUs)**:
  * AMD Radeon RX 400 / 500 ซีรีส์ (สถาปัตยกรรม Polaris เช่น RX 480, RX 570, RX 580)
  * AMD Radeon RX Vega ซีรีส์ (Vega 56, Vega 64, Radeon VII)
  * AMD Radeon RX 5000 ซีรีส์ (RDNA 1 เช่น RX 5500 XT, RX 5600 XT, RX 5700 XT)
  * AMD Radeon RX 6000 ซีรีส์ (RDNA 2 เช่น RX 6600, RX 6700 XT, RX 6800 XT, RX 6900 XT)
  * AMD Radeon RX 7000 ซีรีส์ (RDNA 3 เช่น RX 7600, RX 7700 XT, RX 7800 XT, RX 7900 XTX)
* **การ์ดจอออนบอร์ด (Integrated Graphics / APU)**:
  * AMD Radeon Graphics ในโปรเซสเซอร์ AMD Ryzen APU (เช่น Ryzen 4000, 5000, 6000, 7000, และ 8000 series)

### 2. 🟢 NVIDIA GeForce / RTX GPUs
* **GeForce GTX ซีรีส์**: GTX 900, GTX 1000 (เช่น GTX 1050 2GB, GTX 1060, GTX 1080), GTX 1600 (เช่น GTX 1650, GTX 1660 Super)
* **GeForce RTX ซีรีส์**: RTX 2000, RTX 3000, RTX 4000 ทุกรุ่น

### 3. 🔵 Intel GPUs
* **Intel Arc Discrete GPUs**: Arc A310, A380, A580, A750, A770
* **Intel Integrated Graphics**: Intel Iris Xe, Intel UHD Graphics 620/630/770 ขึ้นไป

### 4. ⚡ CPU Multi-Threading Mode (ไม่จำเป็นต้องมี GPU)
* ซีพียู **AMD Ryzen / Intel Core / Xeon** ทุกรุ่นผ่าน OpenMP Multi-threading ทำงานร่วมกับ GPU หรือทำงานเดี่ยวได้ 100% เหมาะสำหรับเครื่องที่ไม่มีการ์ดจอแยก หรือรันบนคลาวด์/เซิร์ฟเวอร์

---

## 💻 คู่มือการติดตั้งและใช้งาน CLI Version (upscale.py)

### 1. ขั้นตอนเตรียมไดรเวอร์ระบบและ Environment ด้วย uv

#### Step 1.1: ติดตั้งไดรเวอร์ Vulkan ของระบบ

##### 🐧 บน Arch Linux / Manjaro:
```bash
# 1. ติดตั้งไดรเวอร์ Vulkan ตามค่ายการ์ดจอของคุณ:
# [กรณีใช้การ์ดจอ AMD Radeon (Mesa RADV แนะนำที่สุด เสถียรและเร็ว)]:
sudo pacman -S vulkan-radeon vulkan-icd-loader openmp

# [กรณีใช้การ์ดจอ NVIDIA]:
sudo pacman -S nvidia-utils vulkan-icd-loader openmp

# [กรณีใช้การ์ดจอ Intel (Arc / Iris / UHD)]:
sudo pacman -S vulkan-intel vulkan-icd-loader openmp

# 2. ตรวจสอบว่าระบบมองเห็นการ์ดจอผ่าน Vulkan:
vulkaninfo --summary
```

> [!NOTE]
> หากพบปัญหาเกี่ยวกับไลบรารี `libomp.so.5` บน Arch Linux ให้ทำ symlink เชื่อมโยงในระบบ:
> ```bash
> sudo ln -s /usr/lib/libomp.so /usr/lib/libomp.so.5
> sudo ldconfig
> ```

##### 🐧 บน Ubuntu / Debian / Pop!_OS:
```bash
# กรณีใช้การ์ดจอ AMD Radeon หรือ Intel:
sudo apt update && sudo apt install -y libvulkan1 mesa-vulkan-drivers vulkan-tools libomp-dev

# กรณีใช้การ์ดจอ NVIDIA:
sudo apt update && sudo apt install -y libvulkan1 nvidia-driver-<version> libomp-dev
```

##### 🪟 บน Windows (10 / 11):
* **AMD Radeon**: ติดตั้งไดรเวอร์ [AMD Software: Adrenalin Edition](https://www.amd.com/en/support)
* **NVIDIA**: ติดตั้งไดรเวอร์ [GeForce Game Ready / Studio Driver](https://www.nvidia.com/Download/index.aspx)
* **Intel**: ติดตั้งไดรเวอร์ [Intel Arc & Iris Xe Graphics Driver](https://www.intel.com/content/www/us/en/download-center/home.html)
*(ไดรเวอร์ทางการของ Windows ทุกค่ายจะติดตั้ง Vulkan Runtime มาให้อยู่แล้ว โปรแกรมจะตรวจพบและใช้งานได้ทันที)*

#### Step 1.2: ติดตั้ง Python 3.11 ผ่าน uv
```bash
uv python install 3.11
```

#### Step 1.3: สร้างและเข้าสู่ Virtual Environment
```bash
# สร้าง venv ที่เจาะจง Python 3.11
uv venv --python 3.11

# เข้าใช้งาน Virtual Environment (Activate)
source .venv/bin/activate
```

#### Step 1.4: ติดตั้งแพ็กเกจที่จำเป็น
```bash
# ติดตั้งแบบแพ็กเกจโปรเจกต์ทั้งหมด:
uv pip install -e ".[dev]"

# หรือติดตั้งเฉพาะแพ็กเกจพื้นฐานสำหรับ CLI:
uv pip install realesrgan-ncnn-py opencv-python pillow tqdm
```

---

### 2. โครงสร้างคำสั่งพื้นฐาน (Basic Syntax)

เมื่ออยู่ในสถานะ Activate (มี `(.venv)` นำหน้า prompt):
```bash
python upscale.py -i <INPUT_DIR> -o <OUTPUT_DIR> [OPTIONS]
```

หรือสั่งรันทางลัดผ่าน `uv` โดยไม่ต้อง activate:
```bash
uv run python upscale.py -i <INPUT_DIR> -o <OUTPUT_DIR> [OPTIONS]
```

---

### 3. ตารางพารามิเตอร์ทั้งหมด (Command Options)

| Flag | Long Option | Type | Default | Description |
| :---: | :--- | :---: | :---: | :--- |
| `-i` | `--input_dir` | `str` | *(Required)* | โฟลเดอร์รูปภาพต้นทางที่ต้องการแปลง |
| `-o` | `--output_dir` | `str` | *(Required)* | โฟลเดอร์ปลายทางสำหรับบันทึกผลลัพธ์ |
| `-p` | `--preset` | `str` | `None` | 1-Click Preset: `portrait`, `vintage_film`, `landscape`, `anime`, `low_light` |
| `-s` | `--scale` | `int` | `4` | อัตราขยายภาพ: `2` หรือ `4` (Default: `4`) |
| `-m` | `--model` | `str` | `x4plus` | โมเดล AI: `x4plus`, `x4plus-anime`, `animevideov3` |
| `-t` | `--tile_size` | `int` | `0` | ขนาดบล็อกประมวลผล (`0` = ทั้งภาพเร็วสุด, `200-400` = ประหยัด VRAM) |
| `-q` | `--quality` | `int` | `92` | คุณภาพไฟล์ผลลัพธ์ JPG ระดับ `1-100` (Default: `92`) |
| `-c` | `--cpu_workers` | `int` | `3` | จำนวน Worker ฝั่ง CPU (แนะนำ: `3` สำหรับ 6-core) |
| `-d` | `--denoise` | `int` | `0` | ระดับลด Noise `0-100` (Default: `0` เพื่อคงเกรนและผิวธรรมชาติ) |
| `-g` | `--grain` | `int` | `0` | ระดับเกรนฟิล์ม 35mm `0-10` (Default: `0` ปิด, แนะนำ `2-3` สำหรับคน) |
| `-f` | `--face_enhance` | - | `False` | เปิดใช้งาน AI Face Enhancement (GFPGAN / CodeFormer) |
| | `--face_model` | `str` | `gfpgan` | เลือกรุ่นโมเดลหน้า: `gfpgan`, `codeformer` (Default: `gfpgan`) |
| | `--face_fidelity` | `float` | `0.8` | ค่าน้ำหนักความสมดุลใบหน้าเดิม `0.0 - 1.0` (Default: `0.8`) |
| `-mm` | `--mask_mouth` | - | `False` | มาสก์ฟันและรอยยิ้มเดิม (Preserve Real Smile) ป้องกันฟันเกิน/รอยยิ้มเพี้ยน |
| `-h` | `--help` | - | - | แสดงข้อความช่วยเหลือและพารามิเตอร์ทั้งหมด |

> [!TIP]
> 📖 **คู่มือทฤษฎีการถ่ายภาพและการปรับค่าเชิงลึก**: ดูคำแนะนำการปรับค่าสำหรับภาพบุคคล ภาพฟิล์มเก่า ภาพวิว และภาพการ์ตูน พร้อมคำอธิบายในแง่ทฤษฎีการถ่ายภาพ (Film Grain, Acutance, Plastic Skin) ได้ที่ [**Manual.md**](Manual.md)

---

### 4. คุณสมบัติของแต่ละโมเดล (Model Comparison)

1. **`x4plus` (Native 4x) — ค่าเริ่มต้น (Default)**
   - **ความเร็ว**: ปานกลาง
   - **คุณภาพ**: สูงสุด เก็บรายละเอียดพื้นผิว (Texture) และดีเทลขนาดเล็กได้สมบูรณ์แบบ
   - **การใช้งานที่แนะนำ**: เหมาะสำหรับภาพถ่ายทั่วไป วิวทิวทัศน์ ภาพบุคคล และภาพถ่ายจริง

2. **`x4plus-anime` (Native 4x)**
   - **ความเร็ว**: ปานกลาง
   - **คุณภาพ**: สูงมาก ลายเส้นคมกริบ ไร้รอยแตกหรือ noise
   - **การใช้งานที่แนะนำ**: เหมาะสำหรับภาพวาดดิจิทัล ภาพการ์ตูน ภาพ 2D อาร์ตเวิร์กที่ต้องการขยายเป็น 4K

3. **`animevideov3` (Native 2x)**
   - **ความเร็ว**: เร็วที่สุด (ประหยัดทรัพยากร GPU/CPU มากที่สุด)
   - **คุณภาพ**: คมชัด เหมาะสำหรับอนิเมะ การ์ตูน สกรีนช็อต
   - **การใช้งานที่แนะนำ**: เหมาะกับงานที่ต้องการประมวลผลปริมาณมากด้วยความเร็วสูง

### 5. แหล่งจัดเก็บโมเดลและการค้นหา Path (AI Model Storage & Search Paths)

โมเดลที่ใช้งานในระบบแบ่งออกเป็น 2 ประเภท:
1. **Real-ESRGAN Core Models (`x4plus`, `x4plus-anime`, `animevideov3`)**: ติดตั้งมาพร้อมกับแพ็กเกจ `realesrgan-ncnn-py` โดยตรง สามารถเรียกใช้งานได้ทันทีโดยไม่ต้องดาวน์โหลดเพิ่ม
2. **Face Enhancement Models (`CodeFormer`, `GFPGAN`, `YuNet Face Detector`)**: เป็นโมเดล ONNX สำหรับกู้คืนใบหน้า (~228KB ถึง ~376MB) โปรแกรมจะดาวน์โหลดอัตโนมัติเมื่อเปิดใช้งานครั้งแรก

#### 📍 ลำดับการตรวจสอบและค้นหาไฟล์โมเดล (Search Hierarchy)
เมื่อเปิดใช้งาน Face Enhancement ระบบจะค้นหาไฟล์โมเดลเรียงตามลำดับความสำคัญดังนี้:

| ลำดับ | ตำแหน่งที่ระบบเข้าไปตรวจสอบ | คำอธิบายและวัตถุประสงค์ |
| :---: | :--- | :--- |
| **1** | **Explicit Custom Directory** | โฟลเดอร์ที่ส่งผ่านโค้ดหรือพารามิเตอร์ `custom_dir` |
| **2** | **Environment Variable** (`$REAL_ESRGAN_WEIGHTS_DIR`) | สำหรับผู้ใช้ที่ต้องการย้ายโมเดลไปไว้ที่ไดรฟ์อื่น เช่น External SSD หรือไดรฟ์ D: |
| **3** | **Standalone / Portable Mode** (`<exe_dir>/weights`) | ตรวจสอบโฟลเดอร์ `weights/` ข้างไฟล์ `.exe` สำหรับรันแบบพกพาใส่ Flash Drive |
| **4** | **Project / Working Directory** (`./weights` หรือ `./models`) | ตรวจสอบโฟลเดอร์ภายในไดเรกทอรีปัจจุบันของโปรเจกต์ |
| **5** | **Platform-Standard Data Directory** (Persistent Storage) | 🐧 **Linux**: `~/.local/share/real_esrgan_gui/weights/` (มาตรฐาน XDG ปลอดภัยจากการถูกล้างแคช)<br>🪟 **Windows**: `%LOCALAPPDATA%\real_esrgan_gui\weights\`<br>🍎 **macOS**: `~/Library/Application Support/real_esrgan_gui/weights/` |
| **6** | **Legacy Cache Fallback** (`~/.cache/real_esrgan_gui/weights/`) | ตรวจสอบโฟลเดอร์แคชเดิม เพื่อให้ผู้ใช้เดิมใช้งานต่อได้ทันทีโดยไม่ต้องดาวน์โหลดซ้ำ |

#### 🔗 ลิงก์ดาวน์โหลดไฟล์โมเดลเสริมโดยตรง (Supplementary Face Models Direct Download Links)

สำหรับผู้ใช้ที่ต้องการดาวน์โหลดไฟล์โมเดลล่วงหน้า (เช่น นำไปใช้กับเครื่องออฟไลน์ ไม่ต่ออินเทอร์เน็ต หรือกรณีดาวน์โหลดอัตโนมัติผ่านแอปไม่สำเร็จ) สามารถคลิกลิงก์ดาวน์โหลดตรงได้จากตารางด้านล่างนี้:

| ชื่อโมเดล | ชื่อไฟล์ (.onnx) | ขนาดไฟล์ | ลิงก์ดาวน์โหลดโดยตรง (Direct Download) | หน้าที่และคำแนะนำการใช้งาน |
| :--- | :--- | :---: | :---: | :--- |
| **YuNet Face Detector** | `face_detection_yunet_2023mar.onnx` | ~228 KB | [🔗 ดาวน์โหลด YuNet](https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx) | **จำเป็นต้องมี**: โมเดลตรวจจับตำแหน่งใบหน้าและจุด Landmark 5 จุด น้ำหนักเบา ความเร็วสูงพิเศษ |
| **GFPGAN v1.4** | `GFPGANv1.4.onnx` | ~340 MB | [🔗 ดาวน์โหลด GFPGAN v1.4](https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/GFPGANv1.4.onnx) | **แนะนำสำหรับภาพมุมเอียง / ใส่แว่น / ตาธรรมชาติ**: ใช้ Continuous Latent GAN ตรึงพิกัดตาแม่นยำ **ไร้ปัญหาตาซ้อน 100%** |
| **CodeFormer** | `codeformer.onnx` | ~376 MB | [🔗 ดาวน์โหลด CodeFormer](https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/codeformer.onnx) | **แนะนำสำหรับภาพหน้าตรงบุคคลยิ้มเห็นฟัน**: ใช้ Discrete Codebook กู้คืนรูปฟันแท้และเค้าโครงหน้าคมกริบ ไร้ปัญหาฟันหลอน |

> [!TIP]
> 👁️ **ทำไมบางภาพใช้ CodeFormer แล้วเกิด "ตาซ้อนกัน" (Double Eyes) แต่ GFPGAN ตาปกติไม่มั่ว?**:
> - **สาเหตุทางเทคนิค**: CodeFormer ใช้ Transformer ทำนายรหัสจาก Discrete Codebook ซึ่งถูกเทรนด้วยภาพหน้าตรงมองกล้องเป็นหลัก หากเจอดวงตาที่มองเหลือบ, ใบหน้าเอียงหันข้าง, คนใส่แว่นตา, มีแสงสะท้อนที่เลนส์ หรือมีผมตกลงมาบังตา Transformer อาจสับสนพิกัดแล้วหยิบดวงตามองตรงจาก Codebook มาแปะซ้อน ทำให้เกิด **ลูกตาหรือเปลือกตาเพิ่มขึ้นมาซ้อนกัน (Phantom / Double Eyes)**
> - **GFPGAN ทำไมถึงไม่มั่ว?**: GFPGAN ใช้ระบบ Spatial Feature Transform (SFT) ที่แมปพิกัดดวงตาแบบจุดต่อจุด (Continuous Latent Mapping) จึง**ตรึงตำแหน่งดวงตาได้ถูกต้อง 100% ไม่สร้างตาซ้อน**
> - **วิธีแก้ปัญหา**:
>   1. **สลับไปใช้โมเดล `GFPGAN`**: เลือกโมเดลหน้าเป็น GFPGAN ทันที จะได้ดวงตาที่เป็นธรรมชาติ ถูกต้อง ไม่มั่ว 100%
>   2. **หากต้องการใช้ CodeFormer ต่อ**: ให้ปรับค่า **Fidelity Weight ขึ้นเป็น `0.85 – 0.95`** เพื่อบังคับให้ AI ยึดพิกัดดวงตาเดิมจากภาพมากขึ้น
>   3. **หากกังวลเรื่องฟันซ้อนใน GFPGAN**: ให้ติ๊กเปิด **`Preserve Real Smile`** (`--mask_mouth` / `-mm`) ระบบจะมาสก์ดึงฟันแท้จริงจากภาพเดิมมาใช้โดยอัตโนมัติ

#### 📥 คำสั่งดาวน์โหลดผ่าน Terminal / Command Line (ทางลัด)

##### 🐧 บน Linux / macOS (ดาวน์โหลดใส่โฟลเดอร์ weights):
```bash
mkdir -p weights
curl -L -o weights/face_detection_yunet_2023mar.onnx "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
curl -L -o weights/GFPGANv1.4.onnx "https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/GFPGANv1.4.onnx"
curl -L -o weights/codeformer.onnx "https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/codeformer.onnx"
```

##### 🪟 บน Windows (PowerShell):
```powershell
New-Item -ItemType Directory -Force -Path weights
Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -OutFile "weights\face_detection_yunet_2023mar.onnx"
Invoke-WebRequest -Uri "https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/GFPGANv1.4.onnx" -OutFile "weights\GFPGANv1.4.onnx"
Invoke-WebRequest -Uri "https://github.com/harisreedhar/Face-Upscalers-ONNX/releases/download/Models/codeformer.onnx" -OutFile "weights\codeformer.onnx"
```

> [!TIP]
> 🎒 **วิธีพกพาไปใช้งานแบบ 100% Offline (Portable Mode)**:
> หากต้องการนำโปรแกรมใส่ Flash Drive ไปเปิดใช้งานบนเครื่องที่ไม่มีอินเทอร์เน็ต เพียงสร้างโฟลเดอร์ชื่อ `weights` ไว้ข้างไฟล์โปรแกรมหรือข้างไฟล์ `.exe` แล้วนำไฟล์ `.onnx` ทั้ง 3 ไฟล์ไปใส่ไว้ โปรแกรมจะหยิบโมเดลจาก Flash Drive มาใช้งานทันทีโดยไม่ต้องต่อเน็ต
> 
> ⚙️ **การย้ายโฟลเดอร์โมเดลผ่าน Environment Variable**:
> - **บน Linux**: `export REAL_ESRGAN_WEIGHTS_DIR="/mnt/storage/ai_models"`
> - **บน Windows**: `set REAL_ESRGAN_WEIGHTS_DIR=D:\AI_Models`

---

### 6. ตัวอย่างคำสั่งที่ใช้บ่อย (Cheat Sheet: Common Use Cases)

- **[Case 1] 📸 ขยายภาพบุคคล คมชัด ผิวเนียนสมจริง ไร้ฟันซ้อน ด้วย 1-Click Preset**:
  ```bash
  uv run python upscale.py -i ./portraits -o ./output -p portrait
  ```

- **[Case 2] 🎞️ กู้คืนรูปถ่ายเก่า / สแกนฟิล์ม เติมเกรน 35mm ดั้งเดิม**:
  ```bash
  uv run python upscale.py -i ./scans -o ./output -p vintage_film
  ```

- **[Case 3] สปีดเร็วสุด สำหรับงานอนิเมะ/การ์ตูน ขยาย 2 เท่า**:
  ```bash
  uv run python upscale.py -i ./input -o ./output -s 2 -m animevideov3 -t 0
  ```

- **[Case 4] ขยายภาพอนิเมะ/ภาพวาด 4 เท่าแบบคมกริบ (Native 4x)**:
  ```bash
  uv run python upscale.py -i ./input -o ./output -s 4 -m x4plus-anime -t 0
  ```

- **[Case 5] ขยายภาพถ่ายทั่วไป 4 เท่า คุณภาพสูงสุด (โมเดล x4plus ค่าเริ่มต้น)**:
  ```bash
  uv run python upscale.py -i ./photos -o ./photos_4k -s 4 -m x4plus -t 400
  ```

- **[Case 6] รูปต้นฉบับขนาดใหญ่มาก ป้องกัน VRAM 2GB ล้น (Out of Memory)**:
  ```bash
  uv run python upscale.py -i ./large_imgs -o ./output -s 4 -t 200
  ```

- **[Case 7] รีดพลัง CPU เต็มสูบ (เช่น 5 CPU Workers บน Ryzen 4500)**:
  ```bash
  uv run python upscale.py -i ./input -o ./output -c 5 -t 0
  ```

- **[Case 8] เน้นคุณภาพไฟล์ JPG สูงสุด (ลดการบีบอัดภาพ)**:
  ```bash
  uv run python upscale.py -i ./input -o ./output -q 98
  ```

---

### 7. การตรวจสอบประสิทธิภาพการทำงาน (Performance Monitoring)

บนระบบ Linux สามารถเปิดดูการใช้ทรัพยากรขณะ AI กำลัง Upscale ภาพได้:

- **ตรวจสอบการทำงานและการใช้ VRAM ของ GPU (NVIDIA)**:
  ```bash
  watch -n 0.5 nvidia-smi
  ```

- **ตรวจสอบการทำงานและการใช้ VRAM ของ GPU (AMD Radeon)**:
  ```bash
  sudo radeontop
  ```

- **ตรวจสอบการทำงานของ GPU (Intel Arc / Iris Xe)**:
  ```bash
  sudo intel_gpu_top
  ```

- **ตรวจสอบการทำงานของ CPU Cores และ Memory (ทุก Threads)**:
  ```bash
  htop
  ```

---

## 🖥️ การใช้งาน Desktop GUI Application

### การเปิดใช้งานแอปพลิเคชัน
```bash
# เปิดผ่าน uv module:
uv run python -m src.gui.app

# หรือเปิดผ่าน CLI entrypoint script:
uv run upscale-gui
```

### การตั้งค่าฮาร์ดแวร์คู่ขนาน (Hybrid GPU + CPU Concurrency)
- ในกลุ่ม **⚡ Hardware & Concurrency** ทางขวามือของหน้าต่าง:
  - **Enable GPU Worker (Device 0: Vulkan)**: ติ๊กถูกเพื่อดึงพลัง GPU อัตโนมัติ (รองรับทั้ง **AMD Radeon**, **NVIDIA GeForce/RTX** และ **Intel Arc**)
  - **CPU Workers**: กำหนดจำนวน Process ฝั่งซีพียูให้ประมวลผลคู่ขนานไปพร้อมกับ GPU แบบ Hybrid Pipeline (แนะนำ: 3 Workers สำหรับซีพียู 6 Cores)

### ระบบสลับธีม (Theme Switcher)
- บริเวณมุมขวาบนของหน้าต่าง มีปุ่มสลับธีม (Theme Toggle Button)
- **🌙 Dark Mode**: โทนสีมืดสบายตา ไฮไลต์ด้วยสี Indigo & Sky Blue เหมาะกับการทำงานในที่แสงน้อย
- **☀️ Light Mode**: โทนสีสว่างสะอาดตา อ่านตัวหนังสือและตรวจสอบภาพได้ชัดเจนในสภาพแวดล้อมสว่าง

---

## 🧪 การทดสอบระบบ (Automated Tests & Quality Gates)

โปรเจกต์นี้ใช้ `pytest` ร่วมกับ PySide6 Offscreen Platform ในการทดสอบอัตโนมัติ 100%:

```bash
# รันชุดทดสอบทั้งหมด (Unit Tests, GUI Component Tests, Real NCNN Inference Tests)
QT_QPA_PLATFORM=offscreen uv run pytest tests/ -v

# ตรวจสอบ Code Quality & Linting
uv run ruff check src tests upscale.py
```

---

## 📦 การสร้างไฟล์ติดตั้ง (Cross-Platform Standalone Build)

### บน Linux:
```bash
./packaging/build_linux.sh
# ไฟล์โปรแกรมพร้อมรันจะอยู่ที่ dist/RealESRGAN_GUI_Linux/RealESRGAN_GUI
```

### บน Windows:
```cmd
packaging\build_windows.bat
rem ไฟล์โปรแกรมจะอยู่ที่ dist\RealESRGAN_GUI_Windows\RealESRGAN_GUI.exe
```

### สร้างอัตโนมัติผ่าน GitHub Actions CI:
โปรเจกต์มี CI Workflow ใน [`.github/workflows/build-windows.yml`](.github/workflows/build-windows.yml):
- ทำการรันเทส ตรวจสอบความถูกต้อง และ Build ไฟล์ `.exe` บน Windows Server (GitHub Runner)
- บังคับใช้ **Python 3.11** ผ่าน `astral-sh/setup-uv`
- บีบอัดเป็น `RealESRGAN_GUI_Windows_x64.zip` และอัปโหลดเป็น GitHub Artifacts ให้ดาวน์โหลดได้ทันที
- แนบไฟล์ Release ให้อัตโนมัติเมื่อมีการ Push Git Tag (เช่น `v1.0.0`)

---

## 📁 โครงสร้างโปรเจกต์ (Project Architecture)

```text
upscale_project/
├── .gitignore                             # Git ignore configuration
├── pyproject.toml                         # Project metadata, dependencies & build config
├── upscale.py                             # Backward-compatible headless CLI
├── Manual.md                              # Photography theory & parameter tuning guide
├── src/
│   ├── core/                              # Headless AI Processing Engine
│   │   ├── config.py                      # UpscaleConfig dataclass & parameter validation
│   │   ├── models.py                      # Model registry & metadata
│   │   ├── denoise.py                     # Adaptive edge-preserving denoising filter
│   │   ├── face_enhancer.py               # ONNX Face restoration (GFPGAN / CodeFormer)
│   │   ├── worker.py                      # Multi-process GPU & CPU workers
│   │   └── engine.py                      # Queue manager & cooperative cancellation
│   └── gui/                               # PySide6 Desktop GUI Interface
│       ├── app.py                         # Application bootstrap & window setup
│       ├── theme.py                       # Theme manager (Dark / Light stylesheet switching)
│       ├── main_window.py                 # Main application window & layout
│       ├── worker_thread.py               # QThread bridging GUI and core engine
│       └── components/
│           ├── drop_zone.py               # Drag-and-drop batch queue table
│           ├── control_panel.py           # Model & hardware parameters
│           ├── comparison_viewer.py       # Interactive before/after split slider
│           ├── progress_panel.py          # Progress bar, ETA, start/cancel actions
│           └── log_viewer.py              # Color-coded activity logs
├── tests/                                 # Automated Test Suites
│   ├── test_config.py                     # Config & file resolution tests
│   ├── test_denoise.py                    # Denoise & texture preservation tests
│   ├── test_face_enhance.py               # ONNX Face restoration unit tests
│   ├── test_engine.py                     # Queue & lifecycle tests
│   ├── test_gui.py                        # PySide6 components & state tests
│   └── test_integration_upscale.py       # Real NCNN inference & cancellation tests
└── packaging/                             # Standalone Distribution Recipes
    ├── pyinstaller_linux.spec
    ├── pyinstaller_windows.spec
    ├── build_linux.sh
    └── build_windows.bat
```

---

## 📄 License
MIT License
