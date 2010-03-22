import gst
import time

from base.gst_test import GstTest

class GstVDecoderTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = None
		self.num_buffers = 100
		self.expected_framerate = 0

		self.buffer_times = []

	def pad_add(self, demuxer, pad):
		dec_pad = self.dec.get_pad("sink")
		pad.link(dec_pad)

	def create_pipeline(self):
		p = gst.Pipeline()

		src = gst.element_factory_make("filesrc")
		src.props.num_buffers = self.num_buffers
		src.props.location = self.location
		demux = gst.element_factory_make("qtdemux")
		dec = gst.element_factory_make(self.element)
		sink = gst.element_factory_make("fakesink")
		demux.connect("pad-added", self.pad_add)

		p.add(src, demux, dec, sink)
		src.link(demux)
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
		total_time = self.buffer_times[-1] - self.buffer_times[0]
		fps = count / total_time
		self.out['framerate'] = int(fps)
		if self.expected_framerate:
			if fps >= self.expected_framerate:
				self.checks['framerate'] = 1
			else:
				self.checks['framerate'] = 0

test_class = GstVDecoderTest
