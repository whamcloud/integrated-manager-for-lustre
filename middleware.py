

import traceback
import sys

class ExceptionPrinterMiddleware:
    def process_exception(self, request, exception):
        exc_info = sys.exc_info()
        print "######################## Exception #############################"
        print '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
        print "################################################################"
        return None

