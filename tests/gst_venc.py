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
		self.missed_keyframes = 0
		self.extra_keyframes = 0
		self.bytestream = True
		self.keyframe_interval = 1

		# h264 IDR frames check
		self.missed_iframes = 0
		self.forced_iframe = False
		self.iframe_interval = 0

		self.extra_parameters = {}

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

		for (key, value) in self.extra_parameters.iteritems():
			enc.set_property(key, value)

		if self.element == "x264enc":
			bitrate /= 1000
			enc.props.key_int_max = self.framerate
			enc.props.byte_stream = self.bytestream
			enc.props.aud = False

		if self.mode is not None:
			enc.props.mode = self.mode

		if self.intra_refresh is not None:
			enc.props.intra_refresh = self.intra_refresh

		if self.keyframe_interval is not None:
			enc.props.keyframe_interval = self.keyframe_interval

		if bitrate:
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

	def send_keyframe_event(self):
		struct = gst.Structure("GstForceKeyUnit")
		event = gst.event_new_custom(gst.EVENT_CUSTOM_UPSTREAM, struct)
		self.pipeline.send_event(event)
		return True

	def check_keyframe_interval(self, type, buffer, timestamp):
		if self.keyframe_interval == 0:
			return

		got_i_slices = False
		if (type == 1 or type == 5):
			v = unpack_from('b', buffer, 5)[0]
			# first_mb_in_slice = 0 (1 in ue)
			# slice_type = 2 or 7 (011 or 0001000 in ue)
			if (v & 0xf0 == 0xb0) or (v == 0x88):
				got_i_slices = True

		if ((timestamp / gst.SECOND) % self.keyframe_interval == 0):
			if (not got_i_slices):
				self.missed_keyframes += 1
		else:
			if (type == 5 or type == 7 or type == 8 or got_i_slices):
				self.extra_keyframes += 1

	def check_iframe_interval(self, type, buffer, timestamp):
		if self.iframe_interval == 0:
			return

		iframe_pos = (timestamp / gst.SECOND) % self.iframe_interval
		if (iframe_pos == 0):
			self.forced_iframe = True
			self.send_keyframe_event()
		elif self.forced_iframe:
			if type != 5:
				max_iframe_delay = 1.0 / self.framerate * 8 # 5 frames
				if iframe_pos > max_iframe_delay:
					self.missed_iframes += 1
				else:
					return
			self.forced_iframe = False

	def handoff(self, element, buffer, pad):
		if self.codec == "h264":
			timestamp = float(buffer.timestamp)
			if timestamp > 0:
				type = unpack_from('b', buffer, 4)[0] & 0x1f
				self.check_keyframe_interval(type, buffer, timestamp)
				self.check_iframe_interval(type, buffer, timestamp)
		self.buffer_sizes.append(buffer.size)
		self.buffer_times.append(time.time())
		return True

	def on_stop(self):
		count = len(self.buffer_times) - 1
		if count <= 0:
			self.error = "No buffers processed"
			return
		total_time = self.buffer_times[-1] - self.buffer_times[0]
		tgt_time = float(self.num_buffers) / self.framerate
		fps = count / total_time
		bt = sum(self.buffer_sizes) / tgt_time * 8
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
				print "missed by %i%%" % (abs(tbt - bt) / tbt * 100)
		if self.codec == "h264":
			self.checks['keyframes-ok'] = self.missed_keyframes == 0 and self.extra_keyframes == 0
			self.checks['iframes-ok'] = self.missed_iframes == 0

test_class = GstVEncoderTest
