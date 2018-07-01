from urllib.parse import urlparse
import requests
import shlex
import subprocess
import re
import math
import os

from tempfile import NamedTemporaryFile


MIN_SIZE = 1024
MAX_SIZE = 50*1024*1024

ACCEPT_MIMETYPES = [None, 'video/webm', 'video/mp4']
CHUNK_SIZE = 1024

LOUD = -12.0  # if bigger Just loud, most likely not annoying YELLOW  %50
SCREAM = -5.0  # Very loud, if bigger 80% scream ORANGE
DEFENITLY_SCREAM = -0.5  #if bigger then 100% scream RED


FROM_TO_LOUDNESS_BADNESS = {
		 -30:{-15:0, -10:20, -6:40, -3:95,  0:100, 3:100, math.inf: 100},
		 -25:{-15:0, -10:10, -6:30, -3:90,  0:100, 3:100, math.inf: 100},
		 -20:{-15:0, -10:5,  -6:15, -3:80,  0:95,  3:100, math.inf: 100},
		 -15:{-15:0, -10:0,  -6:10, -3:75,  0:80,  3:99,  math.inf: 100},
		 -10:{-15:0, -10:0,  -6:5,  -3:60,  0:70,  3:99,  math.inf: 100},
		 -6 :{-15:0, -10:0,  -6:0,  -3:50,  0:60,  3:95,  math.inf: 100},
	math.inf:{-15:0, -10:0,  -6:0,  -3:40,  0:50,  3:95,  math.inf: 100}
}

ABSOLUTE_LOUDNESS_BADNESS = {-15:0, -10:0, -7:5, -5:30, -3:70, 0:95, math.inf: 100}

def check_min_file_size(size):
	if (size < MIN_SIZE):
		raise Exception('File is too small')

def check_max_file_size(size):
	if (size > MAX_SIZE):
		raise Exception('File is too large')

def download_video(url):
	parsed_url = urlparse(url)

	req = requests.get(url, timeout=120, stream=True)
	if (req.status_code != 200):
		raise Exception('Got code %s while trying to retrieve URL' % req.status_code)

	# if ('Content-Length' in req.headers):
	# 	length = int(req.headers['Content-Length'])
	# 	check_min_file_size(length)
	# 	check_max_file_size(length)

	if (not (req.headers['Content-Type'] in ACCEPT_MIMETYPES)):
		raise Exception('Unsupported content MIME type')

	url_name = parsed_url.path.split('/')[-1] if (not parsed_url.path.endswith('/')) else 'video'

	temp_file = NamedTemporaryFile(prefix=url_name, delete=False)

	content_size = 0
	for chunk in req.iter_content(CHUNK_SIZE):
		content_size += len(chunk)
		check_max_file_size(content_size)
		temp_file.write(chunk)

	check_min_file_size(content_size)

	return temp_file

def analyze_data(data):
	data_records = data['data']
	max_integral_loudness = max(map(lambda record: record['i'], data_records))

	screamer_chance = 0

	if (len(data_records) >= 20):
		for t in range(20, len(data_records)):
			previous_second = sum(map(lambda record: record['m'], data_records[t-10 : t-1])) / 10 #TODO: use data_records[t-1]['i'] instead?
			if (previous_second > -15):
				this_second = max(map(lambda record: record['m'], data_records[t-20 : t-11]))
				current_badness = badness(previous_second, this_second)
				if (current_badness > screamer_chance):
					screamer_chance = current_badness
					#print("%f -> %f: %d" % (this_second, previous_second, current_badness))
	else:
		badness_range = first_leq(max_integral_loudness, ABSOLUTE_LOUDNESS_BADNESS.keys())
		screamer_chance = ABSOLUTE_LOUDNESS_BADNESS[badness_range]
	#TODO: take range into account?
	return {'max_volume': max_integral_loudness, 'screamer_chance': screamer_chance, 'duration_msec': data['duration_msec'], 'volume_range': data['range']}


def first_leq(n, lst):
	return next(x for x in sorted(lst) if x >= n)

