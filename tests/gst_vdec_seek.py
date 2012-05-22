import gst
import time
import os
import glib

from base.gst_test import GstTest

class GstSeekTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = None
		self.duration = None
		self.timer_set = False
		self.state = 0

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

		sink.set_property("sync", True)
		return p


	def on_state_changed(self, old, new):
		if (not self.timer_set) and (new == gst.STATE_PLAYING):
			self.timer_set = True
			glib.timeout_add(1000, self.seek_timeout)
			self.duration = self.pipeline.query_duration(gst.FORMAT_TIME, None)[0]

	def seek_timeout(self):
		self.state += 1

		if self.duration < 5 * gst.SECOND:
			self.checks['clip_long_enough'] = 0
			return False

		if self.state == 1:
			self.checks['seek_fwd'] = self.seek(2)
			return True

		if self.state == 2:
			return True

		if self.state == 3:
			self.checks['seek_back'] = self.seek(-2)
			return True

		# seek to a position 1 sec before clip end -> EOS
		if self.state == 4:
			pos_now = self.pipeline.query_position(gst.FORMAT_TIME, None)[0]
			self.checks['seek_to_end'] = \
					self.seek((self.duration - pos_now - gst.SECOND) / gst.SECOND)

			self.checks['clip_long_enough'] = 1
			return False

		assert False

	def seek(self, secs):
		pos_before = self.pipeline.query_position(gst.FORMAT_TIME, None)[0]
		seek_ns = pos_before + (secs * gst.SECOND)
		seek_start_time = time.time()

		if not self.pipeline.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, seek_ns):
			print "seek error"
			return 0

		# wait for seek to complete
		if self.pipeline.get_state() != (gst.STATE_CHANGE_SUCCESS, \
				gst.STATE_PLAYING, \
				gst.STATE_VOID_PENDING):
			print "seek error"
			return 0

		seek_ready_time = time.time()
		pos_after = self.pipeline.query_position(gst.FORMAT_TIME, None)[0]

		seek_dur = pos_after - pos_before
		seek_inac = secs * gst.SECOND - seek_dur
		seek_time = seek_ready_time - seek_start_time

		print "Seeked %d ms, inaccuracy %d ms, seeking took %.2f seconds" % \
				(seek_dur / 1000000, seek_inac / 1000000, seek_time)
		if seek_inac < 0.2:
			return 1
		return 0

test_class = GstSeekTest
