import gst
import time

from base.gst_test import GstTest
from struct import *

import os

class GstVEncoderTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = "theoraenc"
		self.num_buffers = 100
		self.bitrate = 0
		self.framerate = 15
		self.framesize = "640x480"
		self.expected_framerate = 0
		self.deviation = 0.15
		self.format = "I420"
		self.location = None

		self.buffer_sizes = []
		self.buffer_times = []
		self.mode = None
		self.intra_refresh = None
		self.codec = None

		# h264 keyframe check
		self.total_count = 0
		self.missed_keyframes = 0
		self.bytestream = True

	def start(self):
		# cache the file
		if self.location:
			os.system("dd if=%s of=/dev/null" % self.location)
		GstTest.start(self)

	def create_pipeline(self):
		p = gst.Pipeline()

		width, height = self.framesize.split("x")
		width, height = int(width), int(height)

		if self.location:
			src = gst.element_factory_make("filesrc")
			src.props.num_buffers = self.num_buffers
			src.props.location = self.location
			if self.format == "I420":
				bpp = 1.5
			elif self.format == "UYVY":
				bpp = 2
			src.props.blocksize = int(width * height * bpp)
		else:
			src = gst.element_factory_make("videotestsrc")
			src.props.num_buffers = self.num_buffers
		bitrate = self.bitrate
		enc = gst.element_factory_make(self.element)
		if self.element == "x264enc":
			bitrate /= 1000
			enc.props.key_int_max = self.framerate
			enc.props.byte_stream = self.bytestream
			enc.props.aud = False

		if self.mode is not None:
			enc.props.mode = self.mode

		if self.intra_refresh is not None:
			enc.props.intra_refresh = self.intra_refresh

		enc.props.bitrate = bitrate
		sink = gst.element_factory_make("fakesink")

		s = gst.Structure("video/x-raw-yuv")
		s["format"] = gst.Fourcc(self.format)
		s["width"] = width
		s["height"] = height
		s["framerate"] = gst.Fraction(self.framerate, 1)

		if self.codec == "h264":
			capf_raw = gst.element_factory_make("capsfilter")
			capf_raw.props.caps = gst.Caps(s)

			s = gst.Structure("video/x-h264")
			if self.bytestream:
				s["stream-format"] = "byte-stream"
			else:
				s["stream-format"] = "avc"
			capf_enc = gst.element_factory_make("capsfilter")
			capf_enc.props.caps = gst.Caps(s)

			p.add(src, capf_raw, enc, capf_enc, sink)
			gst.element_link_many(src, capf_raw, enc, capf_enc, sink)
		else:
			capf = gst.element_factory_make("capsfilter")
			capf.props.caps = gst.Caps(s)

			p.add(src, capf, enc, sink)
			gst.element_link_many(src, capf, enc, sink)

		sink.connect("handoff", self.handoff)
		sink.set_property("signal-handoffs", True)
		return p

	def handoff(self, element, buffer, pad):
		if self.codec == "h264":
			if self.total_count > 0:
				type = unpack_from('b', buffer, 4)[0] & 0x1f
				if (self.total_count % self.framerate == 0 and type != 7 and type != 8):
					self.missed_keyframes += 1
			self.total_count += 1
		self.buffer_sizes.append(buffer.size)
		self.buffer_times.append(time.time())
		return True

	def on_stop(self):
		count = len(self.buffer_times) - 1
		if count <= 0:
			self.error = "No buffers processed"
			return
		total_time = self.buffer_times[-1] - self.buffer_times[0]
		fps = count / total_time
		bt = sum(self.buffer_sizes) / total_time * 8
		self.out['framerate'] = int(fps)
		self.out['bitrate'] = int(bt)
		if self.expected_framerate:
			if fps >= self.expected_framerate:
				self.checks['framerate'] = 1
			else:
				self.checks['framerate'] = 0
		tbt = self.bitrate
		if tbt:
			dev = self.deviation
			if (bt > tbt - (tbt * dev)) and (bt < tbt + (tbt * dev)):
				self.checks['bitrate'] = 1
			else:
				self.checks['bitrate'] = 0
		if self.codec == "h264":
			self.checks['keyframes-ok'] = self.missed_keyframes == 0

test_class = GstVEncoderTest
