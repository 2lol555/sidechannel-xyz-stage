import os
import subprocess
import tempfile
import uuid
import platform
import matplotlib.pyplot as plt


def show_non_interactive_image() -> None:
    temp_dir: str = tempfile.gettempdir()
    guid: str = str(uuid.uuid4())
    output_path: str = os.path.join(temp_dir, guid)
    plt.savefig(output_path)
    output_path += '.png' # Add automatic extension

    # Automatically open the image based on the operating system
    system: str = platform.system()
    if system == 'Windows':
        subprocess.Popen(['start', output_path], shell=True)
    elif system == 'Linux':
        subprocess.Popen(['xdg-open', output_path])
    elif system == 'Darwin':  # macOS
        subprocess.Popen(['open', output_path])
    else:
        print(f"Cannot automatically open image on path {output_path} using operating system: {system}")
