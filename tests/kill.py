import os, signal

class KillTest(object):
	def start(self):
		os.kill(os.getpid(), signal.SIGSEGV)

test_class = KillTest
