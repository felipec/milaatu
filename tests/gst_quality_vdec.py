import gst
import os

from base.gst_test import GstTest

class GstQualityVDecoderTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = None
		self.num_buffers = 500

		self.input_buffers = 0
		self.output_buffers = 0
		self.ssim_avg = self.ssim_min = self.ssim_max = 0
		self.queue_mem = 20 * 1024 * 1024

	def pad_add(self, demuxer, pad, data):
		if not str(pad.get_caps()).startswith("video/"):
			return
		opad = data.get_pad("sink")
		pad.link(opad)

	def create_pipeline(self):
		p = gst.Pipeline()

		src = gst.element_factory_make("filesrc")
		src.props.location = self.location

		ext = os.path.splitext(self.location)[1].lower()
		ext_demux = {
				".asf": "asfdemux",
				".wmv": "asfdemux",
				".mp4": "qtdemux",
				".avi": "avidemux",
				".mkv": "matroskademux",
				".gdp": "gdpdepay" }

		demux = gst.element_factory_make(ext_demux.get(ext))
		tee = gst.element_factory_make("tee")

		dec = gst.element_factory_make(self.element)
		dec2 = gst.element_factory_make("avvdec")
		ssim = gst.element_factory_make("xssim")
		sink = gst.element_factory_make("fakesink")
		queue = gst.element_factory_make("multiqueue")

		pre_id = gst.element_factory_make("identity")
		post_id = gst.element_factory_make("identity")

		queue.set_properties(
				max_size_bytes=self.queue_mem,
				max_size_time=0,
				max_size_buffers=0)

		p.add(src, demux, tee, dec, dec2, queue, ssim, sink)
		p.add(pre_id, post_id)

		src.link(demux)
		try:
			demux.link(dec)
		except gst.LinkError:
			demux.connect("pad-added", self.pad_add, tee)
		gst.element_link_many(tee, pre_id, dec, post_id, queue, ssim)
		gst.element_link_many(tee, dec2, queue, ssim)
		ssim.link(sink)

		ssim.connect("got_results", self.got_results)

		pre_id.connect("handoff", self.dec_handoff_in)
		post_id.connect("handoff", self.dec_handoff_out)
		return p

	def got_results(self, element, savg, smin, smax):
		self.ssim_avg = savg
		self.ssim_min = smin
		self.ssim_max = smax

	def dec_handoff_in(self, element, buffer):
		self.input_buffers += 1

	def dec_handoff_out(self, element, buffer):
		self.output_buffers += 1
		if self.output_buffers < self.num_buffers:
			return
		self.pipeline.send_event(gst.event_new_eos())

	def on_stop(self):
		self.out['input_buffers'] = self.input_buffers
		self.out['output_buffers'] = self.output_buffers
		self.out['ssim_avg'] = self.ssim_avg
		self.out['ssim_min'] = self.ssim_min
		self.out['ssim_max'] = self.ssim_max
		self.checks['ssim'] = self.ssim_avg >= 0.98

test_class = GstQualityVDecoderTest
