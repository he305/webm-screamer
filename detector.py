from urllib.parse import urlparse
import requests
import shlex
import subprocess
import re
import math
import os
from tempfile import NamedTemporaryFile

ACCEPT_MIMETYPES = [None, 'video/webm', 'video/mp4']

LOUD = -12.0  # if bigger Just loud, most likely not annoying YELLOW  %50
SCREAM = -5.0  # Very loud, if bigger 80% scream ORANGE
DEFENITLY_SCREAM = -0.5  #if bigger then 100% scream RED


def download_video(url):
	parsed_url = urlparse(url)

	req = requests.get(url, timeout=300)
	if (req.status_code != 200):
		raise Exception('Got code %s while trying to retrieve URL' % req.status_code)

	if (not (req.headers['Content-Type'] in ACCEPT_MIMETYPES)):
		raise Exception('Unsupported content MIME type')

	url_name = parsed_url.path.split('/')[-1] if (not parsed_url.path.endswith('/')) else 'video'
	
	temp_file = None

	with open(url_name, 'wb') as temp_file:
	    temp_file.write(req.content)

	return temp_file


def analyze_video(filename):
	data = None
	cmd = shlex.split('ffmpeg -hide_banner -vn -filter_complex "ebur128=dualmono=true" -f null - -i "%s"' % filename)
	with NamedTemporaryFile(prefix='ffmpeg_ebur128', mode="w+", encoding='utf-8') as ffmpeg_output:
		subprocess.run(cmd, stdout=ffmpeg_output, stderr=ffmpeg_output, timeout=300)
		ffmpeg_output.seek(0)
		data = parse_ffmpeg_output(ffmpeg_output)

	if (data == None):
		print("ALERY@!!#!#@# " + filename)
		
		raise Exception("Can't parse file as video")

	os.remove(filename)
	return data

def determine_scream_chance(parsed):
	print(parsed)
	if any(v >= DEFENITLY_SCREAM for v in parsed.values()):
		print(parsed.values())
		return 1.0
	elif any(v >= SCREAM for v in parsed.values()):
		return 0.8
	elif any(v >= LOUD for v in parsed.values()):
		return 0.5
	else:
		return 0.0

def parse_ffmpeg_output(file):


	line_reg = re.compile(r"\[Parsed_ebur128_\d @ [0-9a-z]{2,16}\]\s+"
						  "t:\s*([\d.]+)\s+"  # Current time in seconds
						  "TARGET:\s*([-\d]+)\s+LUFS\s+"
						  "M:\s*([-\d.]+)\s+"  # Momentary (0.4 sec)
						  "S:\s*([-\d.]+)\s+"  # Short-Term (3 sec)
						  "I:\s*([-\d.]+) LUFS\s+"  # Integrated
						  "LRA:\s*([-\d.]+) LU\s+"
						  )
	M = -120.0
	S = -120.0
	for line in file:
		match = re.match(line_reg, line)
		if match:
			M = max(M, float(match.group(2)))
			S = max(S, float(match.group(3)))
	return determine_scream_chance({"M": M, "S": S})


def get_data(url):
	data = {}
	data["md5"] = url['md5']
	data["scream_chance"] = analyze_video(download_video("http://2ch.hk" + url['url']).name)
	return data