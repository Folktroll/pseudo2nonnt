import os
import subprocess
import glob
import sys
import argparse

TMP_DIR = "tmp"

# Absolute paths for security
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR_ABS = os.path.abspath(os.path.join(SCRIPT_DIR, TMP_DIR))


def run_command(cmd, cwd=None):
    """Run a shell command and exit on error."""
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        sys.exit(e.returncode)


def safe_remove(path_pattern):
    """Safely remove files only inside TMP_DIR."""
    abs_pattern = os.path.abspath(path_pattern)
    if not abs_pattern.startswith(TMP_DIR_ABS):
        print(f"[SECURITY] Refusing to remove files outside TMP_DIR: {abs_pattern}")
        return
    for f in glob.glob(abs_pattern):
        try:
            os.remove(f)
        except Exception as e:
            print(f"[WARN] Cannot remove {f}: {e}")


# === Command line arguments ===
parser = argparse.ArgumentParser(
    description=(
        "Convert pseudo-NT Garmin IMG to non-NT format.\n"
        "\nRequirements:\n"
        "- GMapTool (gmt.exe) from: https://www.gmaptool.eu/\n"
        "- Garmin GMP Extractor (GarminGMPExtract003.exe) from: https://searchevolution.com/"
    ),
    formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument("input_img", help="Input pseudo-NT IMG file")
args = parser.parse_args()

INPUT_IMG = args.input_img
base_name_noext = os.path.splitext(os.path.basename(INPUT_IMG))[0]
FINAL_IMG = base_name_noext + "-nonnt.img"

# Input file check
if not os.path.exists(INPUT_IMG):
    print(f"[ERROR] Input IMG not found: {INPUT_IMG}")
    sys.exit(1)

# Required executables check
gmp_exe = os.path.join(SCRIPT_DIR, "GarminGMPExtract003.exe")
gmt_exe = os.path.join(SCRIPT_DIR, "gmt.exe")
for exe, name, url, exe_name in (
    (
        gmp_exe,
        "Garmin GMP Extractor",
        "https://searchevolution.com/",
        "GarminGMPExtract003.exe",
    ),
    (gmt_exe, "GMapTool", "https://www.gmaptool.eu/", "gmt.exe"),
):
    if not os.path.exists(exe):
        print(
            f"[ERROR] Missing executable: {exe}\nPlease download {name} from {url} and place '{exe_name}' in the script directory."
        )
        sys.exit(1)

# Create temp directory
os.makedirs(TMP_DIR_ABS, exist_ok=True)

# Step 0: Cleanup
print("=== Step 0: Initial cleanup ===")
safe_remove(os.path.join(TMP_DIR_ABS, "*.*"))

# Step 1: Split IMG into GMP submaps
print("=== Step 1: Split big map into GMP submaps ===")
run_command([gmt_exe, "-v", "-i", "-g", INPUT_IMG, "-o", TMP_DIR_ABS + "\\"])

# Check if GMP files were generated
submaps = glob.glob(os.path.join(TMP_DIR_ABS, "*.GMP"))
if not submaps:
    print("[ERROR] Not pseudo-NT format (no GMP files generated)")
    sys.exit(1)

# Step 2: Process each GMP file
print("=== Step 2: Extract each GMP file ===")
for gmp in submaps:
    base_name = os.path.splitext(os.path.basename(gmp))[0]
    print(f"Processing {base_name}")
    run_command([gmp_exe, os.path.basename(gmp)], cwd=TMP_DIR_ABS)
    safe_remove(gmp)

    run_command(
        [
            gmt_exe,
            "-v",
            "-i",
            "-j",
            "-o",
            f"{base_name}.img",
            f"{base_name}.*",
        ],
        cwd=TMP_DIR_ABS,
    )

# Step 3: Merge final IMG
print("=== Step 3: Merge all into final IMG ===")
run_command([gmt_exe, "-v", "-i", "-j", "-o", FINAL_IMG, f"{TMP_DIR_ABS}\\*.img"])

# Step 4: Cleanup
print("=== Step 4: Final cleanup ===")
safe_remove(os.path.join(TMP_DIR_ABS, "*.*"))

print(f"Done. Final IMG: {FINAL_IMG}")
