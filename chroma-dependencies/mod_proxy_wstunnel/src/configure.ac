dnl  vim: set sw=4 expandtab :
dnl
dnl Copyright 2013 Intel Corporation All Rights Reserved.
dnl
dnl  Licensed under the Apache License, Version 2.0 (the "License");
dnl  you may not use this file except in compliance with the License.
dnl  You may obtain a copy of the License at
dnl
dnl      http://www.apache.org/licenses/LICENSE-2.0
dnl
dnl  Unless required by applicable law or agreed to in writing, software
dnl  distributed under the License is distributed on an "AS IS" BASIS,
dnl  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
dnl  See the License for the specific language governing permissions and
dnl  limitations under the License.

dnl Process this file with autoconf to produce a configure script.

AC_INIT(mod_proxy_wstunnel.c)

AC_ARG_WITH(apxs, AC_HELP_STRING([--with-apxs=NAME],
            [name of the apxs executable [[apxs]]]),
            [APXS="$with_apxs"])

if test -z "${APXS}"; then
    AC_PATH_PROGS(APXS, apxs2 apxs, [apxs],
                   [$PATH:/usr/local/apache/bin:/usr/sbin])
fi

AC_SUBST(APXS)

AC_MSG_CHECKING(Apache version)
HTTPD="`${APXS} -q SBINDIR`/`${APXS} -q TARGET`"
HTTPD_INCLUDEDIR="`${APXS} -q INCLUDEDIR`"
if test -x ${HTTPD}; then
    HTTPD_VERSION=`${HTTPD} -v | awk '/version/ {print $3}' \
     | awk -F/ '{print $2}'`
else
    if test -f ${HTTPD_INCLUDEDIR}/ap_release.h; then
        HTTPD_VERSION=`grep '^#define AP_SERVER_MAJORVERSION_NUMBER ' \
         ${HTTPD_INCLUDEDIR}/ap_release.h | sed -e \
         's/^#define AP_SERVER_MAJORVERSION_NUMBER \([0-9]\).*/\1.X/'`
    else
        if test -f ${HTTPD_INCLUDEDIR}/httpd.h; then
            HTTPD_VERSION=`grep '^#define APACHE_RELEASE ' \
             ${HTTPD_INCLUDEDIR}/httpd.h | sed -e \
             's/^#define APACHE_RELEASE \([0-9]\).*/\1.X/'`
        else
            HTTPD_VERSION="2.?"
        fi
    fi
fi
AC_MSG_RESULT($HTTPD_VERSION)

CFLAGS1=""
for arg in ${CFLAGS}
do
    CFLAGS1="${CFLAGS1} -Wc,$arg"
done

CPPFLAGS="${CPPFLAGS}"
CFLAGS="${CFLAGS1}"
LDFLAGS="${LDFLAGS}"
LDLIBS="${LDLIBS}"

AC_SUBST(CPPFLAGS)
AC_SUBST(CFLAGS)
AC_SUBST(LDFLAGS)
AC_SUBST(LDLIBS)

LIBEXECDIR="`${APXS} -q LIBEXECDIR`"
AC_SUBST(LIBEXECDIR)

HTTPD_MAJOR_VERSION=`echo ${HTTPD_VERSION} | sed -e 's/\..*//'`

AC_OUTPUT(Makefile)
