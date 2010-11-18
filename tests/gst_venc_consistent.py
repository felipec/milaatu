import gst
import os
import hashlib

from base.gst_test import GstTest

class GstVEncConsisTest(GstTest):

	def __init__(self):
		GstTest.__init__(self)

		self.element = "theoraenc"
		self.iterations = 100
		self.curr_iteration = 1
		self.bitrate = 0
		self.framerate = 15
		self.framesize = "640x480"
		self.tmp_filename = "/tmp/consistency.raw"
		self.tmp_filename = "/home/user/MyDocs/.tmp/milaatu-temp-file.raw"
		self.hash_value = 0
		try:
			os.mkdir(os.path.dirname(self.tmp_filename))
		except OSError:
			pass

	def start(self):
		# cache the file the first time only
		if self.location and self.hash_value == 0:
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

		enc = gst.element_factory_make(self.element)
		enc.props.bitrate = self.bitrate

		sink = gst.element_factory_make("filesink")
		sink.props.location = self.tmp_filename

		s = gst.Structure("video/x-raw-yuv")
		s["format"] = gst.Fourcc(self.format)
		s["width"] = width
		s["height"] = height
		s["framerate"] = gst.Fraction(self.framerate, 1)

		capf = gst.element_factory_make("capsfilter")
		capf.props.caps = gst.Caps(s)
		p.add(src, capf, enc, sink)

		if not gst.element_link_many(src, capf, enc, sink):
			print " pipeline creation error !!"

		return p

	def print_error(self, new_hash):
		print "Error: hash values are diferent!!"
		print "First iteration: %s" % self.hash_value
		print "Current iteration: %s" % new_hash

	def on_stop(self):

		self.curr_iteration += 1

		if self.curr_iteration == self.iterations:
			print "iterations finished - consistency kept: success"
			print "hash value was = %s" % self.hash_value
			self.checks["consistency"] = 1
			return
		else:
			if not self.hash_value:
				self.hash_value = self.md5sum(self.tmp_filename)
				os.rename(self.tmp_filename, self.tmp_filename + ".orig")
			else:
				tmp = self.md5sum(self.tmp_filename)
				if tmp != self.hash_value:
					self.print_error(tmp)
					self.checks["consistency"] = 0
					return

		self.start()

	def md5sum(self,fname):
		'''Returns an md5 hash for file fname, or stdin if fname is "-".'''
		try:
			f = file(fname, 'rb')
		except:
			return 'Failed to open file'
		m = hashlib.md5()
		while True:
			d = f.read(8096)
			if not d:
				break
			m.update(d)
		f.close()
		return m.hexdigest()

test_class = GstVEncConsisTest
