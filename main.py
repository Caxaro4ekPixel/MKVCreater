import json
import os
from pathlib import Path

conf = json.load(open('E:\Python\MKVCreater\config.json', encoding='utf-8'))


def build_mkv(video_file, audio_file, subtitle_files, font_dir, output_file):
    font_files = " ".join(map(lambda x: f"--attach-file \"{x.absolute()}\"", font_dir.iterdir()))
    command = 'mkvmerge -o "{0}" --video-tracks 0 -A -S -B --default-track 0:yes --language 0:jpn --track-name 0:"Original" "{1}" --default-track 0:yes --language 0:rus --track-name 0:"AniLibria.TV" "{2}" -D -S -B -a 1 --default-track 1:no --language 1:jpn --track-name 1:"Original" "{3}" --language 0:rus --track-name 0:"Надписи" "{4}" --language 0:rus --track-name 0:"Субтитры" "{5}" --attachment-mime-type application/octet-stream  {6}'.format(
        output_file, video_file, audio_file, video_file, subtitle_files['sign'], subtitle_files['full'], font_files)
    print(command)
    os.system(command)


base_path = Path(conf['base_path'])

series_path = (base_path / conf["release_path"] / conf["series"] / "готово")

file_video_name = conf['orig_file_video_name']
file_signs_name = conf['orig_file_signs_name']
file_subs_name = conf['orig_file_subs_name']
file_audio_name = conf['orig_file_audio_name']

video_file = (series_path / file_video_name).absolute()
# is_flac = (series_path / "audio.flac").exists()
# audio_file = ((series_path / "audio.flac").absolute()) if is_flac else ((series_path / "audio.m4a").absolute())
audio_file = (series_path / file_audio_name).absolute()
subtitle_files = {
    "sign": (series_path / file_signs_name).absolute(),
    "full": (series_path / file_subs_name).absolute()
}
font_dir = series_path / "fonts"
output_file = (Path(conf['output_path']) / conf["file_output_name"]).absolute()

build_mkv(video_file, audio_file, subtitle_files, font_dir, output_file)
