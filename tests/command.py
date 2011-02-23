import os

class CommandTest(object):
	def __init__(self):
		self.error = None

	def start(self):
		r = os.system(self.command)
		if r != 0:
			self.error = "Bad exit status"
		pass

test_class = CommandTest
