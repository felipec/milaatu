import gst
import time

from base.gst_test import GstTest
from struct import *

import os

class GstVEncoderResolutionTest(GstTest):

	__RESOLUTION_CHANGE_INTERVAL = 3 # interval in seconds

	def __init__(self):
		GstTest.__init__(self)

		self.element = "theoraenc"
		self.num_buffers = 250
		self.bitrate = 0
		self.framerate = 15
		self.framesize = "640x480"
		self.format = "I420"
		self.location = None

		self.buffer_sizes = []
		self.buffer_times = []
		self.mode = None
		self.intra_refresh = None
		self.codec = None

		self.frame_count = 0
		self.bytestream = True
		self.index = 0
		self.caps = None
		self.tested_resolutions = None

	def start(self):
		self.tested_resolutions = self.tested_resolutions.split(";")

		# cache the file
		if self.location:
			os.system("dd if=%s of=/dev/null" % self.location)
		GstTest.start(self)

	def create_pipeline(self):
		p = gst.Pipeline()

		width, height = self.framesize.split("x")
		width, height = int(width), int(height)

		src = gst.element_factory_make("videotestsrc")
		src.props.num_buffers = self.num_buffers
		bitrate = self.bitrate
		scaler = gst.element_factory_make("videoscale")

		enc = gst.element_factory_make(self.element, "encoder")

		if self.mode is not None:
			enc.props.mode = self.mode

		if self.intra_refresh is not None:
			enc.props.intra_refresh = self.intra_refresh

		enc.props.bitrate = bitrate
		ident = gst.element_factory_make("identity")

		sink = gst.element_factory_make("fakesink")

		s = gst.Structure("video/x-raw-yuv")
		s["format"] = gst.Fourcc(self.format)
		s["width"] = width
		s["height"] = height
		s["framerate"] = gst.Fraction(self.framerate, 1)

		caps = gst.element_factory_make("capsfilter", "capsf")
		caps.props.caps = gst.Caps(s)

		p.add(src, scaler, caps, enc, ident, sink)
		gst.element_link_many(src, scaler, caps, enc, ident, sink)

		ident.connect("handoff", self.handoff)
		ident.set_property("signal-handoffs", True)
		return p

	def handoff(self, element, buffer):
		self.frame_count += 1
		if (self.frame_count % (self.framerate * self.__RESOLUTION_CHANGE_INTERVAL) == 0):
			try:
				tmp = self.tested_resolutions[self.index].split(",")
			except IndexError:
				# no more format changes
				return True

			target_res = tmp[0]
			target_bitrate = int(tmp[1])
			target_fps = int(tmp[2])
			target_format = tmp[3]

			self.index += 1
			enc = self.player.get_by_name("encoder")
			enc.props.bitrate = target_bitrate
			caps = self.player.get_by_name("capsf")
			print "Previous caps: " + str(caps.get_property("caps"))

			width, height = [int(x) for x in target_res.split("x")]
			s = gst.Structure("video/x-raw-yuv")
			s["format"] = gst.Fourcc(target_format)
			s["width"] = width
			s["height"] = height
			s["framerate"] = gst.Fraction(target_fps, 1)
			caps.set_property("caps", gst.Caps(s))
			print "Switched to: " + str(caps.get_property("caps"))

		return True

	def on_stop(self):
		count = len(self.buffer_times) - 1
		if self.frame_count <= 50:
			self.error = "Not enough buffers processed"
			return
		self.checks['no-errors'] = 1

test_class = GstVEncoderResolutionTest
