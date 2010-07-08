import gst
import time

from base.gst_test import GstTest

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
		enc = gst.element_factory_make(self.element)
		enc.props.bitrate = self.bitrate
		sink = gst.element_factory_make("fakesink")

		s = gst.Structure("video/x-raw-yuv")
		s["format"] = gst.Fourcc(self.format)
		s["width"] = width
		s["height"] = height
		s["framerate"] = gst.Fraction(self.framerate, 1)
		capf = gst.element_factory_make("capsfilter")
		capf.props.caps = gst.Caps(s)

		p.add(src, capf, enc, sink)
		gst.element_link_many(src, capf, enc, sink)

		sink.connect("handoff", self.handoff)
		sink.set_property("signal-handoffs", True)
		return p

	def handoff(self, element, buffer, pad):
		self.buffer_sizes.append(buffer.size)
		self.buffer_times.append(time.time())
		return True

	def on_stop(self):
		count = len(self.buffer_times) - 1
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

test_class = GstVEncoderTest
