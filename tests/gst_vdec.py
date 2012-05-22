import gst
import time
import os

from base.gst_test import GstTest

class GstVDecoderTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = None
		self.num_buffers = 500
		self.expected_framerate = 0
		self.expected_max_delay = 0

		self.buffer_times = []

	def pad_add(self, demuxer, pad):
		if not pad.is_linked():
			dec_pad = self.dec.get_pad("sink")
			try:
				pad.link(dec_pad)
			except gst.LinkError:
				pass

	def create_pipeline(self):
		p = gst.Pipeline()

		src = gst.element_factory_make("filesrc")
		src.props.num_buffers = self.num_buffers
		src.props.location = self.location

		ext = os.path.splitext(self.location)[1].lower()
		ext_demux = {
				".asf": "asfdemux",
				".wmv": "asfdemux",
				".mp4": "qtdemux",
				".mov": "qtdemux",
				".avi": "avidemux",
				".mkv": "matroskademux",
				".gdp": "gdpdepay" }

		demux = gst.element_factory_make(ext_demux.get(ext))
		dec = gst.element_factory_make(self.element)
		sink = gst.element_factory_make("fakesink")

		p.add(src, demux, dec, sink)
		src.link(demux)
		try:
			demux.link(dec)
		except gst.LinkError:
			demux.connect("pad-added", self.pad_add)
		dec.link(sink)

		self.dec = dec

		sink.connect("handoff", self.handoff)
		sink.set_property("signal-handoffs", True)
		return p

	def handoff(self, element, buffer, pad):
		self.buffer_times.append(time.time())
		return True

	def on_stop(self):
		count = len(self.buffer_times) - 1
		if count <= 0:
			self.error = "No buffers processed"
			return
		total_time = self.buffer_times[-1] - self.buffer_times[0]
		fps = count / total_time
		max_delay = max(b - a for a, b in zip(self.buffer_times[:-1], self.buffer_times[1:]))
		max_delay = int(max_delay * 1000)
		self.out['framerate'] = int(fps)
		if self.expected_framerate:
			if fps >= self.expected_framerate:
				self.checks['framerate'] = 1
			else:
				self.checks['framerate'] = 0
		self.out['max_delay'] = max_delay
		if self.expected_max_delay:
			if max_delay < self.expected_max_delay:
				self.checks['max_delay'] = 1
			else:
				self.checks['max_delay'] = 0

test_class = GstVDecoderTest
