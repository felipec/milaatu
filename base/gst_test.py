import glib
import gst

import sys
import traceback

def _get_exception():
	etype, value, tb = sys.exc_info()
	lines = traceback.format_exception_only(etype, value)
	return ". ".join([ i.strip() for i in lines ])

class GstTest(object):

	def __init__(self):
		self.error = None
		self.out = {}
		self.checks = {}

	def start(self):
		try:
			self.loop = glib.MainLoop()
			self.player = self.create_pipeline()
			bus = self.player.get_bus()
			bus.add_signal_watch()
			bus.connect("message", self.on_message)
			self.player.set_state(gst.STATE_PLAYING)
			self.loop.run()
		except:
			self.error = _get_exception()

		if not self.error:
			self.on_stop()

	def on_stop(self):
		pass

	def create_pipeline(self):
		return gst.Pipeline()

	def on_state_changed(self, old, new):
		pass

	def on_message(self, bus, message):
		if message.type == gst.MESSAGE_EOS:
			self.player.set_state(gst.STATE_NULL)
			self.loop.quit()
		elif message.type == gst.MESSAGE_ERROR:
			self.player.set_state(gst.STATE_NULL)
			err, debug = message.parse_error()
			self.error = err.message
			self.loop.quit()
		elif message.type == gst.MESSAGE_STATE_CHANGED:
			old, new, pend = message.parse_state_changed()
			self.on_state_changed(old, new)
