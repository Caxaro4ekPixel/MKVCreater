import subprocess
import os
import json
from app.config import ffmpeg_path, ffprobe_path, mkvmerge
from pymediainfo import MediaInfo
from app.utils import get_font_files


def run_command(cmd, signal_handler):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                               universal_newlines=True, encoding='utf-8')
    for line in process.stdout:
        signal_handler.log_message.emit(line.strip())
    process.stdout.close()
    return_code = process.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


def convert_audio_to_aac(input_audio, signal_handler):
    cmd_probe = [
        ffprobe_path,
        '-loglevel', 'error',
        '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_name',
        '-of', 'default=nokey=1:noprint_wrappers=1',
        input_audio
    ]

    probe_process = subprocess.Popen(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     encoding='utf-8')
    codec_name, probe_errors = probe_process.communicate()

    if 'aac' in codec_name.strip():
        signal_handler.log_message.emit("Входной звук уже в формате AAC. Никакого преобразования не требуется.")
        return input_audio

    output_audio = os.path.splitext(input_audio)[0] + "_converted.aac"
    cmd_convert = [
        ffmpeg_path,
        '-y',
        '-i', input_audio,
        '-acodec', 'aac',
        '-ac', '2',
        '-ar', '48000',
        '-b:a', '192k',
        output_audio
    ]

    run_command(cmd_convert, signal_handler)
    return output_audio


def get_stream_indexes(file_path, signal_handler):
    cmd = [
        ffprobe_path,
        '-v', 'error',
        '-print_format', 'json',
        '-show_streams',
        file_path
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                               text=True, encoding='utf-8')
    output, errors = process.communicate()

    if errors:
        signal_handler.log_message.emit("Ошибка: " + errors)

    streams = json.loads(output)['streams']
    signal_handler.log_message.emit(f"Потоки: {streams}")

    audio_stream_jpn_index = None
    audio_stream_any_index = None
    temp_audio_index = 0
    for stream in streams:
        if stream['codec_type'] == 'audio':
            if 'tags' in stream and 'language' in stream['tags'] and stream['tags']['language'] == 'jpn':
                audio_stream_jpn_index = temp_audio_index
                break
            if audio_stream_any_index is None:
                audio_stream_any_index = temp_audio_index
            temp_audio_index += 1

    audio_stream_index = audio_stream_jpn_index if audio_stream_jpn_index is not None else audio_stream_any_index
    signal_handler.log_message.emit(f"Индекс аудиопотока: {audio_stream_index}")
    return audio_stream_index


def remove_delay(input_file, signal_handler):
    rel = {}
    audio_count = 0
    media_info = MediaInfo.parse(input_file)
    for track in media_info.tracks:
        if track.track_type == 'Audio':
            rel[track.track_id] = -track.delay_relative_to_video
            audio_count += 1
    signal_handler.log_message.emit(f"Detected audio tracks: {audio_count}")
    if audio_count == 1:
        audio = ['--sync !num:!rel ']
    elif audio_count == 2:
        audio = ['--sync !num:!rel ',
                 '--sync !num:!rel ']
    else:
        audio = ['']
    params = audio
    cmd_param = ''
    param_id = 0
    for track in rel.keys():
        repl = str(track - 1).replace('!rel', str(rel.get(track)))
        cmd_param += params[param_id].replace('!num', repl).replace('!rel', str(rel.get(track)))
        param_id += 1
    temp_output = input_file.replace('.mkv', '_fixed.mkv')
    cmd = f'"{mkvmerge}" -o "{temp_output}" {cmd_param} "{input_file}"'
    run_command(cmd, signal_handler)

    if os.path.exists(input_file):
        os.remove(input_file)
    os.rename(temp_output, input_file)


def create_enhanced_mkv(input_file, additional_audio, subtitle_signs, subtitle_full, font_directory, output_file,
                        is_remove_delay, is_convert_audio, progress_callback, signal_handler):
    try:
        progress_callback(1)
        if is_convert_audio:
            additional_audio = convert_audio_to_aac(additional_audio, signal_handler)
        progress_callback(5)
    except Exception as e:
        signal_handler.log_message.emit(f"Не удалось конвертировать аудиофайл: {e}")
        return

    audio_index = get_stream_indexes(input_file, signal_handler)
    progress_callback(10)
    cmd = [ffmpeg_path, '-y']

    cmd += [
        '-i', input_file,
        '-i', additional_audio,
        '-i', subtitle_signs,
        '-i', subtitle_full
    ]
    progress_callback(15)
    if font_directory:
        font_files = get_font_files(font_directory)
        for font_file in font_files:
            cmd += ['-attach', font_file, '-metadata:s:t', 'mimetype=application/x-truetype-font']
    progress_callback(30)
    cmd += [
        '-map', '0:v',
        '-map', '1:a:0',
        '-map', f'0:a:{audio_index}',
        '-map', '2:s:0',
        '-map', '3:s:0',
        '-metadata:s:v:0', 'language=jpn', '-metadata:s:v:0', 'title=Original', '-disposition:v:0', 'default',
        '-metadata:s:a:0', 'language=rus', '-metadata:s:a:0', 'title=AniLibria', '-disposition:a:0', 'default',
        '-metadata:s:a:1', 'language=jpn', '-metadata:s:a:1', 'title=Original', '-disposition:a:1', '0',
        '-metadata:s:s:0', 'language=rus', '-metadata:s:s:0', 'title=Надписи', '-disposition:s:0', 'default',
        '-metadata:s:s:1', 'language=rus', '-metadata:s:s:1', 'title=Субтитры', '-disposition:s:1', '0',
        '-c', 'copy',
        '-bitexact',
        output_file
    ]
    progress_callback(40)
    run_command(cmd, signal_handler)
    progress_callback(90)

    if is_remove_delay:
        signal_handler.log_message.emit(f"Удаление задержки для: {output_file}")
        remove_delay(output_file, signal_handler)
    progress_callback(100)
