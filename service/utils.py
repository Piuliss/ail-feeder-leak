import os
import shutil
import string
import unicodedata

import magic
import patoolib

# Characters authorized in filenames
WHITELISTED_FILENAME_CHARS = f"-() {string.ascii_letters}{string.digits}"


def if_binary_move(file_full_path, leak_destination_path):
    """
    Check if file is binary and move it to unprocessed folder
    Returns True if file was moved (binary), False if it's text
    """
    result = False
    try:
        mime = magic.Magic(mime=True)
        mimetype = mime.from_file(file_full_path)
        
        # Check if it's a binary application file (not text)
        if mimetype.rsplit('/', 1)[0] == "application":
            print(f"Binary detected: {os.path.basename(file_full_path)} ({mimetype})")
            print(f"Moving to unprocessed files")
            if os.path.exists(file_full_path):
                shutil.move(file_full_path, leak_destination_path)
            result = True  # File was moved
        else:
            # It's text or other processable format
            print(f"Text file detected: {os.path.basename(file_full_path)} ({mimetype})")
            result = False  # File stays for processing
    except Exception as e:
        print(f"Error checking file type: {e}")
        result = False
    
    return result


def clean_filename(filename):
    """
    Render a valid filename for the feeder 
    """
    # Remove whitespaces
    cleaned_filename = filename.replace(' ', '-')
    # Keep only valid ascii chars
    cleaned_filename = unicodedata.normalize('NFKD', cleaned_filename).encode('ASCII', 'ignore').decode()
    # Keep only whitelisted chars
    return ''.join(c for c in cleaned_filename if c in WHITELISTED_FILENAME_CHARS)


def is_compressed_file_ext(filename):
    """
    Check if filename extension is in the list of allowed compressed file format
    """    
    return filename.lower().endswith(patoolib.ArchiveFormats)


def get_list_of_files(leaks_dir, unprocessed_dir):
    """
    Render a list of leak files
    Uncompress compressed files, sanitize filenames, move unprocessable files 
    """
    print(f"[DEBUG] Scanning directory: {leaks_dir}")
    
    # Search for compressed files and extract them in Leaks Folder
    list_of_files = sorted(filter(lambda x: os.path.isfile(os.path.join(leaks_dir, x)), os.listdir(leaks_dir)))
    print(f"[DEBUG] Files found: {list_of_files}")
    
    for cur_file in list_of_files:
        full_path = os.path.join(leaks_dir, cur_file)
        
        # Extract compressed files
        if is_compressed_file_ext(cur_file):
            print(f"[INFO] Extracting: {cur_file}")
            try:
                patoolib.extract_archive(full_path, verbosity=0, outdir=leaks_dir, interactive=False)
                if os.path.exists(full_path):
                    os.unlink(full_path)
                print(f"[INFO] Extracted and removed: {cur_file}")
            except Exception as e:
                print(f"[ERROR] Failed to extract {cur_file}: {e}")
            continue
        
        # Check if binary and move if needed
        if if_binary_move(full_path, unprocessed_dir):
            # File was moved, skip to next
            continue

    # Move directories to Unprocessed Folder
    # Only keep flattened uncompressed files
    list_of_directories = sorted(filter(lambda x: os.path.isdir(os.path.join(leaks_dir, x)), os.listdir(leaks_dir)))
    for cur_dir in list_of_directories:
        source_dir = os.path.join(leaks_dir, cur_dir)
        print(f"[INFO] Moving directory to unprocessed: {cur_dir}")
        try:
            shutil.move(source_dir, unprocessed_dir)
        except Exception as e:
            print(f"[ERROR] Failed to move directory {cur_dir}: {e}")

    # Sanitize filenames
    list_of_files = sorted(filter(lambda x: os.path.isfile(os.path.join(leaks_dir, x)), os.listdir(leaks_dir)))
    for cur_file in list_of_files:
        sanitize_filename = clean_filename(cur_file)
        if sanitize_filename != cur_file:
            print(f"[INFO] Sanitizing: {cur_file} -> {sanitize_filename}")
            sanitize_filepath = os.path.join(leaks_dir, sanitize_filename)
            try:
                os.rename(os.path.join(leaks_dir, cur_file), sanitize_filepath)
            except Exception as e:
                print(f"[ERROR] Failed to rename {cur_file}: {e}")

    # Get and return final leak files to process
    list_of_files = sorted(filter(lambda x: os.path.isfile(os.path.join(leaks_dir, x)), os.listdir(leaks_dir)))
    print(f"[DEBUG] Final files to process: {list_of_files}")
    return list_of_files


if __name__ == "__main__":
    # zip gunzip, rar, tar
    print(patoolib.ArchiveFormats)