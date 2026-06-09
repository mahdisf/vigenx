import subprocess
import os
import shutil


def separate_vocals_with_demucs(input_audio_path: str, output_dir: str) -> dict:
    """
    Separates vocals from an audio file using Demucs.
    """
    if not shutil.which("demucs"):
        return {"error": "Demucs is not installed or not in the system's PATH. Please run 'pip install demucs'."}

    model_name = 'mdx_extra_q'
    
    print(f"Running Demucs on {input_audio_path} with model {model_name}...")
    
    # --- FINAL FIX: Add '--two-stems' to force "no_vocals.wav" output ---
    command = ["demucs", "--two-stems", "vocals", "-n", model_name, "-o", output_dir, input_audio_path]
    
    try:
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        print("Demucs process finished successfully.")
        print(process.stdout)

        vocals_path = None
        no_vocals_path = None

        for root, dirs, files in os.walk(output_dir):
            if "vocals.wav" in files:
                vocals_path = os.path.join(root, "vocals.wav")
            if "no_vocals.wav" in files:
                no_vocals_path = os.path.join(root, "no_vocals.wav")
            
            if vocals_path and no_vocals_path:
                break

        if vocals_path and no_vocals_path:
            print(f"Found separated files:\n  - Vocals: {vocals_path}\n  - No Vocals: {no_vocals_path}")
            return {
                "vocals": vocals_path,
                "no_vocals": no_vocals_path
            }
        else:
            searched_path = os.path.join(output_dir, model_name)
            return {"error": f"Demucs ran, but output files (vocals.wav, no_vocals.wav) were not found inside {searched_path}"}

    except subprocess.CalledProcessError as e:
        print("Error running Demucs:")
        print(e.stderr)
        return {"error": e.stderr}


# --- How to use it in your huge Python 3.11 code ---
if __name__ == "__main__":
    audio_file = "audio_only.mp3"  # Your input audio file
    output_folder = "separated_audio"

    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    result = separate_vocals_with_demucs(audio_file, output_folder)

    if "error" in result:
        print(f"An error occurred: {result['error']}")
    else:
        print("\nSeparation complete!")
        print(f"  - Vocals saved to: {result['vocals']}")
        print(f"  - Background sound saved to: {result['no_vocals']}") # This is the file you need