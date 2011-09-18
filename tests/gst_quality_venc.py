import gst

from base.gst_test import GstTest

class GstQualityVEncoderTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = "ffenc_mpeg4"
		self.num_buffers = 500
		self.bitrate = 0
		self.framerate = 15
		self.framesize = "640x480"
		self.format = "I420"
		self.location = None

		self.mode = None

		self.ssim_avg = self.ssim_min = self.ssim_max = 0
		self.ssim_avg_threshold = self.ssim_min_threshold = 0.98

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

		if self.mode is not None:
			enc.props.mode = self.mode

		if bitrate:
			enc.props.bitrate = bitrate

		sink = gst.element_factory_make("fakesink")

		s = gst.Structure("video/x-raw-yuv")
		s["format"] = gst.Fourcc(self.format)
		s["width"] = width
		s["height"] = height
		s["framerate"] = gst.Fraction(self.framerate, 1)

		tee = gst.element_factory_make("tee")
		queue = gst.element_factory_make("multiqueue")
		ssim = gst.element_factory_make("xssim")
		dec = gst.element_factory_make("avvdec")

		p.add(tee, queue, ssim, dec)

		capf = gst.element_factory_make("capsfilter")
		capf.props.caps = gst.Caps(s)

		p.add(src, capf, enc, sink)
		gst.element_link_many(src, capf, tee)
		gst.element_link_many(tee, enc, dec, queue, ssim)

		ssim.connect("got_results", self.got_results)

		gst.element_link_many(tee, queue, ssim)
		ssim.link(sink)
		return p

	def got_results(self, element, savg, smin, smax):
		self.ssim_avg = savg
		self.ssim_min = smin
		self.ssim_max = smax

	def on_stop(self):
		self.out['ssim_avg'] = self.ssim_avg
		self.out['ssim_min'] = self.ssim_min
		self.out['ssim_max'] = self.ssim_max
		self.checks['ssim_avg'] = self.ssim_avg >= self.ssim_avg_threshold
		self.checks['ssim_min'] = self.ssim_min >= self.ssim_min_threshold

test_class = GstQualityVEncoderTest
