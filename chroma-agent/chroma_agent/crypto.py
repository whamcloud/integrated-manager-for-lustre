#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


import errno
from chroma_agent import shell
from chroma_agent.log import console_log
import os


class Crypto(object):
    def __init__(self, folder):
        self.PRIVATE_KEY_FILE = os.path.join(folder, "private.pem")
        self.CERTIFICATE_FILE = os.path.join(folder, "self.crt")
        self.AUTHORITY_FILE = os.path.join(folder, "authority.crt")

    @property
    def private_key_file(self):
        """Return a path to a PEM file"""
        if not os.path.exists(self.PRIVATE_KEY_FILE):
            console_log.info("Generating private key")
            shell.try_run(['openssl', 'genrsa', '-out', self.PRIVATE_KEY_FILE, '2048'])

        return self.PRIVATE_KEY_FILE

    @property
    def certificate_file(self):
        if os.path.exists(self.CERTIFICATE_FILE):
            return self.CERTIFICATE_FILE
        else:
            return None

    @property
    def authority_certificate_file(self):
        if os.path.exists(self.AUTHORITY_FILE):
            return self.AUTHORITY_FILE
        else:
            return None

    def generate_csr(self, common_name):
        """Return a CSR as a string"""
        output = shell.try_run(["openssl", "req", "-new", "-subj", "/C=/ST=/L=/O=/CN=%s" % common_name, "-key", self.private_key_file])
        return output.strip()

    def install_authority(self, ca):
        open(self.AUTHORITY_FILE, 'w').write(ca)

    def install_certificate(self, cert):
        """Install a certificate for our private key, signed by the authority"""
        open(self.CERTIFICATE_FILE, 'w').write(cert)

    def delete(self):
        for file in [self.PRIVATE_KEY_FILE, self.CERTIFICATE_FILE, self.AUTHORITY_FILE]:
            try:
                os.unlink(self.PRIVATE_KEY_FILE)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    pass
                else:
                    raise