def badness(from_loudness, to_loudness):
	'''Sudden great increase of volume may indicate screamer. Or not.
	Anyway it is bad for ears.
	"badness" value may vary from 0 to 100.
	We report max "badness" value as "screamer_chance".'''
	from_range =  first_leq(from_loudness, FROM_TO_LOUDNESS_BADNESS.keys())
	to_ranges = FROM_TO_LOUDNESS_BADNESS[from_range]
	to_range = first_leq(to_loudness, to_ranges.keys())
	return FROM_TO_LOUDNESS_BADNESS[from_range][to_range]


def analyze_video(filename):
	data = None
	cmd = shlex.split('C:/ffmpeg/bin/ffmpeg.exe -hide_banner -filter_complex "ebur128=dualmono=true" -f null - -i "%s"' % filename)
	with NamedTemporaryFile(prefix='ffmpeg_ebur128', mode="w+", encoding='utf-8') as ffmpeg_output:
		subprocess.run(cmd, stdout=ffmpeg_output, stderr=ffmpeg_output, timeout=120)
		ffmpeg_output.seek(0)
		data = parse_ffmpeg_output(ffmpeg_output)

	if (data == None):
		print("ALERY@!!#!#@# " + filename)
		return
		#raise Exception("Can't parse file as video")

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
						  "M:\s*([-\d.]+)\s+"  # Momentary (0.4 sec)
						  "S:\s*([-\d.]+)\s+"  # Short-Term (3 sec)
						  "I:\s*([-\d.]+) LUFS\s+"  # Integrated
						  "LRA:\s*([-\d.]+) LU\s+"  # Range amplitude
						  )
	M = -120.0
	S = -120.0
	for line in file:
		match = re.match(line_reg, line)
		if match:
			M = max(M, float(match.group(2)))
			S = max(S, float(match.group(3)))
	return determine_scream_chance({"M": M, "S": S})

	# duration = None
	# duration_re = re.compile('\\s*Duration: (\\d\\d):(\\d\\d):(\\d\\d).(\\d\\d),.*')

	# #[Parsed_ebur128_0 @ 00000000005afe00] t: 23.303     M: -40.0 S: -39.3     I: -34.5 LUFS     LRA:   6.9 LU  FTPK: -27.9 -28.0 dBFS  TPK: -19.5 -19.5 dBFS
	# #[Parsed_ebur128_0 @ 00000000005ed940] t: 19         M: -56.2 S: -30.5     I: -35.1 LUFS     LRA:  12.6 LU  FTPK: -43.9 dBFS  TPK:  -6.0 dBFS
	# data = []
	# data_re = re.compile (
	# 	'\\[Parsed_ebur128_\\d @ [0-9a-f]{16}\\]\\s+'   #'[Parsed_ebur128_0 @ 00000000005afe00] '
	# 	+ 't:\\s*([\\d.]+)\\s+'                         #'t: 23.303     '     -> '23.303'
	# 	+ 'M:\\s*([-\\d.]+)\\s+'                        #'M: -40.0 '          -> '-40.0'
	# 	+ 'S:\\s*([-\\d.]+)\\s+'                        #'S: -39.3     '      -> '-39.3'
	# 	+ 'I:\\s*([-\\d.]+) LUFS\\s+'                   #'I: -34.5 LUFS     ' -> '-34.5'
	# 	+ 'LRA:\\s*([-\\d.]+) LU\\s+.*'                 #'LRA:   6.9 LU  '    -> '6.9'
	# 	)

	# #'    LRA:         4.2 LU'
	# lra = None
	# lra_re = re.compile('^\\s+LRA:\\s+([\\d.]+) LU')

	# for line in ffmpeg_output:
	# 	data_match = re.match(data_re, line)
	# 	if data_match:
	# 		data.append({'m': float(data_match.group(2)), 'i': float(data_match.group(4))})
	# 	else:
	# 		if (duration == None):
	# 			duration_match = re.match(duration_re, line)
	# 			if (duration_match):
	# 				duration = sum(map(lambda i, msec: int(duration_match.group(i))*msec, [1, 2, 3, 4], [3600*1000, 60*1000, 1000, 10]))

	# 		lra_match = re.match(lra_re, line)
	# 		if (lra_match):
	# 			lra = float(lra_match.group(1))

	# return {'duration_msec': duration, 'data': data, 'range': lra}


def get_data(url):
	data = {}
	data['md5'] = url['md5']
	data['scream_chance'] = analyze_video(download_video(url['url']).name)
	print(data)
	return data