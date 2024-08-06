import subprocess
import tkinter as tk
from tkinter import filedialog, ttk
import os
import json
import threading

with open('config.json') as config_file:
    mkvmerge_path = json.load(config_file)['mkvmerge_path']


def update_progress_bar(progress_bar, process):
    while process.poll() is None:
        line = process.stdout.readline()
        if line:
            if "Progress:" in line:
                try:
                    percent = int(line.split("Progress:")[1].strip().replace("%", ""))
                    progress_bar['value'] = percent
                except ValueError:
                    pass
    progress_bar['value'] = 100


def create_mkv(source_video_path, additional_audio_path, sign_subtitle_path, full_subtitle_path, font_directory,
               output_path, progress_bar):
    font_attachments = []
    if font_directory and os.path.isdir(font_directory):
        for font_file in os.listdir(font_directory):
            font_path = os.path.join(font_directory, font_file)
            font_path = font_path.replace("\\", "/")
            if os.path.isfile(font_path):
                font_attachments.extend([
                    "--attachment-name", os.path.basename(font_path),
                    "--attachment-mime-type", "application/x-truetype-font",
                    "--attach-file", font_path
                ])

    mkvmerge_command = [
                           mkvmerge_path, "-o", output_path,
                           "--language", "0:jpn", "--track-name", "0:Original", "--default-track", "0:yes",
                           "--video-tracks", "0", "-A", "-S", "-B",
                           source_video_path,
                           "--language", "0:rus", "--track-name", "0:AniLibira.TV", "--default-track", "0:yes",
                           additional_audio_path,
                           "-D", "-S", "-B", "-a", "1", "--default-track", "1:no", "--language", "1:jpn",
                           "--track-name", "1:Original",
                           source_video_path,
                           "--language", "0:rus", "--track-name", "0:Надписи", "--default-track", "0:yes",
                           sign_subtitle_path,
                           "--language", "0:rus", "--track-name", "0:Субтитры", "--default-track", "0:no",
                           full_subtitle_path,
                       ] + font_attachments

    process = subprocess.Popen(mkvmerge_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True, bufsize=1)

    threading.Thread(target=update_progress_bar, args=(progress_bar, process)).start()


def browse_file(entry):
    filepath = filedialog.askopenfilename()
    entry.delete(0, tk.END)
    entry.insert(0, filepath)


def browse_folder(entry):
    folderpath = filedialog.askdirectory()
    entry.delete(0, tk.END)
    entry.insert(0, folderpath)


def build_interface():
    root = tk.Tk()
    root.title("MKV Builder")
    root.geometry("600x400")

    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(padx=10, pady=10, expand=True, fill='both')

    def create_input_row(parent, label_text, browse_command):
        frame = tk.Frame(parent)
        frame.pack(fill='x', pady=5, expand=True)
        label = tk.Label(frame, text=label_text, width=20, anchor='w')
        label.pack(side='left')
        entry = tk.Entry(frame, width=50)
        entry.pack(side='left', expand=True, fill='x')
        button = tk.Button(frame, text="Browse", command=lambda: browse_command(entry))
        button.pack(side='left', padx=5)
        return entry

    video_entry = create_input_row(main_frame, "Video File:", browse_file)
    audio_entry = create_input_row(main_frame, "Audio File (AniLibira.TV):", browse_file)
    sign_entry = create_input_row(main_frame, "Sign Subtitle File:", browse_file)
    subtitle_entry = create_input_row(main_frame, "Full Subtitle File:", browse_file)
    font_folder_entry = create_input_row(main_frame, "Font Folder:", browse_folder)
    output_entry = create_input_row(main_frame, "Output MKV File:", browse_file)

    progress_bar = ttk.Progressbar(main_frame, orient='horizontal', length=400, mode='determinate')
    progress_bar.pack(pady=10)

    create_button = tk.Button(main_frame, text="Create MKV", command=lambda: create_mkv(
        video_entry.get(),
        audio_entry.get(),
        sign_entry.get(),
        subtitle_entry.get(),
        font_folder_entry.get(),
        output_entry.get(),
        progress_bar
    ))
    create_button.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    build_interface()
