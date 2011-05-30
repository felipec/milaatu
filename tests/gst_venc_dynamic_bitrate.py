import gst

from base.gst_test import GstTest
from struct import *

import os
import glib

class GstVEncoderBitrateTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = "dsph264enc"
		self.num_buffers = 1000
		self.bitrate = 0
		self.framerate = 30
		self.framesize = "640x480"
		self.format = "I420"
		self.location = None
		self.bitrateseq = None
		self.max_bitrate = 2000000
		self.deviation = 15

		self.buffer_sizes = []
		self.buffer_times = []
		self.bitrates = []
		self.mode = None
		self.intra_refresh = None
		self.codec = None
		self.ignored_first = False

	def start(self):
		# cache the file
		if self.location:
			os.system("dd if=%s of=/dev/null" % self.location)
		GstTest.start(self)
		self.ignored_first = False

	def create_pipeline(self):
		p = gst.Pipeline()

		width, height = self.framesize.split("x")
		width, height = int(width), int(height)
		if self.location:
			src = gst.element_factory_make("filesrc")
			src.props.location = self.location
			if self.format == "I420":
				bpp = 1.5
			elif self.format == "UYVY":
				bpp = 2
			src.props.blocksize = int(width * height * bpp)
		else:
			src = gst.element_factory_make("videotestsrc")
		src.props.num_buffers = self.num_buffers

		self.bitrates = self.bitrateseq.split(',')
		bitrate = self.bitrate
		enc = gst.element_factory_make(self.element, "encoder")
		enc.props.bitrate = bitrate
		enc.props.max_bitrate = self.max_bitrate

		if self.mode is not None:
			enc.props.mode = self.mode

		if self.intra_refresh is not None:
			enc.props.intra_refresh = self.intra_refresh

		s = gst.Structure("video/x-raw-yuv")
		s["format"] = gst.Fourcc(self.format)
		s["width"] = width
		s["height"] = height
		s["framerate"] = gst.Fraction(self.framerate, 1)

		capf_raw = gst.element_factory_make("capsfilter")
		capf_raw.props.caps = gst.Caps(s)

		ident = gst.element_factory_make("identity")
		videorate = gst.element_factory_make("videorate")
		sink = gst.element_factory_make("fakesink")

		p.add(src, capf_raw, videorate, enc, ident, sink)
		gst.element_link_many(src, capf_raw, videorate, enc, ident, sink)

		ident.connect("handoff", self.handoff)
		ident.set_property("signal-handoffs", True)

		return p

	def handoff(self, element, buffer):
		if not self.ignored_first:
			self.ignored_first = True
			return True

		self.buffer_sizes.append(buffer.size)
		buffer_ts = float(buffer.timestamp) / gst.SECOND
		self.buffer_times.append(buffer_ts)

		if (len(self.bitrates) > 0):
			next_change = float(self.bitrates[0].split(':')[0])
			if (buffer_ts >= next_change):
				br = int(self.bitrates[0].split(':')[1])
				enc = self.player.get_by_name("encoder")
				enc.props.bitrate = br
				self.bitrates.pop(0)
		return True

	def on_stop(self):
		count = len(self.buffer_times)
		if count <= 0:
			self.error = "No buffers processed"
			return

		self.checks["bitrate"] = 1
		sliding_window = []     # array for 1s of timestamps
		bsizes = []             # array for 1s of buffer sizes
		delta = 0
		bitrate_checks = self.bitrateseq.split(',')
		bitrate_target = self.bitrate
		for index, btime in enumerate(self.buffer_times):
			if (btime < 1.0):
				# ignore buffers for the first second
				continue
			if (len(bitrate_checks) > 0):
				next_change = float(bitrate_checks[0].split(':')[0])
				if (btime >= next_change):
					bitrate_target = int(bitrate_checks[0].split(':')[1])
					if ((btime - next_change) < 1.0):
						# ignore buffers one second after changing the bitrate
						continue
					bitrate_checks.pop(0)
					sliding_window = []
					bsizes = []

			sliding_window.insert(0, btime)
			bsizes.insert(0, self.buffer_sizes[index])

			try:
				delta = self.buffer_times[index + 1] - sliding_window[len(sliding_window) - 1]
				if delta <= 1:
					continue

				if not self.check_bitrate_error(bsizes, bitrate_target):
					break

				while delta > 1:
					sliding_window.pop(len(sliding_window) - 1)
					bsizes.pop(len(bsizes) - 1)
					delta = self.buffer_times[index + 1] - sliding_window[len(sliding_window) - 1]
			except IndexError:
				# exception is reached when self.buffer_times[index + 1] goes out of bounds
				self.check_bitrate_error(bsizes, bitrate_target)

	def check_bitrate_error(self, bsizes, bitrate_target):
		win_bits = sum(bsizes) * 8
		bitrate_error = abs(float((bitrate_target - win_bits)) / bitrate_target * 100)
		if bitrate_error > self.deviation:
			self.checks["bitrate"] = 0
			self.error = "Bitrate verification failed"
			return False

		return True

test_class = GstVEncoderBitrateTest
