import gst
import time

from base.gst_test import GstTest

class GstVEncoderTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = "theoraenc"
		self.num_buffers = 100
		self.bitrate = 0
		self.framerate = 15
		self.framesize = "640x480"

		self.buffer_sizes = []
		self.buffer_times = []

	def create_pipeline(self):
		p = gst.Pipeline()

		src = gst.element_factory_make("videotestsrc")
		src.props.num_buffers = self.num_buffers
		enc = gst.element_factory_make(self.element)
		enc.props.bitrate = self.bitrate
		sink = gst.element_factory_make("fakesink")

		width, height = self.framesize.split("x")

		s = gst.Structure("video/x-raw-yuv")
		s["width"] = int(width)
		s["height"] = int(height)
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

test_class = GstVEncoderTest
