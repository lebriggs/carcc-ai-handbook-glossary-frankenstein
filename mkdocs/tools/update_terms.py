"""When you have a need for speed.
Runs the glossary generation tools in order.
"""

# subprocess runs the two glossary tool scripts.
# sys provides the current Python executable and lets the wrapper exit cleanly.

import subprocess
import sys

try:
    # Run the variant scanner first.
    # generate_tooltips.py uses the generated variant_terms.txt file.
    subprocess.run([sys.executable, "tools/variant_scanner.py"], check=True)

    # Only runs if the variant scanner finished successfully.
    subprocess.run([sys.executable, "tools/generate_tooltips.py"], check=True)

except subprocess.CalledProcessError:
    # Stop the wrapper cleanly without printing a Python traceback.
    sys.exit(1)

print("HEY! The two glossary files were generated. I have to do everything.")
