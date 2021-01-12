# Copyright (c) 2018 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


import errno
import os

from chroma_agent.lib.shell import AgentShell
from chroma_agent.log import console_log


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
            AgentShell.try_run(["openssl", "genrsa", "-out", self.PRIVATE_KEY_FILE, "2048", "-sha256"])

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
        output = AgentShell.try_run(
            [
                "openssl",
                "req",
                "-new",
                "-sha256",
                "-subj",
                "/C=/ST=/L=/O=/CN=%s" % common_name,
                "-key",
                self.private_key_file,
            ]
        )
        return output.strip()

    def install_authority(self, ca):
        open(self.AUTHORITY_FILE, "w").write(ca)

    def install_certificate(self, cert):
        """Install a certificate for our private key, signed by the authority"""
        open(self.CERTIFICATE_FILE, "w").write(cert)

    def delete(self):
        for path in [self.PRIVATE_KEY_FILE, self.CERTIFICATE_FILE, self.AUTHORITY_FILE]:
            try:
                os.unlink(path)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    pass
                else:
                    raise
