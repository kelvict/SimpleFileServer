import SimpleHTTPServer
import BaseHTTPServer
import urllib
import cgi
import os
import sys
import re
from SimpleHTTPServer import SimpleHTTPRequestHandler
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class HTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        path = self.translate_path(self.path)
        boundary = self.headers.plisttext.split("=")[1]

        class FileIterator:
            def __init__(self, f, length):
                self.f = f
                self.length = length

            def next(self):
                line = self.f.readline()
                self.length -= len(line)
                return line

        content_length = int(self.headers['content-length'])
        file_iter = FileIterator(self.rfile, content_length)
        file_iter.next()  # FormBoundary
        line = file_iter.next()  # Content-Disposition
        filename = re.findall(r'filename="(.*)"', line)[0]
        filename = os.path.join(path, filename)
        try:
            uploaded_file = open(filename, 'wb')
        except IOError:
            print "Can't open %s." % filename
        file_iter.next()  # Content-Type
        file_iter.next()  # Blank line

        # Start uploading file.
        cur_line = next_line = file_iter.next()
        while boundary not in next_line:
            uploaded_file.write(cur_line)
            cur_line = next_line
            next_line = file_iter.next()
        else:
            cur_line = cur_line[:-2] if cur_line[-2] == '\r' else cur_line[:-1]
            uploaded_file.write(cur_line)

        # Redirect browser.
        self.send_response(301)
        self.send_header("Location", self.path)
        self.end_headers()

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = StringIO()
        displaypath = cgi.escape(urllib.unquote(self.path))
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
        f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
        f.write("<hr>\n<ul>\n")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write('<li><a href="%s">%s</a>\n'
                    % (urllib.quote(linkname), cgi.escape(displayname)))

        f.write("</ul>\n<hr>\n")
        f.write('<form enctype="multipart/form-data" method="post">\n')
        f.write('<input name="file" type="file" />\n')
        f.write('<input type="submit" value="upload" />\n')
        f.write('</form>\n')
        f.write("</body>\n</html>\n")

        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f


def test(HandlerClass = HTTPRequestHandler,
         ServerClass = BaseHTTPServer.HTTPServer):
    SimpleHTTPServer.test(HandlerClass, ServerClass)


if __name__ == '__main__':
    test()