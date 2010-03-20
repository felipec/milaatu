import gst

from base.gst_test import GstTest

class GstErrorTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)
		self.state_error = 1

	def create_pipeline(self):
		p = gst.Pipeline()

		src = gst.element_factory_make("videotestsrc")
		sink = gst.element_factory_make("fakesink")
		sink.props.state_error = self.state_error

		p.add(src, sink)
		gst.element_link_many(src, sink)

		return p

test_class = GstErrorTest
